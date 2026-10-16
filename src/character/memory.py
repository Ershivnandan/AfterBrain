import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class CharacterMemory:
    """Persistent storage for rigged characters, layer mappings, and pin coordinates."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or settings.character_registry_path
        self._registry: Dict[str, Dict] = {}
        self.load()

    def load(self) -> None:
        """Loads registered characters from JSON file."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    self._registry = json.load(f)
            except Exception as e:
                logger.error(f"Error loading character registry: {e}")
                self._registry = {}
        else:
            self._registry = {}

    def save(self) -> None:
        """Saves registered characters to JSON file."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self._registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving character registry: {e}")

    def register_character(
        self,
        name: str,
        image_path: str,
        landmarks: Dict,
        rig_type: str = "puppet_pins",
        pin_mapping: Optional[Dict[str, str]] = None,
        layer_name: Optional[str] = None,
    ) -> Dict:
        """Stores or updates a character in memory."""
        character_entry = {
            "name": name,
            "image_path": str(Path(image_path).resolve()),
            "layer_name": layer_name or Path(image_path).name,
            "rig_type": rig_type,
            "landmarks": landmarks,
            "pin_mapping": pin_mapping or {
                "mouth": "Pin 1 (Mouth)",
                "hand_left": "Pin 2 (Hand L)",
                "hand_right": "Pin 3 (Hand R)",
                "head": "Pin 4 (Head)",
                "neck": "Pin 5 (Neck)",
                "hip": "Pin 6 (Hip)",
                "foot_left": "Pin 7 (Foot L)",
                "foot_right": "Pin 8 (Foot R)",
            },
            "updated_at": datetime.now().isoformat(),
        }
        self._registry[name] = character_entry
        self.save()
        return character_entry

    def get_character(self, name: str) -> Optional[Dict]:
        """Retrieves character by name."""
        return self._registry.get(name)

    def list_characters(self) -> List[Dict]:
        """Returns all registered characters."""
        return list(self._registry.values())

    def delete_character(self, name: str) -> bool:
        """Removes character from memory."""
        if name in self._registry:
            del self._registry[name]
            self.save()
            return True
        return False

    def get_prompt_context(self) -> str:
        """Generates a concise markdown summary for the LLM system prompt."""
        if not self._registry:
            return "No characters currently registered in Character Memory."

        lines = ["### Registered Characters in After Effects Memory:"]
        for name, char in self._registry.items():
            lines.append(f"\n- **Character Name**: `{name}`")
            lines.append(f"  - **Layer in AE**: `{char.get('layer_name')}`")
            lines.append(f"  - **Rig Type**: `{char.get('rig_type')}`")
            lines.append(f"  - **Available Pins / Joints to Animate**:")
            pins = char.get("pin_mapping", {})
            for part, pin_name in pins.items():
                lines.append(f"    - `{part}` -> Target Pin: `{pin_name}`")
        return "\n".join(lines)
