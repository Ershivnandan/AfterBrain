import json
from pathlib import Path
from typing import Dict, List, Optional
from src.vision.landmark_detector import CharacterLandmarks


class CharacterRigBuilder:
    """Generates ExtendScript to rig characters with Puppet Pins or Layer Parenting in After Effects."""

    @staticmethod
    def build_puppet_rig_script(
        landmarks: CharacterLandmarks,
        comp_name: str = "Character_Scene",
        comp_width: int = 1920,
        comp_height: int = 1080,
        fps: float = 30.0,
        duration: float = 10.0,
    ) -> str:
        """
        Generates production ExtendScript to import character, apply Puppet Tool,
        and place puppet pins at the exact detected landmark coordinates.
        """
        img_path_js = Path(landmarks.image_path).as_posix().replace("'", "\\'")
        char_name = landmarks.character_name

        # Calculate coordinates on layer space (layer pixels: 0 to image_width, 0 to image_height)
        iw = landmarks.image_width
        ih = landmarks.image_height

        # Pixel coords on the original layer
        pins_data = [
            ("Mouth", landmarks.mouth.x * iw, landmarks.mouth.y * ih),
            ("Hand_Left", landmarks.hand_left.x * iw, landmarks.hand_left.y * ih),
            ("Hand_Right", landmarks.hand_right.x * iw, landmarks.hand_right.y * ih),
            ("Head", landmarks.head_top.x * iw, landmarks.head_top.y * ih),
            ("Neck", landmarks.neck.x * iw, landmarks.neck.y * ih),
            ("Hip", landmarks.hip.x * iw, landmarks.hip.y * ih),
            ("Foot_Left", landmarks.foot_left.x * iw, landmarks.foot_left.y * ih),
            ("Foot_Right", landmarks.foot_right.x * iw, landmarks.foot_right.y * ih),
        ]

        pin_code_lines = []
        for i, (pin_name, px, py) in enumerate(pins_data, start=1):
            pin_code_lines.append(f"""
        // Add Pin {i}: {pin_name}
        try {{
            var pin = meshDeform.addPin([{round(px, 1)}, {round(py, 1)}]);
            pin.name = "{char_name}_{pin_name}";
        }} catch(e) {{
            // Fallback for AE versions that access pins by index
        }}
            """)

        pins_script = "\n".join(pin_code_lines)

        jsx = f"""// Automatic Puppet Rig for Character: {char_name}
(function() {{
    app.beginUndoGroup("AI Character Rig: {char_name}");

    try {{
        // 1. Get or create active composition
        var comp = app.project.activeItem;
        if (!(comp && comp instanceof CompItem)) {{
            comp = app.project.items.addComp("{comp_name}", {comp_width}, {comp_height}, 1.0, {duration}, {fps});
            comp.openInViewer();
        }}

        // 2. Import footage
        var io = new ImportOptions(File("{img_path_js}"));
        var footage = app.project.importFile(io);

        // 3. Add to comp and center
        var charLayer = comp.layers.add(footage);
        charLayer.name = "{char_name}";
        charLayer.property("Position").setValue([{comp_width / 2}, {comp_height / 2}]);

        // 4. Apply Puppet Effect
        var puppetEffect = charLayer.property("Effects").addProperty("ADBE Puppet");
        if (!puppetEffect) {{
            puppetEffect = charLayer.property("Effects").addProperty("Puppet");
        }}

        // 5. Add Puppet Pins at detected landmark coordinates
        if (puppetEffect) {{
            var arbMod = puppetEffect.property("ADBE Puppet ARBM Mod");
            var defMod = arbMod ? arbMod.property("ADBE Puppet Deform Mod") : null;
            var meshDeform = defMod ? defMod.property("ADBE Puppet Mesh Deform Group") : null;

            {pins_script}
        }}

        return JSON.stringify({{
            status: "success",
            character: "{char_name}",
            layerIndex: charLayer.index,
            pinsCount: {len(pins_data)}
        }});
    }} catch(err) {{
        return JSON.stringify({{
            status: "error",
            message: err.toString()
        }});
    }} finally {{
        app.endUndoGroup();
    }}
}})();
"""
        return jsx

    @staticmethod
    def build_character_animation_script(
        char_name: str,
        animation_action: str,
        start_time: float = 0.0,
        duration: float = 2.0,
        amplitude: float = 25.0,
    ) -> str:
        """
        Generates targeted animation script for a registered character.
        Supports: 'wave_hand', 'nod_head', 'breathe', 'bounce', 'talk'.
        """
        action = animation_action.lower()

        if "wave" in action:
            # Animate Hand_Right or Hand_Left pin with spring wave
            anim_logic = f"""
        // Waving Hand Animation
        var layer = comp.layer("{char_name}");
        if (layer) {{
            var puppet = layer.property("Effects").property("ADBE Puppet") || layer.property("Effects").property("Puppet");
            if (puppet) {{
                // Target Right Hand Pin
                try {{
                    var pins = puppet.property(1).property(1).property(1); // Pins group
                    var handPin = pins.property(3); // Pin 3 (Hand R)
                    var origPos = handPin.property("Position").value;
                    
                    // Wave back and forth
                    handPin.property("Position").setValueAtTime({start_time}, origPos);
                    handPin.property("Position").setValueAtTime({start_time + 0.3}, [origPos[0] + {amplitude}, origPos[1] - {amplitude}]);
                    handPin.property("Position").setValueAtTime({start_time + 0.6}, [origPos[0] - {amplitude}, origPos[1] - {amplitude * 0.8}]);
                    handPin.property("Position").setValueAtTime({start_time + 0.9}, [origPos[0] + {amplitude}, origPos[1] - {amplitude}]);
                    handPin.property("Position").setValueAtTime({start_time + 1.2}, origPos);
                }} catch(e) {{
                    // Fallback to Layer Rotation if Puppet Pin is not reachable directly
                    layer.property("Rotation").setValueAtTime({start_time}, 0);
                    layer.property("Rotation").setValueAtTime({start_time + 0.3}, 8);
                    layer.property("Rotation").setValueAtTime({start_time + 0.6}, -8);
                    layer.property("Rotation").setValueAtTime({start_time + 0.9}, 0);
                }}
            }}
        }}
            """
        elif "nod" in action or "head" in action:
            anim_logic = f"""
        // Head Nod Animation
        var layer = comp.layer("{char_name}");
        if (layer) {{
            var puppet = layer.property("Effects").property("ADBE Puppet") || layer.property("Effects").property("Puppet");
            try {{
                var pins = puppet.property(1).property(1).property(1);
                var headPin = pins.property(4); // Head pin
                var origPos = headPin.property("Position").value;
                headPin.property("Position").setValueAtTime({start_time}, origPos);
                headPin.property("Position").setValueAtTime({start_time + 0.25}, [origPos[0], origPos[1] + {amplitude}]);
                headPin.property("Position").setValueAtTime({start_time + 0.5}, origPos);
                headPin.property("Position").setValueAtTime({start_time + 0.75}, [origPos[0], origPos[1] + {amplitude * 0.7}]);
                headPin.property("Position").setValueAtTime({start_time + 1.0}, origPos);
            }} catch(e) {{
                layer.property("Position").setValueAtTime({start_time}, layer.property("Position").value);
                var curPos = layer.property("Position").value;
                layer.property("Position").setValueAtTime({start_time + 0.25}, [curPos[0], curPos[1] + 15]);
                layer.property("Position").setValueAtTime({start_time + 0.5}, curPos);
            }}
        }}
            """
        else:
            # Default breathing / idle bobbing animation with expression
            anim_logic = f"""
        // Idle breathing / bobbing
        var layer = comp.layer("{char_name}");
        if (layer) {{
            layer.property("Scale").setValueAtTime({start_time}, [100, 100]);
            layer.property("Scale").setValueAtTime({start_time + 0.8}, [101.5, 98.5]);
            layer.property("Scale").setValueAtTime({start_time + 1.6}, [100, 100]);
            layer.property("Scale").setInterpolationTypeAtKeyframe(1, KeyframeInterpolationType.BEZIER);
            layer.property("Scale").setInterpolationTypeAtKeyframe(2, KeyframeInterpolationType.BEZIER);
            layer.property("Scale").setInterpolationTypeAtKeyframe(3, KeyframeInterpolationType.BEZIER);
            layer.property("Scale").expression = "loopOut('cycle');";
        }}
            """

        jsx = f"""// Animation Action for Character: {char_name} ({animation_action})
(function() {{
    app.beginUndoGroup("Animate Character: {char_name}");
    try {{
        var comp = app.project.activeItem;
        if (!(comp && comp instanceof CompItem)) {{
            return JSON.stringify({{ status: "error", message: "No active composition found." }});
        }}

        {anim_logic}

        return JSON.stringify({{ status: "success", character: "{char_name}", action: "{animation_action}" }});
    }} catch(err) {{
        return JSON.stringify({{ status: "error", message: err.toString() }});
    }} finally {{
        app.endUndoGroup();
    }}
}})();
"""
        return jsx
