import json
import logging
from typing import Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

from src.config import settings
from src.vision.landmark_detector import LandmarkDetector
from src.character.memory import CharacterMemory
from src.character.rig_builder import CharacterRigBuilder
from src.audio.lipsync import LipSyncEngine
from src.bridge.dispatcher import AEBridgeDispatcher
from src.worker.ollama_client import OllamaWorkerClient
from src.extendscript.validator import ExtendScriptValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("anmcp")

# Initialize core services
memory = CharacterMemory()
detector = LandmarkDetector()
dispatcher = AEBridgeDispatcher()
worker = OllamaWorkerClient(memory=memory)

# Initialize MCP Server
app = MCPServer("AfterEffects-AI-Worker", version="0.1.0")


@app.tool()
def ae_get_system_status() -> str:
    """Returns status of Ollama connection, Qwen model, After Effects bridge, and registered characters."""
    ollama_status = worker.check_connection()
    bridge_status = dispatcher.get_status()
    characters = memory.list_characters()

    result = {
        "status": "ready",
        "ollama": ollama_status,
        "after_effects_bridge": bridge_status,
        "characters_registered": len(characters),
        "character_names": [c["name"] for c in characters],
        "output_scripts_dir": str(settings.output_scripts_dir.resolve()),
    }
    return json.dumps(result, indent=2)


@app.tool()
def ae_register_character(
    image_path: str,
    character_name: str,
    rig_type: str = "puppet_pins"
) -> str:
    """
    Registers a new character image into After Effects.
    Uses computer vision to locate the mouth, eyes, hands, and joints,
    automatically creates a Puppet Tool rig, and saves the character to memory.
    """
    try:
        # 1. Vision Landmark Detection
        landmarks = detector.detect(image_path, character_name=character_name)

        # 2. Build Puppet Pin ExtendScript
        rig_script = CharacterRigBuilder.build_puppet_rig_script(landmarks)

        # 3. Execute via After Effects Bridge (Live COM or Mock)
        exec_result = dispatcher.dispatch(rig_script, script_name_prefix=f"rig_{character_name}")

        # 4. Save to Character Memory
        memory.register_character(
            name=character_name,
            image_path=image_path,
            landmarks=landmarks.to_dict()["landmarks"],
            rig_type=rig_type,
            layer_name=character_name
        )

        response = {
            "status": "success",
            "character_name": character_name,
            "detected_landmarks": landmarks.to_dict()["landmarks"],
            "confidence_scores": landmarks.confidence_scores,
            "execution": exec_result
        }
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Error registering character: {e}")
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


@app.tool()
def ae_animate_character(
    character_name: str,
    action_prompt: str
) -> str:
    """
    Animates a previously registered character in After Effects using natural language.
    E.g. 'Make Bob wave with his right hand' or 'Make Hero nod his head and breathe'.
    """
    char = memory.get_character(character_name)
    if not char:
        known = [c["name"] for c in memory.list_characters()]
        return json.dumps({
            "status": "error",
            "message": f"Character '{character_name}' not found in registry. Registered: {known}"
        }, indent=2)

    # Ask Qwen to craft the ExtendScript for this character
    llm_result = worker.generate_extendscript(
        user_prompt=action_prompt,
        character_name=character_name
    )

    if llm_result.get("status") != "success" or not llm_result.get("jsx_code"):
        # Fallback to deterministic rig builder action if LLM is unavailable
        jsx_code = CharacterRigBuilder.build_character_animation_script(
            char_name=character_name,
            animation_action=action_prompt
        )
    else:
        jsx_code = llm_result["jsx_code"]

    # Dispatch to AE
    exec_result = dispatcher.dispatch(jsx_code, script_name_prefix=f"anim_{character_name}")
    response = {
        "status": "success",
        "character": character_name,
        "prompt": action_prompt,
        "execution": exec_result,
        "explanation": llm_result.get("explanation", "Targeted animation applied.")
    }
    return json.dumps(response, indent=2)


@app.tool()
def ae_lipsync_character(
    character_name: str,
    audio_path: Optional[str] = None,
    dialogue_text: Optional[str] = None
) -> str:
    """
    Automates lip-syncing for a character in After Effects.
    Provide either:
    - audio_path: Uses After Effects Audio-to-Keyframes and connects the Mouth Puppet Pin to the loudness curve.
    - dialogue_text: Generates rhythmic phonetic syllable mouth keyframes from dialogue.
    """
    char = memory.get_character(character_name)
    if not char:
        return json.dumps({
            "status": "error",
            "message": f"Character '{character_name}' not found."
        }, indent=2)

    if audio_path:
        jsx_code = LipSyncEngine.build_audio_driven_lipsync_script(
            char_name=character_name,
            audio_file_path=audio_path
        )
    elif dialogue_text:
        jsx_code = LipSyncEngine.build_text_dialogue_lipsync_script(
            char_name=character_name,
            dialogue_text=dialogue_text
        )
    else:
        return json.dumps({
            "status": "error",
            "message": "Either audio_path or dialogue_text must be provided."
        }, indent=2)

    exec_result = dispatcher.dispatch(jsx_code, script_name_prefix=f"lipsync_{character_name}")
    return json.dumps({
        "status": "success",
        "character": character_name,
        "sync_mode": "audio_amplitude" if audio_path else "text_syllables",
        "execution": exec_result
    }, indent=2)


@app.tool()
def ae_generate_animation(prompt: str) -> str:
    """
    Generates general motion graphics, kinetic typography, shapes, and camera moves from natural language.
    Queries Qwen via Ollama, generates ExtendScript, and executes it in After Effects.
    """
    llm_result = worker.generate_extendscript(user_prompt=prompt)
    if llm_result.get("status") != "success" or not llm_result.get("jsx_code"):
        return json.dumps(llm_result, indent=2)

    jsx_code = llm_result["jsx_code"]
    exec_result = dispatcher.dispatch(jsx_code, script_name_prefix="general_anim")

    return json.dumps({
        "status": "success",
        "prompt": prompt,
        "execution": exec_result,
        "explanation": llm_result.get("explanation", ""),
        "syntax_valid": llm_result.get("syntax_valid", True)
    }, indent=2)


@app.tool()
def ae_list_known_characters() -> str:
    """Returns all currently registered characters, their layers, and pin mappings."""
    characters = memory.list_characters()
    return json.dumps({"count": len(characters), "characters": characters}, indent=2)


@app.tool()
def ae_run_raw_extendscript(jsx_code: str) -> str:
    """Executes arbitrary ExtendScript directly in After Effects or the Mock Simulator."""
    cleaned = ExtendScriptValidator.clean_code(jsx_code)
    is_valid, msg = ExtendScriptValidator.validate(cleaned)
    if not is_valid:
        return json.dumps({"status": "error", "message": f"Syntax validation failed: {msg}"}, indent=2)

    exec_result = dispatcher.dispatch(cleaned, script_name_prefix="raw_script")
    return json.dumps(exec_result, indent=2)


if __name__ == "__main__":
    import sys
    logger.info("Starting AfterEffects-AI-Worker MCP Server on stdio...")
    app.run()
