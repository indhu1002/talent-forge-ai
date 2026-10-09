import signal
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
from recruitment.models import CareerReport
from recruitment.career_ai import run_report

class Command(BaseCommand):
    help = "Process persisted AI reports; one worker is sufficient for the free host."

    def handle(self, *args, **options):
        self.stopping = False
        def stop(*_):
            self.stopping = True
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not self.stopping:
            close_old_connections()
            try:
                CareerReport.objects.filter(status="running", updated_at__lt=timezone.now()-timedelta(minutes=8)).update(status="failed", error="This analysis was interrupted. Generate a new report to retry.", updated_at=timezone.now())
                report_id = CareerReport.objects.filter(status="queued").order_by("created_at").values_list("id", flat=True).first()
                if report_id:
                    run_report(report_id)
                else:
                    time.sleep(2)
            except Exception:
                self.stderr.write("AI worker temporarily unavailable; retrying in 10 seconds.")
                time.sleep(10)
