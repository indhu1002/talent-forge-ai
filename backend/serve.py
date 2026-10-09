"""Start the web server and durable report worker on a single small host."""
import os
import signal
import subprocess
import sys
import time

if os.getenv("RENDER") and os.getenv("DB_ENGINE") != "mysql":
    raise SystemExit("Render requires cloud MySQL to preserve accounts, reports and PDFs.")
# A newly provisioned database can take longer than the application image build.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.db import connection, connections, OperationalError
ready_deadline = time.monotonic() + 180
while True:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        connections.close_all()
        break
    except OperationalError:
        connections.close_all()
        if time.monotonic() >= ready_deadline:
            raise SystemExit("Cloud database is not ready after 180 seconds; check database status and connection settings.")
        print("Waiting for the cloud database...", flush=True)
        time.sleep(5)
subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
subprocess.run([sys.executable, "manage.py", "createcachetable"], check=True)
processes = []
def stop(*_):
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
processes.append(subprocess.Popen([sys.executable, "manage.py", "run_career_worker"]))
processes.append(subprocess.Popen([sys.executable, "-m", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:"+os.getenv("PORT", "10000"), "--workers", "1", "--threads", "4", "--timeout", "120", "--graceful-timeout", "20", "--access-logfile", "-", "--error-logfile", "-"]))
while all(process.poll() is None for process in processes):
    time.sleep(1)
for process in processes:
    if process.poll() is None:
        process.terminate()
raise SystemExit(1)
