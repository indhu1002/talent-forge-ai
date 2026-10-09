from io import StringIO
from django.test import TestCase, override_settings
from django.core.management import call_command
from rest_framework.test import APIClient
from recruitment.models import User, Resume, Job, Application
from recruitment.management.commands.seed_reviewer_demo import DEMO_PASSWORD, TEXT

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReviewerDemoTests(TestCase):
    def setUp(self):
        call_command("seed_reviewer_demo", stdout=StringIO())
        self.demo = User.objects.get(username="demo-candidate")
        self.recruiter = User.objects.get(username="demo-recruiter")
        self.real = User.objects.create_user("real", email="real@example.com", password="Str0ng!Pass#123")
        self.hr = User.objects.create_user("realhr", email="hr@example.com", role="recruiter")
        self.realjob = Job.objects.create(recruiter=self.hr, title="Real job", company="Real", location="Remote", description="Real", skills=["Python"])
        self.client = APIClient()

    def test_seed_idempotent_and_nonprivileged(self):
        call_command("seed_reviewer_demo", stdout=StringIO())
        self.assertEqual(User.objects.filter(is_demo=True).count(), 2)
        self.assertEqual(Resume.objects.filter(owner=self.demo).count(), 1)
        self.assertFalse(User.objects.filter(is_demo=True, is_staff=True).exists())
        self.assertFalse(User.objects.filter(is_demo=True, is_superuser=True).exists())

    def test_public_demo_login_and_logout(self):
        tokens = self.client.post("/api/auth/login/", {"username": self.demo.username, "password": DEMO_PASSWORD}).data
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+tokens["access"])
        self.assertTrue(self.client.get("/api/auth/me/").data["is_demo"])
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code, 401)

    def test_demo_cannot_write_or_charge_ai(self):
        self.client.force_authenticate(self.demo)
        resume = Resume.objects.get(owner=self.demo)
        for path, method, data in [("/api/resumes/", "post", {"text": TEXT}),
                                  (f"/api/resumes/{resume.pk}/", "delete", {}),
                                  ("/api/applications/", "post", {}),
                                  ("/api/career-reports/", "post", {})]:
            self.assertEqual(getattr(self.client, method)(path, data).status_code, 403, path)
        self.client.force_authenticate(self.recruiter)
        job = Job.objects.filter(recruiter=self.recruiter).first()
        self.assertEqual(self.client.patch(f"/api/jobs/{job.pk}/", {"active": False}).status_code, 403)
        app = Application.objects.filter(job__recruiter=self.recruiter).first()
        self.assertEqual(self.client.patch(f"/api/applications/{app.pk}/", {"status": "hired"}).status_code, 403)

    def test_demo_and_real_data_are_separate(self):
        self.client.force_authenticate(self.demo)
        self.assertEqual(len(self.client.get("/api/jobs/").data), 3)
        self.assertEqual(self.client.get(f"/api/jobs/{self.realjob.pk}/").status_code, 404)
        self.client.force_authenticate(self.real)
        self.assertEqual([j["id"] for j in self.client.get("/api/jobs/").data], [self.realjob.pk])
        self.assertEqual(self.client.get("/api/analytics/").data["jobs"], 1)
        demo_resume = Resume.objects.get(owner=self.demo)
        self.assertEqual(self.client.get(f"/api/resumes/{demo_resume.pk}/").status_code, 404)
        real_resume = Resume.objects.create(owner=self.real, title="Real", text=TEXT)
        demo_job = Job.objects.filter(recruiter=self.recruiter).first()
        self.assertEqual(self.client.post("/api/applications/", {"resume": real_resume.pk, "job": demo_job.pk}).status_code, 403)

    def test_registration_cannot_opt_into_demo_and_admin_cannot_promote_demo(self):
        result = self.client.post("/api/auth/register/", {"username": "newuser", "email": "new@example.com", "password": "Str0ng!Pass#123", "is_demo": True})
        self.assertEqual(result.status_code, 201, result.data)
        self.assertFalse(result.data["is_demo"])
        admin = User.objects.create_user("admin", email="admin@example.com", role="admin")
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.patch("/api/users/", {"id": self.demo.pk, "role": "admin"}).status_code, 400)
        self.demo.refresh_from_db()
        self.assertEqual(self.demo.role, "candidate")
