# Harshil Agrawal — Portfolio & ML Demo

A minimal FastAPI portfolio website with a deployed Random Forest microservice. Built to demonstrate production ML serving, CI/CD, and containerization.

## Features

- **Portfolio pages** — Home, Projects, Resume, Blog, Contact
- **Live ML Demo** — Manufacturing Defect Prediction (Random Forest) via `/predict`
- **Production patterns** — FastAPI, Docker, and Render deployment

## Stack

- FastAPI + Jinja2
- scikit-learn Random Forest
- Docker
- Render Web Service

## Quick Start

```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -r requirements.txt

# Train model
python ml/train_model.py

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## API

- `GET /` — Home page
- `GET /projects` — Projects page
- `GET /demo` — ML demo page
- `POST /predict` — Defect prediction endpoint
- `GET /health` — Health check
- `GET /api/projects` — Projects JSON

## Deployment

1. Create a Render Web Service using this repository and the Docker runtime.
2. Select the `main` branch and set the health-check path to `/health`.
3. Render automatically redeploys when changes are pushed to `main`.

## Free Resource Notes

- Render's free service tier spins down after inactivity, so the first request after idle time can take longer.

## Model

Random Forest trained on 5,000 synthetic manufacturing sensor samples. Features: temperature, humidity, pressure, vibration, RPM. Accuracy ~0.88.

## Next Steps

- Add blog post engine (Markdown-based)
- Add actual resume PDF download
- Add privacy-conscious analytics
- Add custom domain
