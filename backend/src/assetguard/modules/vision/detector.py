from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from PIL import Image

from assetguard.infrastructure.config import get_settings

logger = logging.getLogger("assetguard.vision")


@dataclass(frozen=True, slots=True)
class Detection:
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class Detector(Protocol):
    model_id: str
    def detect(self, image: Image.Image) -> list[Detection]: ...


class GroundingDinoDetector:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_id = settings.vision_model_id
        self.threshold = settings.vision_confidence_threshold
        self.classes = settings.vision_classes
        try:
            import torch
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        except ImportError as error:
            raise RuntimeError("Vision runtime is not installed. Run: pip install -e 'backend[vision]'") from error
        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("vision_model_loading model=%s device=%s", self.model_id, self.device)
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(self.model_id).to(self.device)
        self.model.eval()
        logger.info("vision_model_loaded model=%s device=%s", self.model_id, self.device)

    def detect(self, image: Image.Image) -> list[Detection]:
        prompt = ". ".join(self.classes) + "."
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device)
        with self._torch.no_grad():
            outputs = self.model(**inputs)
        result = self.processor.post_process_grounded_object_detection(
            outputs, inputs.input_ids, threshold=self.threshold,
            text_threshold=self.threshold, target_sizes=[image.size[::-1]],
        )[0]
        detections: list[Detection] = []
        labels = result.get("text_labels") or result["labels"]
        for score, label, box in zip(result["scores"], labels, result["boxes"]):
            class_name = str(label).lower().strip().removeprefix("a ").rstrip(".")
            if class_name not in self.classes:
                continue
            x1, y1, x2, y2 = (float(value) for value in box.tolist())
            detections.append(Detection(class_name, float(score), x1, y1, x2, y2))
        return detections


@lru_cache(maxsize=1)
def get_detector() -> Detector:
    return GroundingDinoDetector()
