import json
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from src.server import (
    ae_get_system_status,
    ae_register_character,
    ae_animate_character,
    ae_lipsync_character,
    ae_generate_animation,
    ae_list_known_characters,
    ae_run_raw_extendscript,
)


@pytest.fixture
def test_character_png(tmp_path: Path) -> str:
    path = tmp_path / "alien_character.png"
    img = Image.new("RGBA", (300, 500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Alien green head
    draw.ellipse([90, 40, 210, 160], fill=(50, 220, 100, 255))
    # Big eyes
    draw.ellipse([110, 70, 140, 100], fill=(0, 0, 0, 255))
    draw.ellipse([160, 70, 190, 100], fill=(0, 0, 0, 255))
    # Mouth
    draw.rectangle([130, 120, 170, 135], fill=(20, 80, 40, 255))
    # Purple torso
    draw.rectangle([80, 160, 220, 340], fill=(120, 40, 180, 255))
    # Limbs
    draw.rectangle([30, 170, 80, 280], fill=(50, 220, 100, 255))
    draw.rectangle([220, 170, 270, 280], fill=(50, 220, 100, 255))
    draw.rectangle([100, 340, 140, 460], fill=(80, 20, 120, 255))
    draw.rectangle([160, 340, 200, 460], fill=(80, 20, 120, 255))

    img.save(path)
    return str(path)


def test_e2e_mcp_system_status():
    status_raw = ae_get_system_status()
    status = json.loads(status_raw)
    assert status["status"] == "ready"
    assert "ollama" in status
    assert "after_effects_bridge" in status
    assert "characters_registered" in status
    assert isinstance(status["ollama"]["ollama_connected"], bool)


@pytest.mark.ollama
def test_e2e_mcp_character_lifecycle(test_character_png: str):
    # 1. Register character
    reg_raw = ae_register_character(
        image_path=test_character_png,
        character_name="AlienBob"
    )
    reg = json.loads(reg_raw)
    assert reg["status"] == "success"
    assert "mouth" in reg["detected_landmarks"]

    # 2. Check list of known characters
    known_raw = ae_list_known_characters()
    known = json.loads(known_raw)
    assert any(c["name"] == "AlienBob" for c in known["characters"])

    # 3. Test lip-sync
    sync_raw = ae_lipsync_character(
        character_name="AlienBob",
        dialogue_text="Greetings humans! We come in peace."
    )
    sync = json.loads(sync_raw)
    assert sync["status"] == "success"

    # 4. Test deterministic/fallback animation
    anim_raw = ae_animate_character(
        character_name="AlienBob",
        action_prompt="wave right hand"
    )
    anim = json.loads(anim_raw)
    assert anim["status"] == "success"


def test_e2e_mcp_raw_extendscript():
    jsx = """app.beginUndoGroup("TestUndo");
var c = app.project.items.addComp("E2E_Comp", 1280, 720, 1, 3, 24);
app.endUndoGroup();"""

    res_raw = ae_run_raw_extendscript(jsx)
    res = json.loads(res_raw)
    assert res["status"] == "success"
