from datetime import datetime, timedelta, timezone


def create_vehicle(client, plate="123 TUN 4567", status="AUTHORIZED"):
    response = client.post("/api/v1/vehicles", json={
        "plate_number": plate, "owner_name": "Test Driver", "status": status
    })
    assert response.status_code == 201
    return response.json()


def test_complete_entry_exit_workflow(client):
    vehicle = create_vehicle(client)
    spot = client.post("/api/v1/parking/spots", json={"number": "A-01", "zone": "A", "floor": 0})
    assert spot.status_code == 201

    entry = client.post("/api/v1/events/access", json={
        "plate_number": "123 TUN 4567", "event_type": "ENTRY", "gate": "Gate A", "confidence": 0.95
    })
    assert entry.status_code == 200
    assert entry.json()["decision"] == "ALLOW"
    assert entry.json()["spot_number"] == "A-01"

    exit_response = client.post("/api/v1/events/access", json={
        "plate_number": "123 TUN 4567", "event_type": "EXIT", "gate": "Gate B"
    })
    assert exit_response.status_code == 200
    assert exit_response.json()["decision"] == "ALLOW"
    assert exit_response.json()["amount"] == 2.0
    assert client.get("/api/v1/parking/summary").json()["available"] == 1


def test_blacklisted_vehicle_is_denied_and_alert_created(client):
    create_vehicle(client, plate="111 TUN 9999", status="BLACKLISTED")
    response = client.post("/api/v1/events/access", json={
        "plate_number": "111 TUN 9999", "event_type": "ENTRY"
    })
    assert response.json()["decision"] == "DENY"
    assert response.json()["reason"] == "BLACKLISTED"
    alerts = client.get("/api/v1/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "CRITICAL"


def test_reservation_assigns_non_conflicting_spots(client):
    first = create_vehicle(client, "100 TUN 1000")
    second = create_vehicle(client, "200 TUN 2000")
    for number in ("A-01", "A-02"):
        client.post("/api/v1/parking/spots", json={"number": number, "zone": "A", "floor": 0})
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"start_time": start.isoformat(), "end_time": (start + timedelta(hours=2)).isoformat(), "zone": "A"}
    r1 = client.post("/api/v1/reservations", json={**payload, "vehicle_id": first["id"]})
    r2 = client.post("/api/v1/reservations", json={**payload, "vehicle_id": second["id"]})
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["spot_id"] != r2.json()["spot_id"]
