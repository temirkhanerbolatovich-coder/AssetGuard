"""Exercise the configured real Grounding DINO model on a repository demo frame.

This is intentionally a runtime smoke test, not an accuracy benchmark: it proves
that model download, processor, inference and post-processing work together.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from assetguard.modules.vision.detector import GroundingDinoDetector


def main() -> None:
    image_path = Path(__file__).resolve().parents[2] / "demo" / "vision" / "room-305-baseline.png"
    if not image_path.is_file():
        raise FileNotFoundError(f"Demo image is missing: {image_path}")
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    detector = GroundingDinoDetector()
    detections = detector.detect(image)
    for item in detections:
        if not (0 <= item.confidence <= 1 and item.x2 >= item.x1 and item.y2 >= item.y1):
            raise RuntimeError(f"Invalid detector output: {item}")
    print(f"Grounding DINO smoke passed: model={detector.model_id}; detections={len(detections)}")


if __name__ == "__main__":
    main()
