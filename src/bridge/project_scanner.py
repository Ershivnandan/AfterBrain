import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.config import settings
from src.vision.landmark_detector import LandmarkDetector
from src.character.memory import CharacterMemory
from src.character.rig_builder import CharacterRigBuilder
from src.bridge.dispatcher import AEBridgeDispatcher

logger = logging.getLogger(__name__)


class ProjectScanner:
    """Scans all imported footage assets directly from the active Adobe After Effects Project Panel."""

    SCAN_ASSETS_JSX = """// AfterBrain: Project Asset Scanner
(function() {
    var manifest = {
        projectOpen: false,
        projectName: "",
        images: [],
        audio: []
    };

    if (app.project) {
        manifest.projectOpen = true;
        manifest.projectName = app.project.file ? app.project.file.name : "Untitled Project";

        for (var i = 1; i <= app.project.items.length; i++) {
            var item = app.project.items[i];
            if (item instanceof FootageItem && item.file && item.file.exists) {
                var ext = item.file.name.split('.').pop().toLowerCase();
                var assetInfo = {
                    id: item.id,
                    name: item.name,
                    fileName: item.file.name,
                    fullPath: item.file.fsName,
                    width: item.width,
                    height: item.height
                };

                if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'psd' || ext === 'ai') {
                    manifest.images.push(assetInfo);
                } else if (ext === 'mp3' || ext === 'wav' || ext === 'aac' || ext === 'm4a') {
                    manifest.audio.push(assetInfo);
                }
            }
        }

        // Also scan layers in active composition (even if not in project bin)
        if (app.project.activeItem && app.project.activeItem instanceof CompItem) {
            var comp = app.project.activeItem;
            for (var l = 1; l <= comp.numLayers; l++) {
                var layer = comp.layer(l);
                if (layer.source && layer.source instanceof FootageItem && layer.source.file && layer.source.file.exists) {
                    var lFile = layer.source.file;
                    var lExt = lFile.name.split('.').pop().toLowerCase();
                    var existsInManifest = false;
                    for (var mIdx = 0; mIdx < manifest.images.length; mIdx++) {
                        if (manifest.images[mIdx].fullPath === lFile.fsName) {
                            existsInManifest = true;
                            break;
                        }
                    }
                    if (!existsInManifest && (lExt === 'png' || lExt === 'jpg' || lExt === 'jpeg' || lExt === 'psd' || lExt === 'ai')) {
                        manifest.images.push({
                            id: layer.source.id,
                            name: layer.name,
                            fileName: lFile.name,
                            fullPath: lFile.fsName,
                            width: layer.source.width,
                            height: layer.source.height
                        });
                    }
                }
            }
        }
    }

    // Robust JSON serializer for ExtendScript compatibility
    function serializeManifest(m) {
        var str = '{\\n  "projectOpen": ' + (m.projectOpen ? 'true' : 'false') + ',\\n';
        str += '  "projectName": "' + m.projectName.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
        str += '  "images": [\\n';
        for (var j = 0; j < m.images.length; j++) {
            var img = m.images[j];
            str += '    {\\n';
            str += '      "id": ' + img.id + ',\\n';
            str += '      "name": "' + img.name.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
            str += '      "fileName": "' + img.fileName.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
            str += '      "fullPath": "' + img.fullPath.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
            str += '      "width": ' + img.width + ',\\n';
            str += '      "height": ' + img.height + '\\n';
            str += '    }' + (j < m.images.length - 1 ? ',' : '') + '\\n';
        }
        str += '  ],\\n';
        str += '  "audio": [\\n';
        for (var k = 0; k < m.audio.length; k++) {
            var aud = m.audio[k];
            str += '    {\\n';
            str += '      "id": ' + aud.id + ',\\n';
            str += '      "name": "' + aud.name.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
            str += '      "fileName": "' + aud.fileName.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '",\\n';
            str += '      "fullPath": "' + aud.fullPath.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"') + '"\\n';
            str += '    }' + (k < m.audio.length - 1 ? ',' : '') + '\\n';
        }
        str += '  ]\\n';
        str += '}';
        return str;
    }

    // Write manifest to exchange file
    var exchangeFile = new File("__EXCHANGE_PATH__");
    exchangeFile.encoding = "UTF-8";
    exchangeFile.open("w");
    exchangeFile.write(serializeManifest(manifest));
    exchangeFile.close();

    return "Assets scanned: " + manifest.images.length + " images, " + manifest.audio.length + " audio files";
})();
"""

    def __init__(
        self,
        dispatcher: Optional[AEBridgeDispatcher] = None,
        memory: Optional[CharacterMemory] = None,
        detector: Optional[LandmarkDetector] = None,
    ):
        self.dispatcher = dispatcher or AEBridgeDispatcher()
        self.memory = memory or CharacterMemory()
        self.detector = detector or LandmarkDetector()
        self.exchange_path = settings.project_root / "data" / "project_assets_manifest.json"
        self.exchange_path.parent.mkdir(parents=True, exist_ok=True)

    def scan_imported_assets(self) -> Dict[str, Any]:
        """
        Queries After Effects for all footage items in the Project Panel
        and returns the discovered images and audio files.
        """
        # Inject target path into JSX
        escaped_path = str(self.exchange_path.resolve()).replace("\\", "\\\\")
        script = self.SCAN_ASSETS_JSX.replace("__EXCHANGE_PATH__", escaped_path)

        # Dispatch script to After Effects
        self.dispatcher.dispatch(script, script_name_prefix="scan_assets")

        # Read back exchange manifest if written by AE
        if self.exchange_path.exists():
            try:
                with open(self.exchange_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading asset manifest: {e}")

        # Fallback empty manifest
        return {"projectOpen": False, "images": [], "audio": []}

    def auto_register_imported_characters(self) -> Dict[str, Any]:
        """
        Scans all imported images from After Effects, automatically runs
        Landmark Perception on each character image, and registers them into Character Memory.
        """
        manifest = self.scan_imported_assets()
        images = manifest.get("images", [])

        registered_characters = []
        errors = []

        for img in images:
            file_path = img["fullPath"]
            char_name = Path(file_path).stem.title()

            try:
                # 1. Vision Landmark Detection
                landmarks = self.detector.detect(file_path, character_name=char_name)

                # 2. Build Puppet Rig JSX
                rig_script = CharacterRigBuilder.build_puppet_rig_script(landmarks)

                # 3. Dispatch Rig to After Effects
                self.dispatcher.dispatch(rig_script, script_name_prefix=f"rig_{char_name}")

                # 4. Save into Character Memory
                self.memory.register_character(
                    name=char_name,
                    image_path=file_path,
                    landmarks=landmarks.to_dict()["landmarks"],
                    rig_type="puppet_pins",
                    layer_name=char_name,
                    description=f"Auto-imported from After Effects Project ({img['name']})"
                )

                registered_characters.append({
                    "name": char_name,
                    "file": img["name"],
                    "landmarks_detected": True
                })
            except Exception as e:
                errors.append({"file": img["name"], "error": str(e)})

        return {
            "status": "success",
            "scanned_count": len(images),
            "audio_count": len(manifest.get("audio", [])),
            "registered_characters": registered_characters,
            "errors": errors
        }

    def get_tagged_project_assets(self) -> List[Dict[str, Any]]:
        """
        Scans After Effects Project Panel items and cross-references with CharacterMemory.
        Returns a list of assets with their '@tag', registration status, role, and description.
        """
        manifest = self.scan_imported_assets()
        images = manifest.get("images", [])
        tagged_assets = []

        for img in images:
            file_path = img["fullPath"]
            default_tag = Path(file_path).stem.title()
            existing = self.memory.get_character(default_tag)

            if not existing:
                for c in self.memory.list_characters():
                    if c["name"].lower() == default_tag.lower() or Path(c.get("image_path", "")).name.lower() == img["fileName"].lower():
                        existing = c
                        break

            asset_info = {
                "id": img["id"],
                "name": img["name"],
                "tag": f"@{existing['name'] if existing else default_tag}",
                "tag_name": existing["name"] if existing else default_tag,
                "file_name": img["fileName"],
                "full_path": file_path,
                "width": img["width"],
                "height": img["height"],
                "is_tagged": existing is not None,
                "role": existing.get("role", "Character") if existing else "Unassigned",
                "description": existing.get("description", "") if existing else "",
                "personality": existing.get("personality", "") if existing else "",
                "rig_type": existing.get("rig_type", "puppet_pins") if existing else "none",
            }
            tagged_assets.append(asset_info)

        return tagged_assets

    def tag_project_asset(
        self,
        tag_name: str,
        description: str,
        role: str = "Character",
        personality: str = "",
        auto_rig: bool = True
    ) -> Dict[str, Any]:
        """
        Tags an asset from the active AE Project Panel, describes what it is to the AI,
        and automatically rigs it with Puppet Tool pins.
        """
        clean_tag = tag_name.lstrip("@").strip()
        manifest = self.scan_imported_assets()
        images = manifest.get("images", [])

        target_img = None
        for img in images:
            stem = Path(img["fullPath"]).stem.lower()
            if stem == clean_tag.lower() or img["fileName"].lower() == clean_tag.lower():
                target_img = img
                break

        if not target_img and images:
            for img in images:
                if clean_tag.lower() in img["fileName"].lower():
                    target_img = img
                    break
            if not target_img:
                target_img = images[0]

        if not target_img:
            return {"status": "error", "message": f"Asset '{tag_name}' not found in After Effects Project Panel."}

        file_path = target_img["fullPath"]
        display_name = clean_tag.title()

        landmarks_dict = {}
        if auto_rig and role.lower() in ["character", "actor", "hero", "villain", "mascot"]:
            try:
                landmarks = self.detector.detect(file_path, character_name=display_name)
                rig_script = CharacterRigBuilder.build_puppet_rig_script(landmarks)
                self.dispatcher.dispatch(rig_script, script_name_prefix=f"rig_{display_name}")
                landmarks_dict = landmarks.to_dict()["landmarks"]
            except Exception as e:
                logger.warning(f"Could not auto-rig {display_name}: {e}")

        # Save into memory
        char_entry = self.memory.register_character(
            name=display_name,
            image_path=file_path,
            landmarks=landmarks_dict,
            rig_type="puppet_pins" if landmarks_dict else "layer",
            layer_name=display_name,
            description=description,
            personality=personality,
            role=role
        )

        return {
            "status": "success",
            "tag": f"@{display_name}",
            "asset": char_entry,
            "message": f"Successfully tagged @{display_name} as '{role}' ({description})!"
        }

