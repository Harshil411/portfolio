from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import joblib
import numpy as np
from pathlib import Path
import json

from starlette.templating import Jinja2Templates

app = FastAPI(title="Harshil Agrawal Portfolio", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Load model
model_path = BASE_DIR.parent / "ml" / "model.joblib"
model = None
model_meta = {}
if model_path.exists():
    bundle = joblib.load(model_path)
    model = bundle["model"]
    model_meta = bundle.get("meta", {})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Home"})

@app.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    return templates.TemplateResponse("projects.html", {"request": request, "title": "Projects"})

@app.get("/resume", response_class=HTMLResponse)
async def resume(request: Request):
    return templates.TemplateResponse("resume.html", {"request": request, "title": "Resume"})

@app.get("/blog", include_in_schema=False)
async def blog():
    return RedirectResponse("/projects", status_code=307)

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request, "title": "Contact"})

@app.get("/demo", response_class=HTMLResponse)
async def demo(request: Request):
    return templates.TemplateResponse(
        "demo.html",
        {"request": request, "title": "ML Demo", "model_meta": model_meta}
    )

@app.post("/predict")
async def predict(
    temperature: float = Form(...),
    humidity: float = Form(...),
    pressure: float = Form(...),
    vibration: float = Form(...),
    rpm: float = Form(...)
):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    features = np.array([[temperature, humidity, pressure, vibration, rpm]])
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0].tolist()
    return {
        "prediction": int(prediction),
        "prediction_label": "Defect Likely" if prediction == 1 else "No Defect",
        "probability": {
            "no_defect": round(probability[0], 4),
            "defect": round(probability[1], 4)
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None}

@app.get("/api/projects")
async def api_projects():
    projects = [
        {
            "name": "Production LLM Platform",
            "description": "LLM-powered WhatsApp ordering platform for pharmaceutical distribution",
            "tech": ["Azure App Service", "Azure OpenAI", "Snowflake", "Python"],
            "highlights": ["1,500+ product catalog", "24/7 automated ordering", "GitHub Actions CI/CD"]
        },
        {
            "name": "SalesVitals",
            "description": "FastAPI analytics stack with SQLite snapshot mode",
            "tech": ["FastAPI", "SQLite", "Azure OpenAI", "GitHub Actions"],
            "highlights": ["Eliminated recurring Snowflake costs", "Data-grounded talking scripts", "LFS validation"]
        },
        {
            "name": "Banking PII Protection",
            "description": "Local-first PII extraction and anonymization for sensitive banking text",
            "tech": ["FastAPI", "React", "Hugging Face", "Python"],
            "highlights": ["Multilingual transformer inference", "Schema-based entity validation", "Reported micro-F1: 0.84"]
        },
        {
            "name": "DRL Trading System",
            "description": "LSTM + Deep Reinforcement Learning for automated trading",
            "tech": ["LSTM", "PPO", "DQN", "SAC", "Python"],
            "highlights": ["NIFTY-50 backtests", "Sharpe ratio ~1.8", "IEEE ICCICT 2026"]
        },
        {
            "name": "Manufacturing Defect Prediction",
            "description": "Random Forest classifier with EDA and feature importance",
            "tech": ["Python", "Scikit-learn", "Pandas"],
            "highlights": ["Production-grade model serving", "Feature importance analysis", "Live demo available"]
        }
    ]
    return projects
