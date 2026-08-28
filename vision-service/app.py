import os
import tempfile
from functools import lru_cache
from pathlib import Path

import cv2
import httpx
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Security, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartPark Vision Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VEHICLE_LABELS = {"car", "motorcycle", "bus", "truck"}
MODEL_PATH = os.getenv("VISION_MODEL", "yolo11n.pt")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
OCR_LANGUAGES = [language.strip() for language in os.getenv("OCR_LANGUAGES", "en").split(",") if language.strip()]
vision_security = HTTPBearer(auto_error=False)
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_SAMPLES = 180


@lru_cache(maxsize=1)
def get_detector():
    from ultralytics import YOLO

    return YOLO(MODEL_PATH)


@lru_cache(maxsize=1)
def get_reader():
    import easyocr

    return easyocr.Reader(OCR_LANGUAGES, gpu=os.getenv("OCR_GPU", "false").lower() == "true")


def decode_image(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid image")
    return image


def read_plate_text(image: np.ndarray) -> str | None:
    reader = get_reader()
    results = reader.readtext(image, detail=1, paragraph=False)
    texts = [text.strip() for _, text, confidence in results if confidence >= 0.35 and text.strip()]
    return " ".join(texts) if texts else None


def detect_image(image: np.ndarray) -> list[dict]:
    detector = get_detector()
    result = detector.predict(source=image, verbose=False)[0]
    names = result.names
    detections = []

    for box in result.boxes:
        confidence = float(box.conf[0])
        label = names[int(box.cls[0])]
        if label not in VEHICLE_LABELS or confidence < 0.35:
            continue

        x1, y1, x2, y2 = [max(0, int(value)) for value in box.xyxy[0].tolist()]
        crop = image[y1:y2, x1:x2]
        detections.append({
            "vehicle_type": label,
            "confidence": round(confidence, 4),
            "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "plate_text": read_plate_text(crop) if crop.size else None,
        })
    return detections


def image_response(filename: str | None, image: np.ndarray, detections: list[dict]) -> dict:
    return {
        "filename": filename,
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
        "detections": detections,
    }


def detect_video(content: bytes, filename: str | None) -> dict:
    """Sample a short uploaded video until a readable vehicle plate is found."""
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded video is empty")
    if len(content) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="Video must be smaller than 100 MB")

    suffix = Path(filename or "parking-video.mp4").suffix or ".mp4"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        capture = cv2.VideoCapture(str(temp_path))
        if not capture.isOpened():
            raise HTTPException(status_code=422, detail="The uploaded file is not a valid video")

        frame_index = 0
        sampled = 0
        frame_step = max(1, int(capture.get(cv2.CAP_PROP_FPS) // 2) or 1)
        while sampled < MAX_VIDEO_SAMPLES:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % frame_step == 0:
                sampled += 1
                detections = detect_image(frame)
                if any(item.get("plate_text") for item in detections):
                    response = image_response(filename, frame, detections)
                    response.update({"media_type": "video", "frame_index": frame_index})
                    return response
            frame_index += 1
        raise HTTPException(status_code=422, detail="No readable vehicle plate was detected in the video")
    finally:
        if "capture" in locals():
            capture.release()
        if temp_path:
            temp_path.unlink(missing_ok=True)


def detected_plate(response: dict) -> str:
    plate = next((item.get("plate_text") for item in response["detections"] if item.get("plate_text")), None)
    if not plate:
        raise HTTPException(status_code=422, detail={"message": "No license plate was detected", "detection": response})
    return plate


async def send_parking_action(endpoint: str, payload: dict, credentials: HTTPAuthorizationCredentials, response: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        backend_response = await client.post(
            f"{BACKEND_URL}{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
    if not backend_response.is_success:
        detail = backend_response.json().get("detail", "Backend rejected the parking action")
        raise HTTPException(status_code=backend_response.status_code, detail={"message": detail, "detection": response})
    return backend_response.json()


@app.get("/")
def root():
    return {"message": "SmartPark Vision Service"}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_PATH, "model_exists": Path(MODEL_PATH).exists()}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file")

    image = decode_image(await file.read())
    return image_response(file.filename, image, detect_image(image))


@app.post("/detect-and-register")
async def detect_and_register(
    file: UploadFile = File(...),
    parking_spot_id: int = Form(...),
    credentials: HTTPAuthorizationCredentials | None = Security(vision_security),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file")
    if not credentials:
        raise HTTPException(status_code=401, detail="A backend Bearer token is required")

    image = decode_image(await file.read())
    response = image_response(file.filename, image, detect_image(image))
    plate = detected_plate(response)
    parking_entry = await send_parking_action("/parking-entries/by-plate", {"plate_text": plate, "parking_spot_id": parking_spot_id}, credentials, response)
    return {"detection": response, "parking_entry": parking_entry}


@app.post("/detect-and-exit")
async def detect_and_exit(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials | None = Security(vision_security),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file")
    if not credentials:
        raise HTTPException(status_code=401, detail="A backend Bearer token is required")

    image = decode_image(await file.read())
    response = image_response(file.filename, image, detect_image(image))
    plate = detected_plate(response)
    parking_exit = await send_parking_action("/parking-exits/by-plate", {"plate_text": plate}, credentials, response)
    return {"detection": response, "parking_exit": parking_exit}


@app.post("/detect-video-and-register")
async def detect_video_and_register(
    file: UploadFile = File(...),
    parking_spot_id: int = Form(...),
    credentials: HTTPAuthorizationCredentials | None = Security(vision_security),
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Upload a video file")
    if not credentials:
        raise HTTPException(status_code=401, detail="A backend Bearer token is required")

    response = detect_video(await file.read(), file.filename)
    plate = detected_plate(response)
    parking_entry = await send_parking_action("/parking-entries/by-plate", {"plate_text": plate, "parking_spot_id": parking_spot_id}, credentials, response)
    return {"detection": response, "parking_entry": parking_entry}


@app.post("/detect-video-and-exit")
async def detect_video_and_exit(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials | None = Security(vision_security),
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="Upload a video file")
    if not credentials:
        raise HTTPException(status_code=401, detail="A backend Bearer token is required")

    response = detect_video(await file.read(), file.filename)
    plate = detected_plate(response)
    parking_exit = await send_parking_action("/parking-exits/by-plate", {"plate_text": plate}, credentials, response)
    return {"detection": response, "parking_exit": parking_exit}
