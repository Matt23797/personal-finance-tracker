# Deployment Guide for Ubuntu VM

Follow these steps to migrate the Finance Tracker to your Ubuntu VM.

## 1. Setup Environment
Copy the project folder to `/home/ubuntu/finance_tracker` on your VM.

```bash
cd /home/ubuntu/finance_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure Systemd
Copy the service file to the systemd directory:

```bash
sudo cp finance_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable finance_tracker
sudo systemctl start finance_tracker
```

## 3. Configure Nginx
Copy the Nginx configuration:

```bash
sudo cp nginx_site /etc/nginx/sites-available/finance_tracker
sudo ln -s /etc/nginx/sites-available/finance_tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 4. Network Access
The Nginx configuration already restricts access to:
- `192.168.88.0/24` (Local)
- `192.168.100.0/24` (Wireguard)

Ensure your VM firewall (ufw) allows traffic on port 80:
```bash
sudo ufw allow 80/tcp
```
