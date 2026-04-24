"""FastAPI backend for YOLO-Master pavement disease detection."""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from detect import YOLODetector

BACKEND_DIR = Path(__file__).parent
WEIGHTS_DIR = BACKEND_DIR / "weights"
IMAGES_DIR = BACKEND_DIR / "images"
FRONTEND_ASSETS = BACKEND_DIR.parent / "交科赛系统前端(1)" / "交科赛系统前端" / "transport-demo" / "src" / "assets"

detector = YOLODetector()


def find_weights() -> str | None:
    """Search for .pt weight files in the weights directory."""
    if WEIGHTS_DIR.exists():
        for f in WEIGHTS_DIR.glob("*.pt"):
            return str(f)
    return None


def find_image(image_id: int) -> bytes | None:
    """Find a preloaded crack image by ID, checking both backend/images and frontend assets."""
    for directory in [IMAGES_DIR, FRONTEND_ASSETS]:
        if not directory.exists():
            continue
        for pattern in [f"crack_{image_id}.*", f"crack_{image_id}_*"]:
            for f in directory.glob(pattern):
                if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                    return f.read_bytes()
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    weights_path = find_weights()
    print(f"[INFO] 权重文件路径: {weights_path or '未找到，将使用预训练模型'}")
    detector.load(weights_path)
    print("[INFO] YOLO 模型加载完成，服务就绪")
    yield


app = FastAPI(title="智巡速诊 - 病害检测 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "model_loaded": detector.model is not None}


@app.post("/api/detect")
async def detect_uploaded(file: UploadFile = File(...), conf: float = 0.15):
    """Accept an uploaded image and run YOLO inference."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="图片文件为空")

    try:
        result = detector.detect(image_bytes, conf_threshold=conf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    return JSONResponse(content=result)


@app.get("/api/detect-preloaded/{image_id}")
async def detect_preloaded(image_id: int, conf: float = 0.15):
    """Run YOLO inference on a preloaded crack image (crack_1 … crack_6 in assets or backend/images)."""
    image_bytes = find_image(image_id)
    if image_bytes is None:
        raise HTTPException(
            status_code=404,
            detail=f"预置图片 crack_{image_id} 未找到。请将图片放入 backend/images/ 或前端 src/assets/ 目录",
        )

    try:
        result = detector.detect(image_bytes, conf_threshold=conf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")

    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
