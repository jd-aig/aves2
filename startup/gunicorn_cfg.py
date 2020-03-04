import os
import multiprocessing


bind = "0.0.0.0:" + os.getenv('DJANGO_PORT', '8080')
# workers = multiprocessing.cpu_count() * 2 + 1
workers = int(os.getenv('CPU_NUMS', multiprocessing.cpu_count())) * 2 + 1
max_requests = 10000
max_requests_jitter = 100
timeout = 60

chdir = os.getenv('DJANGO_PROJ_PATH')
user = "root"
group = "root"
loglevel = "info"
accesslog = "-"
errorlog = "-"
# errorlog = "/var/log/aves2-gunicorn.log"
capture_output = True
