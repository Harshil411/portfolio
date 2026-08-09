# Harshil Agrawal — Portfolio & ML Demo

A minimal FastAPI portfolio website with a deployed Random Forest microservice. Built to demonstrate production ML serving, CI/CD, and containerization.

## Features

- **Portfolio pages** — Home, Projects, Resume, Blog, Contact
- **Live ML Demo** — Manufacturing Defect Prediction (Random Forest) via `/predict`
- **Production patterns** — FastAPI, Docker, GitHub Actions, Azure App Service deployment

## Stack

- FastAPI + Jinja2 + Tailwind CSS (CDN)
- scikit-learn Random Forest
- Docker
- GitHub Actions CI/CD
- Azure App Service (Free F1 tier)

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

1. Create an Azure App Service (Python 3.11, Free F1 tier) named `harshil-portfolio`.
2. Download the publish profile and add it as GitHub secret `AZURE_WEBAPP_PUBLISH_PROFILE`.
3. Push to `main` — GitHub Actions will train the model and deploy.

## Free Resource Notes

- Azure App Service Free (F1) tier: free forever, custom domain not included.
- Docker Hub / GitHub Container Registry: free tier.
- GitHub Actions: free for public repos.
- Tailwind CDN: free.

## Model

Random Forest trained on 5,000 synthetic manufacturing sensor samples. Features: temperature, humidity, pressure, vibration, RPM. Accuracy ~0.88.

## Next Steps

- Add blog post engine (Markdown-based)
- Add actual resume PDF download
- Add analytics (Azure Application Insights free tier)
- Add custom domain
