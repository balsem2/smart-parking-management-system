import os
from pathlib import Path

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL must be configured")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
