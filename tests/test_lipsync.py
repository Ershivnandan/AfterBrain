from src.audio.lipsync import LipSyncEngine
from src.extendscript.validator import ExtendScriptValidator


def test_audio_lipsync_script_generation():
    jsx = LipSyncEngine.build_audio_driven_lipsync_script(
        char_name="Hero",
        audio_file_path="d:/audio/speech.mp3",
        mouth_pin_index=1
    )

    assert "Hero" in jsx
    assert "Audio Amplitude" in jsx
    assert "Convert Audio to Keyframes" in jsx
    assert "app.beginUndoGroup" in jsx

    is_valid, msg = ExtendScriptValidator.validate(jsx)
    assert is_valid, f"Validation failed: {msg}"


def test_text_dialogue_lipsync_script_generation():
    jsx = LipSyncEngine.build_text_dialogue_lipsync_script(
        char_name="Hero",
        dialogue_text="Welcome to the future of animation!",
        start_time=1.0
    )

    assert "Hero" in jsx
    assert "mouthProp.setValueAtTime" in jsx
    assert "app.beginUndoGroup" in jsx

    is_valid, msg = ExtendScriptValidator.validate(jsx)
    assert is_valid, f"Validation failed: {msg}"
