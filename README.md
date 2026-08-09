# Harshil Agrawal — Portfolio & ML Demo

A minimal FastAPI portfolio website with a deployed Random Forest microservice. Built to demonstrate production ML serving, CI/CD, and containerization.

## Features

- **Portfolio pages** — Home, Projects, Resume, Blog, Contact
- **Live ML Demo** — Manufacturing Defect Prediction (Random Forest) via `/predict`
- **Production patterns** — FastAPI, Docker, and Google Cloud deployment

## Stack

- FastAPI + Jinja2
- scikit-learn Random Forest
- Docker
- Google Compute Engine (Always Free)

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

### Google Cloud Always Free

1. Create an Ubuntu **e2-micro** VM in `us-west1`, `us-central1`, or `us-east1`, and allow inbound HTTP traffic.
2. SSH to the VM, then install Docker, Docker Compose, and Git:

   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2 git
   sudo systemctl enable --now docker
   ```

3. Clone this repository and start the app:

   ```bash
   git clone https://github.com/Harshil411/portfolio.git
   cd portfolio
   sudo docker compose up -d --build
   ```

4. Confirm the service is running at `http://YOUR_VM_IP/health`.

The included `compose.yaml` restarts the portfolio after a VM reboot. Keep the VM in the listed US regions and within the e2-micro/disk/egress free-tier limits. Add a domain and HTTPS only when needed.

### Render

Render remains available for simple managed deployments, but its free service tier spins down after inactivity.

## Model

Random Forest trained on 5,000 synthetic manufacturing sensor samples. Features: temperature, humidity, pressure, vibration, RPM. Accuracy ~0.88.

## Next Steps

- Add blog post engine (Markdown-based)
- Add actual resume PDF download
- Add privacy-conscious analytics
- Add custom domain
