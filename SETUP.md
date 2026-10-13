# Insurance Fraud Detection — Full Setup Guide

A complete, beginner-friendly walkthrough to get this project running from scratch on Windows, in VS Code. Follow the steps in order — each one assumes the previous one is done.

---

## What this project actually is

Three separate pieces work together:

1. **The ML model** — trained files on disk (`models/*.pkl`). You train this once.
2. **Postgres (database)** — stores a record every time a prediction is saved. Runs inside Docker.
3. **The API (FastAPI + uvicorn)** — the live program that loads the model and answers requests.

Think of it like a restaurant: the model is the recipe, Postgres is the receipt logbook, uvicorn is the kitchen that's actually open and cooking.

---

## 1. Prerequisites — install these first

| Tool | Why you need it | Check if installed |
|---|---|---|
| **Python 3.11+** | Runs the training code and the API | `python --version` |
| **VS Code** | Where you edit files and run terminal commands | already have it |
| **Docker Desktop** | Runs Postgres without installing it natively | `docker --version` |
| **Git** (optional) | Only if cloning/versioning the project | `git --version` |

If Docker Desktop isn't installed: download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop), install, restart if prompted, then open it from the Start menu and wait until it shows **"Docker Desktop is running"** (green status, whale icon stops animating in the system tray).

---

## 2. Open the project in VS Code

1. Extract the project zip somewhere, e.g. `D:\Projects\Claude-Insurance-Fraud-Detection`
2. `File → Open Folder` in VS Code, select that folder
3. Open the integrated terminal: `` Ctrl+` `` — this opens already `cd`'d into your project root

---

## 3. Create and activate a virtual environment

A venv keeps this project's Python packages separate from everything else on your machine.

```powershell
python -m venv venv
```

Activate it (PowerShell syntax — **not** `source`, that's bash-only):

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the script from running:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

You'll know it worked when your prompt shows `(venv)` at the start.

> **Note:** every *new* terminal tab needs this activation step again — it doesn't carry over between tabs.

---

## 4. Fix `requirements.txt` before installing

`matplotlib==3.9.1` was yanked from PyPI for Windows specifically (a bug caused its Windows wheels to be pulled), which forces pip to try building it from source — and that needs a C++ compiler most people don't have installed.

Neither `matplotlib` nor `seaborn` is actually used anywhere in this project's code, so just remove them:

Open `requirements.txt` in VS Code and delete these two lines:
```
matplotlib==3.9.1
seaborn==0.13.2
```

Save the file.

---

## 5. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

This should complete cleanly — everything else in the file has prebuilt Windows wheels.

---

## 6. Train the model

```powershell
python -m src.train
```

This loads `data/insurance_claims.csv` (1,000 rows), trains an XGBoost classifier and an Isolation Forest, and saves:
- Model files → `models/`
- Evaluation metrics → `reports/metrics.json`

Expected real-world numbers (not a target, this is what the model actually achieves):
```
accuracy: 0.77   recall: 0.43   f1: 0.47   roc_auc: 0.82   false_positive_rate: 0.13
```

---

## 7. Set up Postgres (the database)

### 7a. Create your `.env` file

```powershell
copy .env.example .env
```

This gives the app the database credentials it needs (`fraud_user` / `fraud_pass` / `fraud_detection`), matching what `docker-compose.yml` sets up automatically.

### 7b. Make sure nothing else is using port 5432

If you already have Postgres installed natively on Windows (common if you installed it once for another project), it will **block** the Docker container from being reachable, even though the container itself works fine. Check:

```powershell
Get-Service | Where-Object {$_.Name -like "*postgres*"}
```

If anything shows `Running`, open an **Administrator** PowerShell (right-click PowerShell → "Run as administrator", or in VS Code: terminal dropdown → "PowerShell (Run as Administrator)") and run:

```powershell
Stop-Service postgresql-x64-18    # use the actual service name shown above
Set-Service postgresql-x64-18 -StartupType Manual
```

This stops it from grabbing the port again on your next reboot.

### 7c. Start the Docker Postgres container

Back in your normal (venv-activated) terminal:

```powershell
docker compose up db -d
```

Verify it's running:

```powershell
docker ps
```

You should see `fraud_detection_db` with status `Up`/`healthy`. **You only need to run this once per work session** — it keeps running in the background after that.

---

## 8. Start the API server

```powershell
uvicorn app.main:app --reload --port 8000
```

Watch the startup log — you want to see:
```
[INFO] Database initialized.
INFO:     Application startup complete.
```

No warnings about failed database connections. This terminal now stays busy running the server — leave it open.

---

## 9. Test it

Open a **second terminal tab** (`+` icon in the terminal panel), activate the venv again (`.\venv\Scripts\Activate.ps1`), or just use your browser.

### Easiest way — Swagger UI

Open in your browser:
```
http://localhost:8000/docs
```

This is an interactive form for every endpoint — no need to write curl commands or fight PowerShell's quoting rules.

- Expand **`POST /predict/store`** → "Try it out" → paste a sample claim JSON → "Execute"
- Expand **`GET /predictions`** → "Try it out" → "Execute" → confirms it's saved in the database

### Sample claim JSON to use

```json
{
  "months_as_customer": 328,
  "age": 48,
  "policy_state": "OH",
  "policy_csl": "250/500",
  "policy_deductable": 1000,
  "policy_annual_premium": 1406.91,
  "umbrella_limit": 0,
  "insured_sex": "MALE",
  "insured_education_level": "MD",
  "insured_occupation": "craft-repair",
  "insured_hobbies": "sleeping",
  "insured_relationship": "husband",
  "capital-gains": 53300,
  "capital-loss": 0,
  "incident_type": "Single Vehicle Collision",
  "collision_type": "Side Collision",
  "incident_severity": "Major Damage",
  "authorities_contacted": "Police",
  "incident_state": "SC",
  "incident_city": "Columbus",
  "incident_hour_of_the_day": 5,
  "number_of_vehicles_involved": 1,
  "property_damage": "YES",
  "bodily_injuries": 1,
  "witnesses": 2,
  "police_report_available": "YES",
  "total_claim_amount": 71610,
  "injury_claim": 6510,
  "property_claim": 13020,
  "vehicle_claim": 52080,
  "auto_make": "Saab",
  "auto_model": "92x",
  "auto_year": 2004,
  "claim_id": "CLAIM-1001"
}
```

### Run the automated tests

```powershell
pytest tests/ -v
```

---

## 10. Every-day startup checklist (once everything above is done)

You don't repeat steps 1–7 every time. Each time you sit down to work:

1. Open Docker Desktop, wait for "running" status
2. Open VS Code, open a terminal, activate venv: `.\venv\Scripts\Activate.ps1`
3. `docker compose up db -d` (only needed if you'd shut it down previously)
4. `uvicorn app.main:app --reload --port 8000`
5. Open a second terminal tab for testing, or use `http://localhost:8000/docs`

