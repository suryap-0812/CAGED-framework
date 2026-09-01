# CAGED — Causal Analysis for Guaranteed Engagement Degradation

CAGED is a real-time statistical and algorithmic framework designed to continuously monitor privacy-safe user-engagement event streams and detect whether engagement degradation occurs following a social-platform policy adjustment.

---

## 🌟 Key Features & Architecture

- **Privacy-First Telemetry**: Measures privacy-safe behavioral metrics (likes, comments, shares, clicks, session durations, views) while explicitly excluding private messages, PII, and sensitive content.
- **High-Throughput Ingestion**: Asynchronous stream processing designed for low latency, structured with interfaces compatible with streaming message brokers like Apache Kafka.
- **Memory-Efficient Sketch Aggregation**: Integrates **Count-Min Sketch** for frequency estimation and **HyperLogLog** for approximate unique-user cardinality tracking.
- **Adaptive Baseline & Counterfactual Freezing**: Dynamically fits pre-policy engagement baselines (Exponential Smoothing / ARIMA) and freezes baseline states at policy trigger time $T_0$ to prevent contamination from post-policy degradation.
- **Multi-Metric Degradation Detector**: Computes standardized Z-score deviations and multi-metric composite degradation scores with statistically calibrated false-alarm controls.
- **Streaming User Segmentation**: Localizes degradation across user behavioral clusters (e.g. casual, regular, heavy, content-focused) using streaming online clustering.
- **Optional ML Forecasting**: Isolated XGBoost module for early post-policy degradation prediction without altering core statistical inference.
- **Full-Stack Monitoring**: FastAPI backend delivering REST APIs alongside a React + TypeScript interactive dashboard for real-time visualization.

---

## 🚀 Setup & Execution Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm

### 1. Backend Setup & Local Server Execution
```bash
# Create virtual environment and install dependencies
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

# Run pytest unit & health endpoint tests
PYTHONPATH=backend pytest -c backend/pytest.ini backend/tests

# Start FastAPI development backend server (runs on http://localhost:8000)
PYTHONPATH=backend backend/.venv/bin/python backend/app/main.py
```

### 2. Frontend Setup & Local Dev Server
```bash
# Install node dependencies
cd frontend
npm install

# Start Vite React frontend development server (runs on http://localhost:3000)
npm run dev

# Build for production & type-check
npm run build
```

---

## 📁 Repository Structure

```text
caged/
├── backend/                  # FastAPI Application & Statistical Core Engine
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint
│   │   ├── config.py         # App configuration & environment settings
│   │   ├── api/              # API routes & schema definitions
│   │   │   ├── routes/       # Endpoint handlers (health.py)
│   │   │   └── schemas/      # Pydantic schemas (health.py)
│   │   ├── core/             # Logging, security, exceptions
│   │   │   ├── logging.py    # Structured logging
│   │   │   └── exceptions.py # App exception handlers
│   │   ├── ingestion/        # Event stream producer/consumer
│   │   ├── preprocessing/    # Privacy filters & sanitization
│   │   ├── metrics/          # Time-window aggregations & rolling stats
│   │   ├── sketches/         # Count-Min Sketch & HyperLogLog
│   │   ├── baselines/        # Exponential smoothing & baseline models
│   │   ├── policy/           # Policy events, registry & frozen baselines
│   │   ├── detection/        # Z-score & multi-metric degradation detectors
│   │   ├── segmentation/     # User feature extraction & streaming clustering
│   │   ├── ml/               # Isolated XGBoost ML predictors
│   │   ├── reporting/        # Alerting & analytical report engines
│   │   ├── simulation/       # Synthetic platform event generator
│   │   ├── storage/          # Database persistence (SQLAlchemy / PostgreSQL)
│   │   └── services/         # Orchestration & workflow services
│   ├── tests/                # Pytest unit, statistical, & integration tests
│   └── requirements.txt      # Backend Python dependencies
│
├── frontend/                 # React + TypeScript + Vite Web Dashboard
│   ├── src/
│   │   ├── components/       # UI Header, Footer, navigation
│   │   ├── pages/            # HealthPage monitoring UI
│   │   ├── services/         # Axios API service client
│   │   ├── types/            # TypeScript interfaces
│   │   ├── App.tsx           # Router & page layout
│   │   └── main.tsx          # React DOM entrypoint
│   └── package.json          # Frontend npm dependencies
│
├── docs/                     # Documentation Directory
│   ├── architecture.md       # High-level system architecture & data model
│   ├── development-plan.md   # 20-phase development roadmap & dependency plan
│   └── Porject-document.md   # Complete domain specification & project background
│
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore configuration
└── README.md                 # Project README
```

---

## 📚 Documentation Links

- [System Architecture](docs/architecture.md)
- [Development Plan & Roadmap](docs/development-plan.md)
- [Complete Project Specification](docs/Porject-document.md)
