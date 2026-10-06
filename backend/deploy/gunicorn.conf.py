"""Gunicorn settings. Run from backend/:  gunicorn -c deploy/gunicorn.conf.py run:app"""
bind = "127.0.0.1:5000"        # internal only; Nginx is the public entry point
workers = 4                    # SRD 5.3
timeout = 30
graceful_timeout = 30
keepalive = 5
accesslog = "-"                # stdout -> journald
errorlog = "-"
loglevel = "info"
forwarded_allow_ips = "127.0.0.1"
