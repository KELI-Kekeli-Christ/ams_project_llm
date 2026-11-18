<p align="center">
  <a href="README.md"><b>English</b></a>
  &nbsp;·&nbsp;
  <a href="README.fr.md">Français</a>
  &nbsp;·&nbsp;
  <a href="README.es.md">Español</a>
</p>

# AMS Project Workspace

Overview
- Multi-component repository for the AMS hotel assistant project (LLM services, robot integrations, admin UI, services and tests).

Components
- `ams_project_llm`: FastAPI-based backend providing LLM-driven services, CRUD/db layer, schemas, QR/static assets. Uses `uvicorn` for serving and `SQLAlchemy` for DB access.
- `robot_hotel`: Robot-focused application (robot integration, LLM interactions, vision). Includes `main.py`, YOLO/face models and ML tooling.
- `admin`: Admin UI and utilities (admin app entrypoint at `admin/app.py`).
- `services`: Small service scripts used across the project (chat, email, face_detection, reservations, RAG, recording, Whisper integration).
- `pepper_test` / `packages_pepper`: Pepper robot test scripts and Pepper-specific packages.
- `tests`: Unit and integration tests with `pytest` and fixtures.
- `config`: Configuration files (email, etc.).
- `docs` and other project-level resources (hotel.json, plans, rules, workflow diagrams).

Key Functionality
- LLM services and index-based retrieval (document ingestion, RAG workflows, LlamaIndex integrations).
- Real-time WebSocket and HTTP APIs for chat and streaming (FastAPI + WebSockets + Uvicorn).
- Robot integrations (Pepper test scripts, robot control + conversation flows).
- Vision pipelines: face recognition, object detection (YOLOv8 / Ultralytics), OpenCV-based capture and processing.
- Speech processing: Whisper-based transcription and audio handling.
- Email sending and reservation automation.
- QR code generation and static assets delivery.
- Tests and CI-focused fixtures for unit/integration testing.

Technologies & Libraries (observed)
- Language & runtime: Python 3.12 (virtualenvs under `env/` in multiple folders)
- Web frameworks: FastAPI, Flask, Starlette
- ASGI server: Uvicorn (with uvloop)
- DB / ORM: SQLAlchemy, aiosqlite (async DB where used)
- Data validation: Pydantic
- Websockets: `websockets`, `httpx`, `aiohttp` where applicable
- LLM / embeddings / RAG: Llama-Index, OpenAI, Ollama, HuggingFace, transformers, sentence-transformers, tiktoken
- ML / DL frameworks: PyTorch, Triton (where present)
- Vision: OpenCV, face-recognition, Ultralytics (YOLOv8)
- Speech: Whisper (and wrapper scripts under `services/whisper.py`)
- Other: qrcode, PyYAML, python-dotenv, requests, pandas, scikit-learn, numpy

Where to find requirements
- `ams_project_llm/requirements.txt`
- `robot_hotel/requirement.txt`
- `admin/requirements.txt` (if present in that folder)

Quick Start (recommended order)
1. Create & activate a Python virtual environment (per component):

```bash
python -m venv env
source env/bin/activate
pip install -r ams_project_llm/requirements.txt
```

2. Run the LLM backend (from `ams_project_llm`):

```bash
cd ams_project_llm
uvicorn main:app --reload
```

3. Run the robot app (from `robot_hotel`):

```bash
cd ../robot_hotel
python main.py
```

4. Run the admin UI (if present):

```bash
cd ../admin
python app.py
```

5. Run tests from repository root:

```bash
pytest -q
```

Configuration
- Environment variables can be placed in `.env` files and `python-dotenv` is available.
- Mail settings: see `config/email_config.json`.

Notes & Next Steps
- Each component maintains its own `requirements.txt` and `env/` virtualenv; prefer installing only what you need for the component you will run.
- If you want, I can expand any component section with detailed run instructions, env var names, sample `.env` and common troubleshooting steps.

Contributing
- Open an issue or PR for changes. Run tests and ensure style consistency before submitting.

Contact
- Project files and scripts are in this workspace; point me to any file you want documented in more detail and I will update this README.
