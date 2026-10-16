from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image


@dataclass
class Point2D:
    x: float
    y: float

    def to_list(self) -> List[float]:
        return [round(self.x, 2), round(self.y, 2)]

    def to_ae_point(self, comp_width: int, comp_height: int) -> List[float]:
        """Convert normalized (0-1) coordinates to After Effects comp pixels."""
        return [round(self.x * comp_width, 2), round(self.y * comp_height, 2)]


@dataclass
class CharacterLandmarks:
    character_name: str
    image_path: str
    image_width: int
    image_height: int
    # Bounding box of non-transparent character content [x_min, y_min, x_max, y_max]
    content_bbox: List[int]

    # Facial landmarks (relative 0.0 - 1.0 within image)
    mouth: Point2D
    mouth_top: Point2D
    mouth_bottom: Point2D
    eye_left: Point2D
    eye_right: Point2D
    head_top: Point2D
    chin: Point2D

    # Body joints (relative 0.0 - 1.0 within image)
    neck: Point2D
    shoulder_left: Point2D
    shoulder_right: Point2D
    elbow_left: Point2D
    elbow_right: Point2D
    hand_left: Point2D
    hand_right: Point2D
    hip: Point2D
    foot_left: Point2D
    foot_right: Point2D

    confidence_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "character_name": self.character_name,
            "image_path": str(self.image_path),
            "image_size": [self.image_width, self.image_height],
            "content_bbox": self.content_bbox,
            "landmarks": {
                "mouth": self.mouth.to_list(),
                "mouth_top": self.mouth_top.to_list(),
                "mouth_bottom": self.mouth_bottom.to_list(),
                "eye_left": self.eye_left.to_list(),
                "eye_right": self.eye_right.to_list(),
                "head_top": self.head_top.to_list(),
                "chin": self.chin.to_list(),
                "neck": self.neck.to_list(),
                "shoulder_left": self.shoulder_left.to_list(),
                "shoulder_right": self.shoulder_right.to_list(),
                "elbow_left": self.elbow_left.to_list(),
                "elbow_right": self.elbow_right.to_list(),
                "hand_left": self.hand_left.to_list(),
                "hand_right": self.hand_right.to_list(),
                "hip": self.hip.to_list(),
                "foot_left": self.foot_left.to_list(),
                "foot_right": self.foot_right.to_list(),
            },
            "confidence_scores": self.confidence_scores,
        }

    def get_comp_coordinates(self, comp_width: int, comp_height: int) -> Dict[str, List[float]]:
        """Maps relative landmarks to After Effects composition space."""
        return {
            "mouth": self.mouth.to_ae_point(comp_width, comp_height),
            "mouth_top": self.mouth_top.to_ae_point(comp_width, comp_height),
            "mouth_bottom": self.mouth_bottom.to_ae_point(comp_width, comp_height),
            "eye_left": self.eye_left.to_ae_point(comp_width, comp_height),
            "eye_right": self.eye_right.to_ae_point(comp_width, comp_height),
            "head_top": self.head_top.to_ae_point(comp_width, comp_height),
            "chin": self.chin.to_ae_point(comp_width, comp_height),
            "neck": self.neck.to_ae_point(comp_width, comp_height),
            "shoulder_left": self.shoulder_left.to_ae_point(comp_width, comp_height),
            "shoulder_right": self.shoulder_right.to_ae_point(comp_width, comp_height),
            "elbow_left": self.elbow_left.to_ae_point(comp_width, comp_height),
            "elbow_right": self.elbow_right.to_ae_point(comp_width, comp_height),
            "hand_left": self.hand_left.to_ae_point(comp_width, comp_height),
            "hand_right": self.hand_right.to_ae_point(comp_width, comp_height),
            "hip": self.hip.to_ae_point(comp_width, comp_height),
            "foot_left": self.foot_left.to_ae_point(comp_width, comp_height),
            "foot_right": self.foot_right.to_ae_point(comp_width, comp_height),
        }


