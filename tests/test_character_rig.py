from pathlib import Path
from src.vision.landmark_detector import LandmarkDetector, Point2D, CharacterLandmarks
from src.character.memory import CharacterMemory
from src.character.rig_builder import CharacterRigBuilder
from src.extendscript.validator import ExtendScriptValidator


def test_character_memory_crud(tmp_path: Path):
    reg_file = tmp_path / "registry.json"
    memory = CharacterMemory(registry_path=reg_file)

    assert len(memory.list_characters()) == 0

    memory.register_character(
        name="Bob",
        image_path="test_bob.png",
        landmarks={"mouth": [0.5, 0.3]},
        rig_type="puppet_pins",
        description="Blue cartoon boy with sneakers",
        personality="Hyperactive and funny",
        role="Protagonist"
    )

    assert len(memory.list_characters()) == 1
    char = memory.get_character("Bob")
    assert char is not None
    assert char["name"] == "Bob"
    assert char["description"] == "Blue cartoon boy with sneakers"
    assert char["personality"] == "Hyperactive and funny"
    assert char["role"] == "Protagonist"
    
    prompt_ctx = memory.get_prompt_context()
    assert "Bob" in prompt_ctx
    assert "Hyperactive and funny" in prompt_ctx
    assert "Blue cartoon boy with sneakers" in prompt_ctx

    # Re-instantiate from file to test persistence
    memory2 = CharacterMemory(registry_path=reg_file)
    assert len(memory2.list_characters()) == 1
    assert memory2.get_character("Bob")["personality"] == "Hyperactive and funny"


def test_rig_builder_produces_valid_jsx():
    # Synthetic landmarks
    lm = CharacterLandmarks(
        character_name="TestChar",
        image_path="d:/assets/char.png",
        image_width=500,
        image_height=800,
        content_bbox=[50, 50, 450, 750],
        mouth=Point2D(0.5, 0.3),
        mouth_top=Point2D(0.5, 0.28),
        mouth_bottom=Point2D(0.5, 0.32),
        eye_left=Point2D(0.4, 0.22),
        eye_right=Point2D(0.6, 0.22),
        head_top=Point2D(0.5, 0.05),
        chin=Point2D(0.5, 0.38),
        neck=Point2D(0.5, 0.42),
        shoulder_left=Point2D(0.3, 0.45),
        shoulder_right=Point2D(0.7, 0.45),
        elbow_left=Point2D(0.2, 0.55),
        elbow_right=Point2D(0.8, 0.55),
        hand_left=Point2D(0.15, 0.65),
        hand_right=Point2D(0.85, 0.65),
        hip=Point2D(0.5, 0.68),
        foot_left=Point2D(0.35, 0.95),
        foot_right=Point2D(0.65, 0.95),
    )

    jsx = CharacterRigBuilder.build_puppet_rig_script(lm)
    assert "ADBE Puppet" in jsx
    assert "TestChar" in jsx
    assert "app.beginUndoGroup" in jsx
    assert "app.endUndoGroup" in jsx

    is_valid, msg = ExtendScriptValidator.validate(jsx)
    assert is_valid, f"Validation failed: {msg}"
