# Gunicorn configuration file for production deployment
bind = "0.0.0.0:5000"
workers = 2
worker_class = "sync"
timeout = 60
graceful_timeout = 30
keepalive = 5
preload_app = False
accesslog = "-"
errorlog = "-"
loglevel = "info"
proc_name = "product-api"

