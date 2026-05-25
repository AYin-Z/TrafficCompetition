"""YOLO-Master inference wrapper for pavement disease detection."""

import base64
import io
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

from .disease_advice import generate_advice


class YOLODetector:
    def __init__(self, weights_path: str | None = None):
        self.model = None
        self.weights_path = weights_path

    def load(self, weights_path: str | None = None):
        path = weights_path or self.weights_path
        if path and Path(path).exists():
            self.model = YOLO(path)
        else:
            self.model = YOLO("yolov8n.pt")
            print(f"[WARN] 权重文件未找到 ({path})，使用 yolov8n 预训练模型作为演示")

    def detect(self, image_bytes: bytes, conf_threshold: float = 0.25) -> dict:
        if self.model is None:
            raise RuntimeError("模型未加载，请先调用 load()")

        img_array = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("无法解码图片")

        results = self.model(img, conf=conf_threshold, verbose=False)
        result = results[0]

        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append({
                "class_name": cls_name,
                "confidence": round(confidence, 4),
                "bbox": [round(x1), round(y1), round(x2), round(y2)],
            })

        annotated = result.plot()
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        annotated_b64 = base64.b64encode(buffer).decode("utf-8")

        advice = generate_advice(detections)

        return {
            "annotated_image": annotated_b64,
            "detections": detections,
            "summary": advice,
            "count": len(detections),
        }
