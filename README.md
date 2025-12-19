<<<<<<< HEAD
# personal-finance-tracker
An open source personal finance tracker/monthly budgeting app
=======
# Personal Finance Tracker

A Flask-based personal finance tracker with SimpleFin integration and budget forecasting.

## Features
- Transaction tracking and categorization.
- SimpleFin sync for automated bank data import.
- Budget projection and forecasting.
- Modern, responsive UI.

## Deployment Guide

### 1. Prerequisites
- Python 3.12+
- Nginx
- A virtual environment (`venv`)

### 2. Application Setup
1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Copy the template: `cp .env.template .env`
   - Edit `.env` and set a unique `SECRET_KEY`.
   - **Note:** The app defaults to `dev_key` if not set, but this is insecure for production.


### 3. Running with Gunicorn
For production, use Gunicorn to serve the application:
```bash
venv/bin/python -m gunicorn -c deploy/gunicorn_config.py "app:create_app()"
```

### 4. Nginx Configuration
A template configuration is provided in `deploy/finance.conf`.

#### Option A: Standard Nginx Installation
1. Copy the template:
   ```bash
   sudo cp deploy/finance.conf /etc/nginx/conf.d/finance.conf
   ```
2. Edit `/etc/nginx/conf.d/finance.conf` to set your `server_name` and `proxy_pass` IP.
3. Reload Nginx: `sudo systemctl reload nginx`

#### Option B: Docker-based Nginx
1. Mount or copy `deploy/finance.conf` to your Nginx container's `/etc/nginx/conf.d/` directory.
2. Update the `proxy_pass` to point to the host machine's IP where the app is running.
3. Restart the container: `docker compose restart nginx`

## License
MIT
>>>>>>> 909a5cc (Initial commit)
