import re
from pathlib import Path
from typing import List, Optional, Tuple


class LipSyncEngine:
    """Generates ExtendScript expressions and keyframes for automatic character lip-syncing."""

    @staticmethod
    def build_audio_driven_lipsync_script(
        char_name: str,
        audio_file_path: str,
        mouth_pin_index: int = 1,
        min_threshold: float = 2.0,
        max_threshold: float = 22.0,
        max_mouth_open_pixels: float = 25.0,
    ) -> str:
        """
        Generates ExtendScript to:
        1. Import speech audio file into After Effects.
        2. Convert Audio to Keyframes (creating 'Audio Amplitude' controller).
        3. Bind the character's Mouth Puppet Pin or Mouth layer vertical dimension to the loudness slider.
        """
        audio_path_js = Path(audio_file_path).as_posix().replace("'", "\\'")

        expression_code = f"""// Lip-Sync Expression linked to Audio Amplitude
var audioSlider = thisComp.layer("Audio Amplitude").effect("Both Channels")("Slider");
var openDelta = linear(audioSlider, {min_threshold}, {max_threshold}, 0, {max_mouth_open_pixels});
[value[0], value[1] + openDelta];"""

        jsx = f"""// Automated Audio-Driven Lip Sync for {char_name}
(function() {{
    app.beginUndoGroup("Lip Sync: {char_name}");
    try {{
        var comp = app.project.activeItem;
        if (!(comp && comp instanceof CompItem)) {{
            return JSON.stringify({{ status: "error", message: "No active composition found." }});
        }}

        // 1. Import audio file
        var io = new ImportOptions(File("{audio_path_js}"));
        var audioFootage = app.project.importFile(io);
        var audioLayer = comp.layers.add(audioFootage);
        audioLayer.name = "Dialogue_Audio";

        // 2. Select audio layer and Convert Audio to Keyframes
        // Menu command ID for "Convert Audio to Keyframes" is standard in AE
        for (var i = 1; i <= comp.layers.length; i++) {{
            comp.layers[i].selected = false;
        }}
        audioLayer.selected = true;

        var convertCommandId = app.findMenuCommandId("Convert Audio to Keyframes");
        if (convertCommandId) {{
            app.executeCommand(convertCommandId);
        }}

        // 3. Connect expression to Mouth Puppet Pin or Mouth layer
        var charLayer = comp.layer("{char_name}");
        if (!charLayer) {{
            return JSON.stringify({{ status: "error", message: "Character layer '{char_name}' not found." }});
        }}

        var puppet = charLayer.property("Effects").property("ADBE Puppet") || charLayer.property("Effects").property("Puppet");
        if (puppet) {{
            try {{
                var pins = puppet.property(1).property(1).property(1);
                var mouthPin = pins.property({mouth_pin_index});
                mouthPin.property("Position").expression = `{expression_code}`;
            }} catch(e) {{
                // Fallback to vertical scale
                charLayer.property("Scale").expression = `
                    var amp = thisComp.layer("Audio Amplitude").effect("Both Channels")("Slider");
                    var yMod = linear(amp, {min_threshold}, {max_threshold}, 100, 105);
                    [value[0], value[1] * (yMod / 100)];
                `;
            }}
        }} else {{
            // Scale fallback if no puppet effect
            charLayer.property("Scale").expression = `
                var amp = thisComp.layer("Audio Amplitude").effect("Both Channels")("Slider");
                var yMod = linear(amp, {min_threshold}, {max_threshold}, 100, 105);
                [value[0], value[1] * (yMod / 100)];
            `;
        }}

        return JSON.stringify({{
            status: "success",
            character: "{char_name}",
            audioFile: "{Path(audio_file_path).name}"
        }});
    }} catch(err) {{
        return JSON.stringify({{ status: "error", message: err.toString() }});
    }} finally {{
        app.endUndoGroup();
    }}
}})();
"""
        return jsx

    @staticmethod
    def build_text_dialogue_lipsync_script(
        char_name: str,
        dialogue_text: str,
        start_time: float = 0.0,
        words_per_minute: float = 140.0,
        mouth_pin_index: int = 1,
        mouth_open_pixels: float = 22.0,
    ) -> str:
        """
        Generates timed keyframe ExtendScript based on natural language dialogue text
        when no audio file is provided. Uses phonetic syllable timing.
        """
        # Parse dialogue into words
        words = re.findall(r"\w+|[^\w\s]", dialogue_text)
        seconds_per_word = 60.0 / words_per_minute

        current_time = start_time
        keyframe_statements = []

        for token in words:
            if token in (",", ";", "-", "—"):
                current_time += 0.25  # breath pause
                continue
            if token in (".", "!", "?"):
                current_time += 0.50  # sentence pause
                continue

            # Estimate syllables
            syllables = max(1, len(re.findall(r"[aeiouyAEIOUY]+", token)))
            syllable_dur = min(0.35, max(0.10, seconds_per_word / syllables))

            for _ in range(syllables):
                t_open = current_time + syllable_dur * 0.4
                t_close = current_time + syllable_dur * 0.85

                keyframe_statements.append(f"""
                mouthProp.setValueAtTime({round(current_time, 2)}, origMouthPos);
                mouthProp.setValueAtTime({round(t_open, 2)}, [origMouthPos[0], origMouthPos[1] + {mouth_open_pixels}]);
                mouthProp.setValueAtTime({round(t_close, 2)}, origMouthPos);
                """)
                current_time += syllable_dur

        keyframes_block = "\n".join(keyframe_statements)

        jsx = f"""// Text-Driven Syllable Lip Sync for {char_name}
(function() {{
    app.beginUndoGroup("Dialogue Lip Sync: {char_name}");
    try {{
        var comp = app.project.activeItem;
        if (!(comp && comp instanceof CompItem)) {{
            return JSON.stringify({{ status: "error", message: "No active composition found." }});
        }}

        var charLayer = comp.layer("{char_name}");
        if (!charLayer) {{
            return JSON.stringify({{ status: "error", message: "Layer '{char_name}' not found." }});
        }}

        var puppet = charLayer.property("Effects").property("ADBE Puppet") || charLayer.property("Effects").property("Puppet");
        if (puppet) {{
            var pins = puppet.property(1).property(1).property(1);
            var mouthPin = pins.property({mouth_pin_index});
            var mouthProp = mouthPin.property("Position");
            var origMouthPos = mouthProp.value;

            {keyframes_block}
        }}

        return JSON.stringify({{
            status: "success",
            character: "{char_name}",
            duration: {round(current_time - start_time, 2)}
        }});
    }} catch(err) {{
        return JSON.stringify({{ status: "error", message: err.toString() }});
    }} finally {{
        app.endUndoGroup();
    }}
}})();
"""
        return jsx