### Shutting down

- `Ctrl+C` in the uvicorn terminal to stop the API
- `docker compose down` to stop Postgres (your data is safe — it lives in a Docker volume, not the container itself)

---

## Troubleshooting quick reference

| Symptom | Cause | Fix |
|---|---|---|
| `source: not recognized` | Using bash syntax in PowerShell | Use `.\venv\Scripts\Activate.ps1` instead |
| matplotlib build fails | Yanked Windows wheels for 3.9.1 | Remove matplotlib/seaborn from `requirements.txt` (unused in code anyway) |
| `password authentication failed for user "fraud_user"` | A native Postgres service is holding port 5432 instead of Docker | `Stop-Service postgresql-x64-18` (as Administrator) |
| `Cannot open 'postgresql-x64-18' service` | Not running PowerShell as Administrator | Reopen terminal as Administrator |
| `docker compose up` fails with "cannot connect to Docker API" | Docker Desktop isn't running | Open Docker Desktop, wait for it to fully start |
| curl JSON errors in PowerShell | PowerShell mangles escaped quotes | Use Swagger UI (`/docs`) instead, or save JSON to a file and use `curl.exe -d "@file.json"` |

---

## What's next

Once this is all working locally, the next steps are:
1. **Improve model recall** (currently 43%) via `scale_pos_weight` tuning and threshold sweeping
2. **Regenerate the project report** with real metrics and real diagrams instead of placeholders
3. **Deploy publicly** (AWS/Render/Fly.io) so the project is reachable from any device, not just `localhost`
