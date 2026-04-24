"""YOLO-Master inference wrapper for pavement disease detection."""

import base64
import io
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

DISEASE_ADVICE = {
    "lmlj": {
        "name": "路面裂缝",
        "iron_rider": "引导车辆变道避让，布置防撞锥桶并疏导后方车流。",
        "drone": "路面出现明显裂缝病害，建议养护部门采用沥青灌缝工艺进行预防性密封处理。",
    },
    "hbgdf": {
        "name": "横斑/龟裂/断缝",
        "iron_rider": "对病害区域进行临时警戒，限制重型车辆通行并提示减速。",
        "drone": "路面出现龟裂与断缝交叉病害，判定基层承载力不足，建议挖除破损层后重建路面结构。",
    },
    "hxlf": {
        "name": "横向裂缝",
        "iron_rider": "加强该路段降雨期间的巡视，防止因渗水引发坑槽。",
        "drone": "判定为路面温度收缩引起的横向开裂，建议在换季前使用密封胶处理。",
    },
    "zxlf": {
        "name": "纵向裂缝",
        "iron_rider": "立即双向封锁该车道，布置防撞锥桶并疏导后方车流。",
        "drone": "判定为沥青面层疲劳开裂，建议养护部门采用沥青热灌缝工艺进行预防性密封。",
    },
    "jl": {
        "name": "井盖缺损",
        "iron_rider": "紧急在井盖位置布设反光锥桶与警示标志，防止车辆碾压造成事故。",
        "drone": "检测到井盖缺损或移位，存在车辆陷落风险，建议立即联系市政部门更换井盖。",
    },
    "kc": {
        "name": "坑槽",
        "iron_rider": "紧急封锁坑槽区域，防止车辆轮胎陷入造成二次事故。",
        "drone": "坑槽深度较大，建议采用铣刨机清除破损层，使用热沥青紧急重铺。",
    },
    "ssf": {
        "name": "松散/碎裂",
        "iron_rider": "清扫路面碎屑与松散骨料，设置临时减速警示标志。",
        "drone": "路面面层松散剥落，基层外露，建议铣刨后重新摊铺沥青混凝土面层。",
    },
    "CZ": {
        "name": "车辙",
        "iron_rider": "雨天重点巡查该区域，车辙积水易导致车辆打滑失控。",
        "drone": "检测到明显车辙变形，建议对变形路段进行铣刨罩面处理，恢复路面平整度。",
    },
}

DEFAULT_ADVICE = {
    "name": "未知病害",
    "iron_rider": "对异常区域进行临时警戒隔离，引导车辆减速绕行。",
    "drone": "检测到路面异常，建议派遣专业检测队伍进行现场勘查评估。",
}


def generate_advice(detections: list[dict]) -> str:
    if not detections:
        return "未检测到明显病害，路面状况良好。"

    lines = []
    for i, det in enumerate(detections, 1):
        cls = det["class_name"]
        conf = det["confidence"]
        info = DISEASE_ADVICE.get(cls, DEFAULT_ADVICE)
        display_name = info["name"]
        lines.append(f"【病害 {i}】{display_name}（置信度: {conf:.2f}）")
        lines.append(f"  铁骑行动：{info['iron_rider']}")
        lines.append(f"  无人机建议：{info['drone']}")
        lines.append("")

    return "\n".join(lines)


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
