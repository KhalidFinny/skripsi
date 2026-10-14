from dataclasses import dataclass, field
from typing import Any
import cv2
import dlib
import numpy as np
from shared.config import ComparisonConfig


@dataclass
class ROIExtractor:
    config: ComparisonConfig
    _detector: Any = field(init=False, repr=False)
    _predictor: Any = field(init=False, repr=False)
    def __post_init__(self) -> None:
        if not self.config.predictor_path.exists():
            raise FileNotFoundError(f"Predictor tidak ditemukan: {self.config.predictor_path}")
        self._detector = dlib.get_frontal_face_detector()
        self._predictor = dlib.shape_predictor(str(self.config.predictor_path))

    def extract_landmarks(self, image: np.ndarray) -> np.ndarray | None:
        """68 titik dlib (68x2, float64) pada wajah terbesar; None kalau tidak ada wajah.

        Dipakai keluarga fitur geometri (`features/geometry.py`).
        Deteksi wajahnya sama dengan `extract_rois` supaya ROI dan geometri
        selalu berasal dari landmark yang identik.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self._detector(gray)
        if len(faces) == 0:
            return None
        face = max(faces, key=lambda rect: rect.width() * rect.height())
        landmarks = self._predictor(gray, face)
        return np.asarray([(landmarks.part(i).x, landmarks.part(i).y) for i in range(68)], dtype=np.float64)

    def extract_rois_from_landmarks(self, image: np.ndarray, landmarks: np.ndarray) -> dict[str, np.ndarray]:
        """ROI dari landmark yang SUDAH dihitung (hindari deteksi wajah dua kali)."""
        output: dict[str, np.ndarray] = {}
        for region_name, indices in self.config.regions.items():
            roi = self._extract_region(image=image, landmarks=landmarks, indices=indices)
            if roi.size == 0:
                raise ValueError(f"Empty ROI for region: {region_name}")
            output[region_name] = cv2.resize(roi, self.config.target_size[region_name])
        return output

    def extract_rois(self, image: np.ndarray) -> dict[str, np.ndarray]:
        landmarks = self.extract_landmarks(image)
        if landmarks is None:
            raise ValueError("No face detected")
        return self.extract_rois_from_landmarks(image, landmarks)

    def _extract_region(self, image: np.ndarray, landmarks: np.ndarray, indices: list[int]) -> np.ndarray:
        pts = [(float(landmarks[i, 0]), float(landmarks[i, 1])) for i in indices]
        xs, ys = zip(*pts)

        left = max(0, int(min(xs)) - self.config.padding_x)
        top = max(0, int(min(ys)) - self.config.padding_y)
        right = min(image.shape[1], int(max(xs)) + self.config.padding_x)
        bottom = min(image.shape[0], int(max(ys)) + self.config.padding_y)

        return image[top:bottom, left:right]
