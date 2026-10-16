import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from typing import Optional

from src.character.memory import CharacterMemory
from src.vision.landmark_detector import LandmarkDetector
from src.character.rig_builder import CharacterRigBuilder
from src.audio.lipsync import LipSyncEngine
from src.bridge.dispatcher import AEBridgeDispatcher
from src.worker.ollama_client import OllamaWorkerClient
from src.bridge.project_scanner import ProjectScanner

logger = logging.getLogger(__name__)


from pathlib import Path
from src.config import settings

WEB_DIR = settings.project_root / "src" / "web"


class AfterBrainHTTPHandler(BaseHTTPRequestHandler):
    """Handles REST API and Web UI requests for the After Effects AI Live Copilot."""

    memory = CharacterMemory()
    detector = LandmarkDetector()
    dispatcher = AEBridgeDispatcher()
    worker = OllamaWorkerClient(memory=memory)
    scanner = ProjectScanner(dispatcher=dispatcher, memory=memory, detector=detector)

    def _send_file(self, file_path: Path, content_type: str):
        if file_path.exists():
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        else:
            self._send_json(404, {"error": "File not found"})

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Connection", "close")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/style.css":
            self._send_file(WEB_DIR / "style.css", "text/css; charset=utf-8")
        elif path == "/app.js":
            self._send_file(WEB_DIR / "app.js", "application/javascript; charset=utf-8")
        elif path == "/api/status":
            ollama_status = self.worker.check_connection()
            bridge_status = self.dispatcher.get_status()
            characters = self.memory.list_characters()
            self._send_json(200, {
                "status": "ready",
                "ollama": ollama_status,
                "bridge": bridge_status,
                "character_count": len(characters),
                "characters": [c["name"] for c in characters]
            })
        elif path == "/api/project_assets":
            assets = self.scanner.get_tagged_project_assets()
            self._send_json(200, {
                "status": "success",
                "count": len(assets),
                "assets": assets
            })
        elif path == "/api/characters":
            characters = self.memory.list_characters()
            self._send_json(200, {"characters": characters})
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(post_body)
        except Exception:
            req_data = {}

        if path == "/api/tag_asset":
            tag = req_data.get("tag", "").strip()
            desc = req_data.get("description", "").strip()
            role = req_data.get("role", "Character").strip()
            personality = req_data.get("personality", "").strip()
            auto_rig = req_data.get("auto_rig", True)

            if not tag:
                self._send_json(400, {"error": "Missing tag parameter"})
                return

            res = self.scanner.tag_project_asset(tag, desc, role=role, personality=personality, auto_rig=auto_rig)
            self._send_json(200, res)

        elif path == "/api/chat":
            message = req_data.get("message", "").strip()
            char_override = req_data.get("character", "").strip()
            if not message:
                self._send_json(400, {"reply": "Please type a message or prompt."})
                return

            msg_lower = message.lower()

            # 0. Conversational greetings / status checks
            if msg_lower in ["hi", "hello", "hey", "are you working", "are you working ?", "are you there", "test", "status", "ping", "help"]:
                chars = self.memory.list_characters()
                char_str = ", ".join([f"@{c['name']}" for c in chars]) if chars else "None yet"
                reply = (
                    "👋 Hello! Yes, I am fully online and connected live to your After Effects session!\n\n"
                    f"• Active Model: {self.worker.model}\n"
                    f"• Tagged Characters in Memory: {char_str}\n\n"
                    "How to use me:\n"
                    "1. Import your character image into AE's Project Panel.\n"
                    "2. Tell me: `@CharacterName is our goofy protagonist`\n"
                    "3. Prompt me: `Make @CharacterName wave and bounce happily`!"
                )
                self._send_json(200, {"reply": reply, "status": "success"})
                return

            # 1. Check if user is defining/tagging an asset directly in chat: e.g. "@AlienBob is a goofy alien"
            import re
            tag_def_match = re.search(r"@([a-zA-Z0-9_\.\-]+)\s+(?:is\s+(?:a|our|the)?|as\s+)\s*(.+)", message, re.IGNORECASE)
            if tag_def_match:
                tag_name = tag_def_match.group(1)
                desc = tag_def_match.group(2).strip()
                role = "Character"
                if any(w in desc.lower() for w in ["background", "backdrop", "scenery", "env"]):
                    role = "Background"
                elif any(w in desc.lower() for w in ["prop", "item", "object"]):
                    role = "Prop"

                tag_res = self.scanner.tag_project_asset(tag_name, desc, role=role)
                if tag_res.get("status") == "success":
                    reply = f"✨ Tagged **@{tag_name}** as *{role}* ('{desc}')!\nI've inspected the asset from your Project Panel and saved it into memory. You can now prompt me with `@{tag_name}` to animate it!"
                    self._send_json(200, {"reply": reply, "status": "success", "tagged_asset": tag_res})
                    return

            # 2. Check if this is an animation request
            is_animation = any(w in msg_lower for w in ["anim", "zoom", "pan", "move", "rotat", "scale", "fade", "bounce", "jump", "walk", "wave", "camera", "motion", "cinematic", "push", "drift", "bg_", "layer", "composition", "comp"])

            # 3. Asset Scan ONLY when explicitly requested and not an animation
            if not is_animation and any(k in msg_lower for k in ["scan assets", "scan my", "scan project", "refresh assets", "sync assets"]):
                res = self.scanner.auto_register_imported_characters()
                reg = res.get("registered_characters", [])
                if reg:
                    names = ", ".join([f"@{r['name']}" for r in reg])
                    reply = f"🔍 Scanned AE Project Panel! Found and rigged {len(reg)} asset(s): {names}.\nThey are now taggable with `@` in chat!"
                else:
                    reply = "No new image footage found in your AE Project Panel. Drag & drop your character image into AE first, then ask me to scan!"
                self._send_json(200, {"reply": reply, "status": "success", "data": res})
                return

            # 4. Extract target layer / character: e.g. "bg_tinku_garden", "@AlienBob", etc.
            characters = self.memory.list_characters()
            target_char = char_override

            mentioned_tags = re.findall(r"@([a-zA-Z0-9_\.\-]+)", message)
            if mentioned_tags:
                target_char = mentioned_tags[0]

            if not target_char:
                # Check for explicit layer names like "bg_tinku_garden"
                layer_token_match = re.search(r"\b([a-zA-Z0-9_]+(?:_[a-zA-Z0-9_]+)+)\b", message)
                if layer_token_match:
                    target_char = layer_token_match.group(1)

            if not target_char:
                for c in characters:
                    if c["name"].lower() in msg_lower:
                        target_char = c["name"]
                        break

            # If user asks to animate background/scenery without a specific name
            if not target_char and any(w in msg_lower for w in ["background", "backdrop", "scenery", "camera", "title", "text"]):
                target_char = "Background"

            # Lip-sync intent
            if any(k in msg_lower for k in ["lipsync", "lip sync", "mouth", "speak", "say"]):
                dialogue = message
                for w in ["lipsync", "lip sync", "speak", "say"]:
                    dialogue = dialogue.replace(w, "").replace(w.title(), "")
                dialogue = dialogue.strip(" :\"'") or "Hello! I am speaking live in After Effects."
                jsx = LipSyncEngine.build_text_dialogue_lipsync_script(target_char or "Character", dialogue)
                exec_res = self.dispatcher.dispatch(jsx, script_name_prefix=f"chat_lipsync_{target_char}")
                reply = f"🎤 Generated syllable lip-sync keyframes for **@{target_char or 'Character'}** speaking: \"{dialogue}\"!\nApplied directly to mouth pin in active comp."
                self._send_json(200, {"reply": reply, "status": "success", "execution": exec_res})
                return

            # Standard animation with Qwen
            res = self.worker.generate_extendscript(message, character_name=target_char)
            jsx = res.get("jsx_code", "")
            if jsx:
                exec_res = self.dispatcher.dispatch(jsx, script_name_prefix=f"chat_anim_{target_char or 'fx'}")
                explanation = res.get("explanation", "Animation generated and applied.")
                reply = f"🚀 **{target_char or 'Motion'}**: {explanation}\nExtendScript executed live in active composition!"
                self._send_json(200, {"reply": reply, "status": "success", "jsx_code": jsx, "execution": exec_res})
            else:
                self._send_json(200, {"reply": f"⚠️ Could not generate animation: {res.get('error', 'Unknown error')}", "status": "error"})

        elif path == "/api/scan_assets":
            # Auto-scan all footage directly in the After Effects Project Panel!
            res = self.scanner.auto_register_imported_characters()
            self._send_json(200, res)

        elif path == "/api/animate":
            character_name = req_data.get("character")
            prompt = req_data.get("prompt", "")

            if not character_name or not prompt:
                self._send_json(400, {"error": "Missing character or prompt parameter"})
                return

            res = self.worker.generate_extendscript(prompt, character_name=character_name)
            jsx = res.get("jsx_code", "")
            if jsx:
                exec_res = self.dispatcher.dispatch(jsx, script_name_prefix=f"anim_{character_name}")
                self._send_json(200, {
                    "status": "success",
                    "jsx_code": jsx,
                    "execution": exec_res,
                    "explanation": res.get("explanation", "")
                })
            else:
                self._send_json(500, {"error": res.get("error", "Failed to generate JSX")})

        elif path == "/api/lipsync":
            character_name = req_data.get("character")
            audio_path = req_data.get("audio_path")
            dialogue = req_data.get("dialogue")

            if not character_name:
                self._send_json(400, {"error": "Missing character parameter"})
                return

            if audio_path:
                jsx = LipSyncEngine.build_audio_driven_lipsync_script(character_name, audio_path)
            else:
                dialogue_text = dialogue or "Hello there! Welcome to AfterBrain."
                jsx = LipSyncEngine.build_text_dialogue_lipsync_script(character_name, dialogue_text)

            exec_res = self.dispatcher.dispatch(jsx, script_name_prefix=f"lipsync_{character_name}")
            self._send_json(200, {
                "status": "success",
                "jsx_code": jsx,
                "execution": exec_res
            })

        elif path == "/api/generate":
            prompt = req_data.get("prompt", "")
            if not prompt:
                self._send_json(400, {"error": "Missing prompt parameter"})
                return

            res = self.worker.generate_extendscript(prompt)
            jsx = res.get("jsx_code", "")
            if jsx:
                exec_res = self.dispatcher.dispatch(jsx, script_name_prefix="gen_anim")
                self._send_json(200, {
                    "status": "success",
                    "jsx_code": jsx,
                    "execution": exec_res,
                    "explanation": res.get("explanation", "")
                })
            else:
                self._send_json(500, {"error": res.get("error", "Failed to generate JSX")})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        # Silence standard HTTP access logs
        return


def start_api_server(port: int = 8088) -> ThreadingHTTPServer:
    """Starts local AfterBrain HTTP API server in a background thread."""
    server = ThreadingHTTPServer(("localhost", port), AfterBrainHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"AfterBrain local API server running on http://localhost:{port}")
    return server