class LandmarkDetector:
    """Detects facial features and body joints on arbitrary cartoon/character images."""

    def __init__(self):
        # Load OpenCV default cascades for face/eye/smile detection if available in this cv2 build
        self.face_cascade = None
        self.eye_cascade = None
        self.smile_cascade = None

        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            try:
                cv_data_path = cv2.data.haarcascades
                self.face_cascade = cv2.CascadeClassifier(cv_data_path + "haarcascade_frontalface_default.xml")
                self.eye_cascade = cv2.CascadeClassifier(cv_data_path + "haarcascade_eye.xml")
                self.smile_cascade = cv2.CascadeClassifier(cv_data_path + "haarcascade_smile.xml")
            except Exception:
                pass

    def detect(self, image_path: str, character_name: str = "character") -> CharacterLandmarks:
        """Analyze character image and extract anatomical landmarks."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found at: {image_path}")

        # Open with PIL to safely check dimensions and alpha channel
        pil_img = Image.open(path)
        width, height = pil_img.size

        # Find non-transparent bounding box
        content_bbox = self._get_content_bounding_box(pil_img)
        bx0, by0, bx1, by1 = content_bbox
        bw = max(1, bx1 - bx0)
        bh = max(1, by1 - by0)

        # Convert to OpenCV image (BGR and Grayscale)
        rgb_img = np.array(pil_img.convert("RGB"))
        gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)

        # Attempt OpenCV face/eye detection on the cropped non-transparent region if available
        faces = []
        if self.face_cascade is not None:
            try:
                face_crop = gray[by0:by1, bx0:bx1]
                faces = self.face_cascade.detectMultiScale(face_crop, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            except Exception:
                faces = []

        confidence: Dict[str, float] = {}

        if len(faces) > 0 and self.eye_cascade is not None and self.smile_cascade is not None:
            # Face found by cascade
            fx, fy, fw, fh = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
            # Convert crop coords back to full image coords
            fx_abs = bx0 + fx
            fy_abs = by0 + fy

            face_roi_gray = gray[fy_abs : fy_abs + fh, fx_abs : fx_abs + fw]
            try:
                eyes = self.eye_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.1, minNeighbors=3)
            except Exception:
                eyes = []
            try:
                smiles = self.smile_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.5, minNeighbors=10)
            except Exception:
                smiles = []

            # Eyes
            if len(eyes) >= 2:
                sorted_eyes = sorted(eyes, key=lambda e: e[0])
                e_left = (fx_abs + sorted_eyes[0][0] + sorted_eyes[0][2] / 2) / width
                e_left_y = (fy_abs + sorted_eyes[0][1] + sorted_eyes[0][3] / 2) / height
                e_right = (fx_abs + sorted_eyes[-1][0] + sorted_eyes[-1][2] / 2) / width
                e_right_y = (fy_abs + sorted_eyes[-1][1] + sorted_eyes[-1][3] / 2) / height
                eye_l = Point2D(e_left, e_left_y)
                eye_r = Point2D(e_right, e_right_y)
                confidence["eyes"] = 0.90
            else:
                eye_l = Point2D((fx_abs + fw * 0.35) / width, (fy_abs + fh * 0.45) / height)
                eye_r = Point2D((fx_abs + fw * 0.65) / width, (fy_abs + fh * 0.45) / height)
                confidence["eyes"] = 0.70

            # Mouth
            if len(smiles) > 0:
                sx, sy, sw, sh = sorted(smiles, key=lambda s: s[2] * s[3], reverse=True)[0]
                m_x = (fx_abs + sx + sw / 2) / width
                m_y = (fy_abs + sy + sh / 2) / height
                mouth_pt = Point2D(m_x, m_y)
                mouth_top = Point2D(m_x, (fy_abs + sy) / height)
                mouth_bot = Point2D(m_x, (fy_abs + sy + sh) / height)
                confidence["mouth"] = 0.92
            else:
                m_x = (fx_abs + fw * 0.5) / width
                m_y = (fy_abs + fh * 0.78) / height
                mouth_pt = Point2D(m_x, m_y)
                mouth_top = Point2D(m_x, m_y - (fh * 0.05) / height)
                mouth_bot = Point2D(m_x, m_y + (fh * 0.05) / height)
                confidence["mouth"] = 0.75

            head_top = Point2D((fx_abs + fw * 0.5) / width, fy_abs / height)
            chin = Point2D((fx_abs + fw * 0.5) / width, (fy_abs + fh) / height)
            neck = Point2D((fx_abs + fw * 0.5) / width, (fy_abs + fh * 1.05) / height)
            confidence["face"] = 0.95
        else:
            # Stylized / Cartoon Proportional Fallback Engine
            # Anthropometric canon for cartoon & character illustrations
            confidence["face"] = 0.65
            confidence["mouth"] = 0.65
            confidence["eyes"] = 0.65

            head_cx = (bx0 + bw * 0.5) / width
            head_top_y = (by0 + bh * 0.02) / height
            head_top = Point2D(head_cx, head_top_y)

            # Eyes typically at ~22% of character height
            eye_y = (by0 + bh * 0.22) / height
            eye_l = Point2D((bx0 + bw * 0.38) / width, eye_y)
            eye_r = Point2D((bx0 + bw * 0.62) / width, eye_y)

            # Mouth at ~32% of character height
            mouth_y = (by0 + bh * 0.32) / height
            mouth_pt = Point2D(head_cx, mouth_y)
            mouth_top = Point2D(head_cx, mouth_y - 0.02)
            mouth_bottom = Point2D(head_cx, mouth_y + 0.02)
            mouth_bot = mouth_bottom

            chin = Point2D(head_cx, (by0 + bh * 0.38) / height)
            neck = Point2D(head_cx, (by0 + bh * 0.42) / height)

        # Body & Limb Landmarks using Character Silhouette geometry
        confidence["body"] = 0.80
        center_x = (bx0 + bw * 0.5) / width

        shoulder_y = (by0 + bh * 0.44) / height
        shoulder_l = Point2D((bx0 + bw * 0.28) / width, shoulder_y)
        shoulder_r = Point2D((bx0 + bw * 0.72) / width, shoulder_y)

        elbow_y = (by0 + bh * 0.55) / height
        elbow_l = Point2D((bx0 + bw * 0.20) / width, elbow_y)
        elbow_r = Point2D((bx0 + bw * 0.80) / width, elbow_y)

        hand_y = (by0 + bh * 0.65) / height
        hand_l = Point2D((bx0 + bw * 0.15) / width, hand_y)
        hand_r = Point2D((bx0 + bw * 0.85) / width, hand_y)

        hip_y = (by0 + bh * 0.68) / height
        hip = Point2D(center_x, hip_y)

        foot_y = (by0 + bh * 0.96) / height
        foot_l = Point2D((bx0 + bw * 0.35) / width, foot_y)
        foot_r = Point2D((bx0 + bw * 0.65) / width, foot_y)

        return CharacterLandmarks(
            character_name=character_name,
            image_path=str(path.resolve()),
            image_width=width,
            image_height=height,
            content_bbox=content_bbox,
            mouth=mouth_pt,
            mouth_top=mouth_top,
            mouth_bottom=mouth_bot,
            eye_left=eye_l,
            eye_right=eye_r,
            head_top=head_top,
            chin=chin,
            neck=neck,
            shoulder_left=shoulder_l,
            shoulder_right=shoulder_r,
            elbow_left=elbow_l,
            elbow_right=elbow_r,
            hand_left=hand_l,
            hand_right=hand_r,
            hip=hip,
            foot_left=foot_l,
            foot_right=foot_r,
            confidence_scores=confidence,
        )

    def _get_content_bounding_box(self, img: Image.Image) -> List[int]:
        """Calculates non-transparent pixel bounding box [x0, y0, x1, y1]."""
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            alpha = np.array(img.convert("RGBA"))[:, :, 3]
            non_zero = np.argwhere(alpha > 10)
            if non_zero.size > 0:
                y0, x0 = non_zero.min(axis=0)
                y1, x1 = non_zero.max(axis=0)
                return [int(x0), int(y0), int(x1), int(y1)]

        # If opaque, return full image bounds
        return [0, 0, img.width, img.height]
