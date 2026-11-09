import json
import mimetypes
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.templating import Jinja2Templates

mimetypes.add_type("font/woff2", ".woff2")  # python:3.11-slim has no system MIME table, so fonts would go out as text/plain

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

FEATURES = ["temperature", "humidity", "pressure", "vibration", "rpm"]
# Scenario buttons on the live model. The first is the starting reading, so pages can render its answer without JS.
PRESETS = [
    ("Normal", {"temperature": 75, "humidity": 60, "pressure": 101, "vibration": 0.5, "rpm": 1500}),
    ("Running hot", {"temperature": 95, "humidity": 62, "pressure": 101, "vibration": 0.5, "rpm": 1500}),
    ("Hot & humid", {"temperature": 92, "humidity": 82, "pressure": 101, "vibration": 0.5, "rpm": 1500}),
    ("Shaking at high speed", {"temperature": 76, "humidity": 60, "pressure": 101, "vibration": 1.1, "rpm": 1900}),
]


def predict_reading(reading: dict) -> dict:
    """The /predict response for one sensor reading."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    features = np.array([[reading[name] for name in FEATURES]])
    no_defect, defect = model.predict_proba(features)[0].tolist()
    prediction = int(model.predict(features)[0])
    return {
        "prediction": prediction,
        "prediction_label": "Defect Likely" if prediction == 1 else "No Defect",
        "probability": {"no_defect": round(no_defect, 4), "defect": round(defect, 4)},
    }


NORMAL = predict_reading(PRESETS[0][1]) if model else None

# Single source of truth for every project fact shown on the site and in /api/projects.
# status_tone: "private" (employer-owned), "public" (inspectable), "progress" (in flight).
PROJECTS = [
    {
        "slug": "llm-ordering-platform",
        "name": "Production LLM Platform",
        "headline": "Conversational ordering for pharmaceutical distribution.",
        "summary": "Owned the build of a WhatsApp ordering assistant that pairs Azure OpenAI intent classification with a Snowflake-backed catalog of 1,500+ products and conversation logs. Deployed on Azure App Service, it has handled 10,000+ orders from about 1,000 pharmacies.",
        "trace_label": "System trace",
        "trace": ["WhatsApp inquiry", "Intent classification", "Product context", "Snowflake logs"],
        "metric": {"value": "10,000+", "label": "orders handled, from about 1,000 pharmacies", "short": "orders, ~1,000 pharmacies"},
        "context": "Data & AI Engineering Intern, Prowess Consulting",
        "tags": ["Azure OpenAI", "Snowflake", "Azure App Service", "CI/CD"],
        "status": "Employer-owned work",
        "status_tone": "private",
        "evidence": "Built during an industrial internship. The architecture, role, and scope are documented here.",
        "links": [],
        "decisions": [],
    },
    {
        "slug": "salesvitals",
        "name": "SalesVitals",
        "headline": "A sales analytics platform that briefs field reps before every call.",
        "summary": "A FastAPI customer-insights tool that shows pharmaceutical field reps a customer's full history before each call. Before it, every outreach was manual, with no view of the customer. Insights are served from a versioned SQLite snapshot, validated in GitHub Actions, instead of per-request warehouse reads.",
        "trace_label": "Delivery path",
        "trace": ["Warehouse data", "Versioned snapshot", "FastAPI", "Field insight"],
        "metric": {"value": "0", "label": "warehouse queries per rep request, served from a snapshot", "short": "warehouse queries per request"},
        "context": "Data & AI Engineering Intern, Prowess Consulting",
        "tags": ["FastAPI", "SQLite", "GitHub Actions"],
        "status": "Employer-owned work",
        "status_tone": "private",
        "evidence": "Built during an industrial internship. The delivery architecture and operating constraint are documented here.",
        "links": [],
        "decisions": [
            "Served insights from a versioned SQLite snapshot instead of live warehouse reads, trading data freshness for zero recurring query cost on the delivery path.",
            "Validated snapshots in GitHub Actions so a bad build fails before it reaches the field team.",
        ],
    },
    {
        "slug": "mortgage-pii",
        "name": "Mortgage PII Service",
        "headline": "Finds and redacts personal data in mortgage documents, and shows its evidence.",
        "summary": "A FastAPI service that detects and redacts 19 types of personal data in US mortgage and loan-servicing text, from SSNs and routing numbers to names and addresses. When matches overlap, checksums and rules outrank model confidence, and every rejected match comes back with its reason. Evaluated on synthetic documents, including held-out templates never used for tuning.",
        "trace_label": "Protection path",
        "trace": ["Mortgage text", "Rule + NER candidates", "Validate and rank", "Redacted output"],
        "metric": {"value": "0.977", "label": "strict micro-F1 on 2,070 labeled entities in held-out synthetic documents", "short": "micro-F1, held-out synthetic data"},
        "context": "Open source · synthetic data",
        "tags": ["Python", "FastAPI", "spaCy", "Presidio", "Docker"],
        "status": "Open source",
        "status_tone": "public",
        "evidence": "The repository includes the service, the demo page, the synthetic data generator, and an evaluation that runs in CI on every push.",
        "links": [{"label": "View repository", "href": "https://github.com/Harshil411/banking_PII", "external": True}],
        "decisions": [
            "Runs with networking disabled, so the text never leaves the machine.",
            "Ranks detections by evidence: a checksum that holds outranks a model's confidence, and every rejected candidate comes back with a reason.",
        ],
    },
    {
        "slug": "lstm-drl-trading",
        "name": "Hybrid LSTM + Deep RL Trading",
        "headline": "Forecasting, decision-making, and evaluation under uncertainty.",
        "summary": "A framework that separates forecasting from execution, combining LSTM models with PPO, DQN, and SAC agents, evaluated with risk-adjusted NIFTY-50 backtests.",
        "trace_label": "Decision loop",
        "trace": ["Market data", "LSTM forecast", "RL agent", "Backtest evaluation"],
        "metric": {"value": "~1.8", "label": "Sharpe ratio on NIFTY-50 backtests", "short": "Sharpe ratio, NIFTY-50"},
        "context": "IEEE ICCICT 2026, accepted paper",
        "tags": ["LSTM", "PPO", "DQN", "SAC"],
        "status": "Accepted paper",
        "status_tone": "progress",
        "evidence": "The paper is accepted at IEEE ICCICT 2026. This page records the project focus and backtest result.",
        "links": [],
        "decisions": [
            "Separated forecasting from execution so each stage can be evaluated on its own terms.",
        ],
    },
    {
        "slug": "defect-prediction",
        "name": "Manufacturing Defect Prediction",
        "headline": "From a trained model to an inspectable prediction interface.",
        "summary": "A Random Forest classifier served through FastAPI to demonstrate the full path from a trained model to a live, inspectable prediction interface. The training data is synthetic by design.",
        "trace_label": "Serving path",
        "trace": ["Sensor input", "FastAPI /predict", "Random Forest", "Probability"],
        "metric": {"value": f"{model_meta['accuracy']:.3f}", "label": "held-out accuracy on synthetic data", "short": "held-out accuracy"} if model_meta else None,
        "context": "Synthetic data · deployment and evaluation exercise",
        "tags": ["Python", "scikit-learn", "FastAPI", "Docker"],
        "status": "Live implementation",
        "status_tone": "public",
        "evidence": "Inspect the running model, held-out metrics, feature importances, and source code.",
        "links": [
            {"label": "Try the live model", "href": "/demo", "external": False},
            {"label": "View implementation", "href": "https://github.com/Harshil411/portfolio", "external": True},
        ],
        "decisions": [
            "Used synthetic data by design: the goal is to demonstrate serving, interface design, and honest evaluation, not to claim field performance.",
        ],
    },
]
for number, project in enumerate(PROJECTS, 1):
    project["no"] = f"{number:02d}"


def page(request: Request, name: str, title: str, status_code: int = 200, **context):
    live = {"presets": PRESETS, "normal": NORMAL, "model_meta": model_meta}
    return templates.TemplateResponse(name, {"request": request, "title": title, **live, **context}, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def not_found_page(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        return page(request, "404.html", "Not found", status_code=404)
    return await http_exception_handler(request, exc)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return page(request, "index.html", "Home", projects=PROJECTS)


@app.get("/demo", response_class=HTMLResponse)
async def demo(request: Request):
    # Exactly what `curl` prints for the Normal reading: FastAPI's compact JSON.
    return page(request, "demo.html", "Live model", api_example=json.dumps(NORMAL, separators=(",", ":")))


@app.get("/resume", response_class=HTMLResponse)
async def resume(request: Request):
    return page(request, "resume.html", "Resume")


# The old pages now live as sections of the home notebook.
@app.get("/projects", include_in_schema=False)
async def projects():
    return RedirectResponse("/#work", status_code=301)


@app.get("/contact", include_in_schema=False)
async def contact():
    return RedirectResponse("/#contact", status_code=301)


@app.get("/blog", include_in_schema=False)
async def blog():
    return RedirectResponse("/#work", status_code=307)


@app.post("/predict")
async def predict(
    # Bounds are generous physical limits; they turn junk input into a 422 instead of a model error.
    temperature: float = Form(..., ge=-50, le=200),
    humidity: float = Form(..., ge=0, le=100),
    pressure: float = Form(..., ge=0, le=300),
    vibration: float = Form(..., ge=0, le=10),
    rpm: float = Form(..., ge=0, le=10000),
):
    return predict_reading({"temperature": temperature, "humidity": humidity, "pressure": pressure, "vibration": vibration, "rpm": rpm})


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None}


@app.get("/api/projects")
async def api_projects():
    return PROJECTS
