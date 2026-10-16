import datetime
import json
import re
from pathlib import Path
from typing import Dict, Any
from src.config import settings


class MockAEBridge:
    """Simulates After Effects execution and saves .jsx scripts to output_scripts directory."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or settings.output_scripts_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, jsx_code: str, script_name_prefix: str = "ai_anim") -> Dict[str, Any]:
        """
        Simulates execution of ExtendScript:
        - Saves the script to disk
        - Analyzes operations (Comps, Layers, Pins, Keyframes)
        - Returns a structured execution report
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{script_name_prefix}_{timestamp}.jsx"
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(jsx_code)

        # Parse operations from code using regex heuristics
        comps_added = re.findall(r'addComp\(["\'](.*?)["\']', jsx_code)
        layers_added = re.findall(r'layers\.add.*\(["\']?(.*?)["\']?\)', jsx_code)
        text_layers = re.findall(r'addText\(["\'](.*?)["\']\)', jsx_code)
        puppet_pins = re.findall(r'addPin\(\[(.*?)\]\)', jsx_code)
        expressions_applied = re.findall(r'\.expression\s*=\s*[`"\'](.*?)[`"\']', jsx_code, flags=re.DOTALL)

        simulated_layers = []
        for t in text_layers:
            simulated_layers.append({"type": "TextLayer", "content": t})
        for l in layers_added:
            if l:
                simulated_layers.append({"type": "FootageLayer", "name": l})
        if puppet_pins:
            simulated_layers.append({
                "type": "PuppetEffect",
                "pinsCount": len(puppet_pins),
                "coordinates": puppet_pins
            })

        return {
            "status": "success",
            "mode": "mock_simulation",
            "message": "Script validated and simulated successfully (After Effects Offline Mode).",
            "saved_script_path": str(file_path.resolve()),
            "simulation_details": {
                "compositions_created": comps_added or ["Active Comp"],
                "layers_manipulated": simulated_layers,
                "puppet_pins_placed": len(puppet_pins),
                "expressions_bound": len(expressions_applied),
                "undo_safe": "app.beginUndoGroup" in jsx_code and "app.endUndoGroup" in jsx_code,
            },
        }
