FIRST_HOUR_RATE, ADDITIONAL_HOUR_RATE, DAILY_MAXIMUM_RATE = 2.0, 1.0, 15.0
def calculate_parking_fee(minutes: int) -> float:
    if minutes <= 0: return FIRST_HOUR_RATE
    days, remaining = divmod(minutes, 1440); total = days * DAILY_MAXIMUM_RATE
    if not remaining: return total
    if remaining <= 60: return total + FIRST_HOUR_RATE
    return total + min(FIRST_HOUR_RATE + ((remaining - 1) // 60) * ADDITIONAL_HOUR_RATE, DAILY_MAXIMUM_RATE)
