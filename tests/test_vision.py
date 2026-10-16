from pathlib import Path
from PIL import Image, ImageDraw
import pytest
from src.vision.landmark_detector import LandmarkDetector


@pytest.fixture
def sample_character_image(tmp_path: Path) -> Path:
    """Creates a sample cartoon character image with transparent background for testing."""
    img_path = tmp_path / "test_hero.png"
    # Create 400x600 RGBA image
    img = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw head (circle)
    draw.ellipse([140, 50, 260, 170], fill=(255, 220, 180, 255), outline=(0, 0, 0, 255))
    # Draw eyes
    draw.ellipse([170, 90, 190, 110], fill=(50, 50, 50, 255))
    draw.ellipse([210, 90, 230, 110], fill=(50, 50, 50, 255))
    # Draw mouth
    draw.rectangle([180, 130, 220, 145], fill=(200, 50, 50, 255))
    # Draw body / torso
    draw.rectangle([120, 180, 280, 400], fill=(50, 120, 220, 255))
    # Draw arms
    draw.rectangle([60, 200, 120, 350], fill=(255, 220, 180, 255))
    draw.rectangle([280, 200, 340, 350], fill=(255, 220, 180, 255))
    # Draw legs
    draw.rectangle([140, 400, 190, 560], fill=(30, 30, 30, 255))
    draw.rectangle([210, 400, 260, 560], fill=(30, 30, 30, 255))

    img.save(img_path)
    return img_path


def test_landmark_detector_finds_features(sample_character_image: Path):
    detector = LandmarkDetector()
    landmarks = detector.detect(str(sample_character_image), character_name="Hero")

    assert landmarks.character_name == "Hero"
    assert landmarks.image_width == 400
    assert landmarks.image_height == 600

    # Verify mouth coordinates exist and are within bounds (0.0 to 1.0)
    assert 0.0 <= landmarks.mouth.x <= 1.0
    assert 0.0 <= landmarks.mouth.y <= 1.0

    # Verify hands exist and left is to the left of right
    assert landmarks.hand_left.x < landmarks.hand_right.x

    # Verify comp scaling to 1920x1080
    comp_points = landmarks.get_comp_coordinates(1920, 1080)
    assert "mouth" in comp_points
    assert 0 <= comp_points["mouth"][0] <= 1920
    assert 0 <= comp_points["mouth"][1] <= 1080
