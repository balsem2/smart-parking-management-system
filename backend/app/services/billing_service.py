import math

from app.core.config import settings


def calculate_amount(duration_minutes: int) -> float:
    if duration_minutes <= 0:
        return 0.0
    hours = math.ceil(duration_minutes / 60)
    raw = settings.first_hour_rate + max(0, hours - 1) * settings.additional_hour_rate
    return round(min(raw, settings.daily_max_rate), 2)
