import tempfile
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from .models import User, Resume, Job, Application
from .analysis import analyze, match
TEXT = """Alex Morgan
alex@example.com | +91 9876543210 | github.com/alex | linkedin.com/in/alex
SUMMARY
Full-stack developer with experience building reliable platforms and collaborating with a team.
SKILLS
Python, React, Django, MySQL, SQL, Docker, Git, REST
EXPERIENCE
Developer | Studio | 2024–2026
- Developed features for 1000 users and improved performance by 30%.
- Built APIs, designed interfaces and collaborated with stakeholders.
PROJECTS
- Created a recruitment platform.
EDUCATION
Computer Science degree | 2024
CERTIFICATIONS
AWS certificate
"""
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RecruitmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.candidate = User.objects.create_user("alice", email="alice@example.com", password="Str0ng!Pass#123", role="candidate")
        self.other = User.objects.create_user("bob", email="bob@example.com", password="Str0ng!Pass#123", role="candidate")
        self.recruiter = User.objects.create_user("recruiter", email="hr@example.com", password="Str0ng!Pass#123", role="recruiter")
        self.other_recruiter = User.objects.create_user("otherhr", email="otherhr@example.com", password="Str0ng!Pass#123", role="recruiter")
        self.admin = User.objects.create_user("admin", email="admin@example.com", password="Str0ng!Pass#123", role="admin")
        self.resume = Resume.objects.create(owner=self.candidate, title="Alice Resume", text=TEXT, analysis=analyze(TEXT))
        self.job = Job.objects.create(recruiter=self.recruiter, title="Developer", company="Studio", location="Remote", skills=["React", "Python", "Django"], description="Build things.")
    def auth(self, user):
        self.client.force_authenticate(user=user)
    def test_anonymous_denied(self):
        self.assertEqual(self.client.get("/api/resumes/").status_code, 401)
    def test_registration_and_jwt(self):
        response = self.client.post("/api/auth/register/", {"username":"newperson", "email":"new@example.com", "first_name":"New", "password":"Str0ng!Pass#123", "role":"candidate"})
        self.assertEqual(response.status_code, 201, response.data)
        tokens = self.client.post("/api/auth/login/", {"username":"newperson", "password":"Str0ng!Pass#123"}).data
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+tokens["access"])
        self.assertEqual(self.client.get("/api/auth/me/").data["role"], "candidate")
        refresh = self.client.post("/api/auth/refresh/", {"refresh":tokens["refresh"]})
        self.assertEqual(refresh.status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh":tokens["refresh"]}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh":refresh.data["refresh"]}).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh/", {"refresh":refresh.data["refresh"]}).status_code, 401)
    def test_cannot_register_admin_or_weak_password(self):
        self.assertEqual(self.client.post("/api/auth/register/", {"username":"evil","email":"evil@example.com","password":"Str0ng!Pass#123","role":"admin"}).status_code,400)
        self.assertEqual(self.client.post("/api/auth/register/", {"username":"new","email":"new@example.com","password":"123","role":"candidate"}).status_code,400)
    def test_resume_privacy(self):
        self.auth(self.other)
        self.assertEqual(self.client.get("/api/resumes/").data, [])
        self.assertEqual(self.client.get(f"/api/resumes/{self.resume.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/resumes/{self.resume.id}/").status_code, 404)
        self.auth(self.recruiter)
        self.assertEqual(self.client.get("/api/resumes/").data, [])
    def test_text_resume_analysis(self):
        self.auth(self.candidate)
        response = self.client.post("/api/resumes/", {"title":"New resume", "text":TEXT}, format="json")
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(len(response.data["analysis"]["criteria"]),18)
        self.assertGreater(response.data["analysis"]["score"],50)
    def test_invalid_pdf_and_short_text(self):
        self.auth(self.candidate)
        fake = SimpleUploadedFile("bad.pdf", b"not a pdf", content_type="application/pdf")
        self.assertEqual(self.client.post("/api/resumes/", {"title":"Bad","file":fake},format="multipart").status_code,400)
        self.assertEqual(self.client.post("/api/resumes/", {"title":"Short","text":"Hi"}).status_code,400)
    def test_valid_pdf_extract_and_private_download(self):
        import io
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=595,height=842)
        font = DictionaryObject({NameObject("/Type"):NameObject("/Font"),NameObject("/Subtype"):NameObject("/Type1"),NameObject("/BaseFont"):NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 50 750 Td (Alex Morgan Python Django React MySQL experience education summary skills projects built APIs and improved performance by 30 percent in 2026.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = io.BytesIO(); writer.write(output)
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            self.auth(self.candidate)
            response = self.client.post("/api/resumes/",{"title":"PDF","file":SimpleUploadedFile("resume.pdf",output.getvalue(),content_type="application/pdf")},format="multipart")
            self.assertEqual(response.status_code,201,response.data)
            rid = response.data["id"]
            self.assertIn("Python",response.data["text"])
            self.auth(self.other)
            self.assertEqual(self.client.get(f"/api/resumes/{rid}/download/").status_code,404)
            self.auth(self.candidate)
            download = self.client.get(f"/api/resumes/{rid}/download/")
            self.assertEqual(download.status_code,200)
            # Close file handles without emitting request_finished inside TestCase atomic.
            for closer in download._resource_closers:
                closer()
            self.assertEqual(self.client.delete(f"/api/resumes/{rid}/").status_code,204)
    def test_candidate_cannot_create_jobs_or_change_status(self):
        self.auth(self.candidate)
        self.assertEqual(self.client.post("/api/jobs/",{"title":"Bad","company":"Bad","location":"Remote","description":"Bad","skills":["Python"]},format="json").status_code,403)
        app=Application.objects.create(candidate=self.candidate, job=self.job,resume=self.resume)
        self.assertEqual(self.client.patch(f"/api/applications/{app.id}/",{"status":"hired"},format="json").status_code,403)
    def test_recruiter_job_ownership(self):
        self.auth(self.other_recruiter)
        self.assertEqual(self.client.patch(f"/api/jobs/{self.job.id}/",{"active":False},format="json").status_code,403)
        self.assertEqual(self.client.delete(f"/api/jobs/{self.job.id}/").status_code,403)
        self.auth(self.recruiter)
        self.assertEqual(self.client.patch(f"/api/jobs/{self.job.id}/",{"active":False},format="json").status_code,200)
    def test_apply_and_recruiter_visibility(self):
        self.auth(self.candidate)
        body={"job":self.job.id,"resume":self.resume.id}
        result=self.client.post("/api/applications/",body,format="json")
        self.assertEqual(result.status_code,201,result.data)
        self.assertEqual(self.client.post("/api/applications/",body,format="json").status_code,400)
        self.auth(self.recruiter)
        self.assertEqual(len(self.client.get("/api/resumes/").data),1)
        self.assertEqual(self.client.patch(f"/api/applications/{result.data['id']}/",{"status":"shortlisted"},format="json").status_code,200)
        self.assertEqual(self.client.delete(f"/api/resumes/{self.resume.id}/").status_code,403)
        self.auth(self.other_recruiter)
        self.assertEqual(self.client.get("/api/resumes/").data,[])
        self.assertEqual(self.client.get("/api/applications/").data,[])
        self.assertEqual(self.client.patch(f"/api/applications/{result.data['id']}/",{"status":"hired"},format="json").status_code,404)
    def test_cannot_apply_with_foreign_resume_or_closed_job(self):
        self.auth(self.other)
        self.assertEqual(self.client.post("/api/applications/",{"job":self.job.id,"resume":self.resume.id},format="json").status_code,403)
        self.auth(self.candidate)
        self.job.active=False;self.job.save()
        self.assertEqual(self.client.post("/api/applications/",{"job":self.job.id,"resume":self.resume.id},format="json").status_code,403)
    def test_match_and_private_resume_id(self):
        self.auth(self.candidate)
        matches=self.client.get(f"/api/jobs/matches/?resume={self.resume.id}")
        self.assertEqual(matches.status_code,200)
        self.assertEqual(matches.data[0]["match"]["score"],100)
        self.auth(self.other)
        self.assertEqual(self.client.get(f"/api/jobs/matches/?resume={self.resume.id}").status_code,404)
    def test_admin_and_analytics_scope(self):
        self.auth(self.other)
        self.assertEqual(self.client.get("/api/analytics/").data["resumes"],0)
        self.assertEqual(self.client.get("/api/users/").status_code,403)
        self.auth(self.admin)
        self.assertEqual(self.client.get("/api/analytics/").data["resumes"],1)
        self.assertEqual(self.client.get("/api/users/").status_code,200)
        self.assertEqual(self.client.patch("/api/users/",{"id":self.admin.id,"role":"candidate"},format="json").status_code,400)
    def test_empty_skill_list_rejected(self):
        self.auth(self.recruiter)
        self.assertEqual(self.client.post("/api/jobs/",{"title":"Dev","company":"Studio","location":"Remote","description":"Build","skills":[]},format="json").status_code,400)
    @patch("recruitment.analysis.urllib.request.urlopen", side_effect=TimeoutError)
    @patch.dict("os.environ", {"OPENAI_API_KEY":"test","ENABLE_AI_FEEDBACK":"1"})
    def test_ai_failure_preserves_local_analysis(self, mock):
        result=analyze(TEXT)
        self.assertEqual(len(result["criteria"]),18)
        self.assertIsNone(result["ai_feedback"])
        self.assertIn("ai_notice",result)
    def test_skill_boundaries_and_invalid_match_id(self):
        self.assertEqual(match("JavaScript and MySQL and digital products", ["Java", "SQL", "Git"])["score"],0)
        self.auth(self.candidate)
        self.assertEqual(self.client.get("/api/jobs/matches/?resume=invalid").status_code,400)
    @patch.dict("os.environ", {"OPENAI_API_KEY":"test", "ENABLE_AI_FEEDBACK":"1", "OPENAI_MODEL":"gpt-5.6-terra"})
    @patch("recruitment.analysis.urllib.request.urlopen")
    def test_terra_feedback_uses_responses_api(self, http):
        import json
        import io
        http.return_value = io.BytesIO(json.dumps({"status":"completed","output":[{"content":[{"type":"output_text","text":"Highlight the API project and quantify the outcomes you can verify."}]}]}).encode())
        result = analyze(TEXT)
        request = http.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(payload["model"], "gpt-5.6-terra")
        self.assertFalse(payload["store"])
        self.assertNotIn("max_tokens", payload)
        self.assertIn("Highlight the API project", result["ai_feedback"])