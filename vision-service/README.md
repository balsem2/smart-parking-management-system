# SmartPark Vision Service

The first vision-service slice detects vehicles in uploaded images and runs OCR on each detected vehicle crop.

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

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8002/detect -F "file=@car.jpg"
```

The first inference downloads the configured YOLO model and EasyOCR assets. OCR output is a first integration result and needs plate-specific detection/training for production accuracy.
