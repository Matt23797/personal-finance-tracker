# Finance Tracker Pro

A state-of-the-art personal finance management system built with Flask, featuring automated bank syncing, intelligent forecasting, and visual goal tracking.

## Premium Features

### Automated & Bulk Data Management
- **SimpleFin Integration**: Securely sync transactions from 10,000+ financial institutions.
- **Bulk Import**: Support for **OFX**, **QFX**, and **CSV** files with smart deduplication.
- **Smart Categorization**: Machine-learning style pattern matching that learns your categorization habits.

### Intelligence & Forecasting
- **90-Day Vision**: Advanced forecasting engine that projects your future balance based on:
    - 60-day historical "burn rate" (dynamic average).
    - Planned monthly income.
    - Active budget constraints and target goals.
- **Interactive Scenarios**: High-end Chart.js visualizations for scenario analysis.

### Visual Goal Tracking
- **Trajectory Progress**: Track your savings goals with a dynamic trajectory chart.
- **Smart Projections**: See exactly when you'll hit your milestones based on current trends.
- **Dynamic UI**: Fluid, responsive interface with hover-aware management tools.

### Desktop App Support
- **Standalone Executable**: Run the entire system as a native Windows application.
- **Auto-UI Launch**: Automatically opens your default web browser on startup.
- **Local Persistence**: Zero-config database stored right next to your application icon.

### Security & Resilience
- **Fernet Encryption**: Critical API keys are stored with military-grade symmetric encryption.
- **Persistence Layer**: Resilient to environment resets via `.env` based auto-reconnection.
- **JWT Authentication**: Full JSON Web Token security for API and State management.

## Deployment & Setup

### 1. Prerequisites
- Python 3.12+
- Nginx (for production)
- Linux/WSL environment

### 2. Quick Start
1. **Prepare Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configuration**:
   - `cp .env.template .env`
   - Set your `SECRET_KEY` and optional `SIMPLEFIN_TOKEN`.
3. **Database & Services**:
   - **Zero Configuration**: The app automatically creates and initializes its SQLite database (`finance.db`) on the first boot. No manual SQL setup is required.
   - Run in dev: `python app.py`
   - Run in prod: `gunicorn -c deploy/gunicorn_config.py "app:create_app()"`

### 3. Windows Executable Build
For users who prefer a desktop experience without managing Python:
1. Ensure Python 3.12+ is installed on Windows.
2. Run the automated build script:
   ```powershell
   python build_exe.py
   ```
3. Your standalone application will be ready in the `dist/FinanceTracker` directory. Just double-click `FinanceTracker.exe` to launch!

## Technical Architecture
- **Backend**: Flask + SQLAlchemy (Modular Blueprints)
- **Frontend**: Vanilla JS (Dynamic Components) + Chart.js
- **API**: RESTful architecture with JWT protection
- **Proxy**: Nginx handled via `deploy/finance.conf`

## Support

If this project helps you out, you can support its development here:
https://buymeacoffee.com/Matt23797

## 📄 License
MIT

