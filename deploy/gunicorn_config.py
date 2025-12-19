import multiprocessing

# Bind to all interfaces to allow access from local/wireguard networks
# Port 8000 is common for Gunicorn
bind = "0.0.0.0:8000"

# Recommended number of workers: (2 x cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Forward headers for Nginx proxy
forwarded_allow_ips = '*'
secure_scheme_headers = {'X-FORWARDED-PROTO': 'https'}

# Log settings
accesslog = '-'
errorlog = '-'
loglevel = 'info'
