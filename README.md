z# SmartPark AI

Socle backend d'un système intelligent de gestion de parking : contrôle d'accès,
véhicules, places, sessions, réservations, tarification, alertes, analytics et
événements WebSocket.

## Démarrage rapide

### Docker (PostgreSQL + Redis + API)

```bash
docker compose up --build
```

Documentation interactive : <http://localhost:8000/docs>

### Développement local

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --reload
```

Sans variable d'environnement, l'API utilise SQLite (`smartpark.db`) et injecte
20 places ainsi que trois véhicules de démonstration.

## Flux principal

Envoyer une détection OCR à `POST /api/v1/events/access` :

```json
{
  "plate_number": "123 TUN 4567",
  "event_type": "ENTRY",
  "gate": "Gate A",
  "confidence": 0.95
}
```

Le moteur normalise la plaque, décide `ALLOW`/`DENY`, attribue une place,
ouvre ou ferme une session, calcule le tarif, crée les alertes nécessaires et
diffuse l'événement sur `ws://localhost:8000/api/v1/events/ws`.

## Vérification

```bash
cd backend
pytest -q
```

## Prochaines phases

- Authentification JWT et RBAC
- Dashboard React/TypeScript
- Service vision séparé (YOLO + OpenCV + OCR + tracking)
- Redis Pub/Sub pour plusieurs instances backend
- Alembic, CI/CD, Kubernetes, Prometheus et Grafana
