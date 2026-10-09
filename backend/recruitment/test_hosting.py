import tempfile
from pathlib import Path
from unittest.mock import patch
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import User, Resume, ResumeBlob, CareerReport
from .career_ai import run_report, enqueue_report
from .tests import TEXT
from .test_career import JD, sample_result

DATABASE_STORAGE = {"default": {"BACKEND": "recruitment.storage.DatabaseResumeStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}

@override_settings(STORAGES=DATABASE_STORAGE, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HostingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("hosted-owner", email="owner@example.com")
        self.other = User.objects.create_user("hosted-other", email="other@example.com")
        self.client = APIClient()

    def test_pdf_persists_without_local_files_and_remains_private(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            resume = Resume.objects.create(owner=self.owner, title="Cloud PDF", text=TEXT, file=ContentFile(b"%PDF-test private bytes", name="resume.pdf"))
            self.assertEqual(list(Path(folder).iterdir()), [])
            self.assertEqual(ResumeBlob.objects.count(), 1)
            # Reopen through a new model/storage instance, as after a restart.
            fresh = Resume.objects.get(pk=resume.pk)
            self.assertEqual(fresh.file.read(), b"%PDF-test private bytes")
            self.client.force_authenticate(self.other)
            self.assertEqual(self.client.get(f"/api/resumes/{resume.pk}/download/").status_code, 404)
            self.client.force_authenticate(self.owner)
            response = self.client.get(f"/api/resumes/{resume.pk}/download/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"%PDF-test private bytes")
            self.assertEqual(self.client.delete(f"/api/resumes/{resume.pk}/").status_code, 204)
            self.assertEqual(ResumeBlob.objects.count(), 0)

    def test_storage_has_no_public_url_and_enforces_capacity(self):
        storage = storages["default"]
        with self.assertRaises(ValueError):
            storage.url("resumes/private.pdf")
        with patch.dict("os.environ", {"MAX_RESUME_STORAGE_MB": "0"}):
            from rest_framework.exceptions import ValidationError
            with self.assertRaises(ValidationError):
                storage.save("resumes/private.pdf", ContentFile(b"private"))
        self.assertEqual(ResumeBlob.objects.count(), 0)

    def test_health_checks_database_without_disclosing_connection(self):
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})
        with patch("config.hosting.connection.cursor", side_effect=RuntimeError("secret-host")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_home_uses_compiled_frontend_and_never_exposes_media(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "index.html").write_text("<html>Talent Forge</html>")
            with override_settings(FRONTEND_DIST=Path(folder)):
                response = self.client.get("/")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Talent Forge", b"".join(response.streaming_content))
        self.assertEqual(self.client.get("/media/resumes/private.pdf").status_code, 404)

    @patch.dict("os.environ", {"CAREER_WORKER_MODE": "database"})
    @patch("recruitment.career_ai.executor.submit")
    def test_hosted_enqueue_leaves_persistent_work_for_worker(self, submit):
        enqueue_report(123)
        submit.assert_not_called()

    @patch("recruitment.career_ai.connections.close_all")
    @patch("recruitment.career_ai.close_old_connections")
    @patch("recruitment.career_ai.generate_report")
    def test_duplicate_worker_claim_does_not_repeat_provider_call(self, generator, close_old, close_all):
        resume = Resume.objects.create(owner=self.owner, title="Resume", text=TEXT)
        report = CareerReport.objects.create(owner=self.owner, resume=resume, title="JD", resume_snapshot=TEXT, job_description=JD)
        generator.return_value = (sample_result(), "test-model")
        run_report(report.pk)
        run_report(report.pk)
        generator.assert_called_once()
        report.refresh_from_db()
        self.assertEqual(report.status, "completed")
