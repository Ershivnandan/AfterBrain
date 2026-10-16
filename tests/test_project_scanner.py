import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.bridge.project_scanner import ProjectScanner
from src.character.memory import CharacterMemory
from src.vision.landmark_detector import LandmarkDetector


def test_project_scanner_manifest_processing(tmp_path):
    # Create dummy character image
    dummy_img = tmp_path / "HeroBob.png"
    import numpy as np
    import cv2
    img_data = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(dummy_img), img_data)

    # Mock dispatcher and exchange file
    mock_dispatcher = MagicMock()
    mock_memory = CharacterMemory(registry_path=tmp_path / "test_reg.json")
    mock_detector = LandmarkDetector()

    scanner = ProjectScanner(dispatcher=mock_dispatcher, memory=mock_memory, detector=mock_detector)
    scanner.exchange_path = tmp_path / "project_assets_manifest.json"

    # Simulate AE writing the manifest file
    manifest_data = {
        "projectOpen": True,
        "projectName": "TestProject.aep",
        "images": [
            {
                "id": 1,
                "name": "HeroBob.png",
                "fileName": "HeroBob.png",
                "fullPath": str(dummy_img),
                "width": 100,
                "height": 100
            }
        ],
        "audio": []
    }
    with open(scanner.exchange_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    res = scanner.auto_register_imported_characters()
    assert res["status"] == "success"
    assert res["scanned_count"] == 1
    assert len(res["registered_characters"]) == 1
    assert res["registered_characters"][0]["name"] == "Herobob"

    # Verify character is saved in memory
    saved = mock_memory.get_character("Herobob")
    assert saved is not None
    assert saved["name"] == "Herobob"
    assert saved["rig_type"] == "puppet_pins"
