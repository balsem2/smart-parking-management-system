from datetime import datetime, timezone

from app.models import Vehicle, VehicleStatus


def access_decision(vehicle: Vehicle | None) -> tuple[bool, str]:
    if vehicle is None:
        return False, "UNKNOWN_VEHICLE"
    if vehicle.status == VehicleStatus.BLACKLISTED:
        return False, "BLACKLISTED"
    if vehicle.status == VehicleStatus.EXPIRED:
        return False, "SUBSCRIPTION_EXPIRED"
    if vehicle.subscription_expires_at:
        expiry = vehicle.subscription_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < datetime.now(timezone.utc):
            return False, "SUBSCRIPTION_EXPIRED"
    if vehicle.status == VehicleStatus.VISITOR:
        return True, "VISITOR_ACCESS"
    return True, vehicle.status.value
