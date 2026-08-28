# SmartPark Vision Service

The Vision Service detects vehicles in uploaded images or short recorded videos and runs OCR on each detected vehicle crop. Video uploads are sampled frame-by-frame, so they can simulate an entry or exit camera for a demo.

## Run locally

```powershell
cd D:\smartpark-ai\vision-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8002 --reload
```

Endpoints:

- `GET /health` checks service availability and model configuration.
- `POST /detect` accepts an image multipart field named `file`.
- `POST /detect-video-and-register` accepts a video plus `parking_spot_id` and creates an entry.
- `POST /detect-video-and-exit` accepts a video and closes the matching active session.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8002/detect -F "file=@car.jpg"
```

The first inference downloads the configured YOLO model and EasyOCR assets. OCR output is a first integration result and needs plate-specific detection/training for production accuracy.

For the PFE demo, use a short MP4/WebM/MOV where the vehicle plate is visible for at least one second. The service samples up to 180 frames and accepts videos up to 100 MB.
