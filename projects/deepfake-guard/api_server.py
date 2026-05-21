#!/usr/bin/env python3
"""DeepfakeGuard REST API 服务"""

import argparse
import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from deepfake_guard import DeepfakeDetector

app = FastAPI(title="DeepfakeGuard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = DeepfakeDetector()


class DetectionResponse(BaseModel):
    filename: str
    fake_probability: float
    anomaly_score: float
    verdict: str
    signals: List[str]
    frequency_score: float
    exif_score: float
    noise_score: float


class BatchResponse(BaseModel):
    total: int
    suspicious: int
    results: List[DetectionResponse]


@app.post("/detect", response_model=DetectionResponse)
async def detect_single(image: UploadFile = File(...)):
    """检测单张图像"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            content = await image.read()
            tmp.write(content)
            tmp.flush()
            result = detector.analyze(tmp.name)
        os.unlink(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")

    return DetectionResponse(
        filename=image.filename,
        fake_probability=round(result.fake_probability, 4),
        anomaly_score=round(result.anomaly_score, 4),
        verdict=result.verdict,
        signals=result.signals,
        frequency_score=round(result.frequency_score, 4),
        exif_score=round(result.exif_score, 4),
        noise_score=round(result.noise_score, 4),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DeepfakeGuard API Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8080, help="监听端口")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
