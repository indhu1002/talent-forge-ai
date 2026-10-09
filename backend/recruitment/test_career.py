import copy
import io
import json
from unittest.mock import patch
from datetime import timedelta
from urllib.error import HTTPError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Resume, CareerReport
from .career_ai import generate_report, run_report, CareerAIError
from .tests import TEXT
JD = "Full-stack developer. Build React interfaces and Django APIs with Python and MySQL. Explain authentication, testing and database query performance. Preferred skills include Docker and AWS."
def sample_result():
    return {
        "job_title":"Full-stack developer",
        "overview":"Resume evidence supports Django and React; confirm deployment experience.",
        "strengths":["Developed features using React and Django."],
        "requirements":[
            {"requirement":"Python","importance":"essential","status":"matched","resume_evidence":"Python, React, Django","recommendation":"Highlight the relevant project."},
            {"requirement":"Production deployment","importance":"preferred","status":"missing","resume_evidence":"Not evidenced in resume","recommendation":"Develop practical deployment experience."}
        ],
        "resume_edits":[{"section":"Experience","action":"rewrite","original":"- Developed features for 1000 users and improved performance by 30%.","suggested":"Developed features serving 1000 users; improved performance by 30%.","reason":"Make the result clear.","evidence":"Developed features for 1000 users","needs_confirmation":False}],
        "tailored_summary":"Developer with Python, React, Django and MySQL experience.",
        "keywords_to_highlight":["Python","Django"],
        "skills_to_develop":["Production deployment"],
        "interview_questions":[{"category": category,"difficulty":"intermediate","question":f"Practice question {i+1} about {category}","why_asked":"Checks relevant skills.","sample_answer":"Explain the approach and your actual example.","answer_points":["Approach","Tradeoff","Example"],"resume_connection":"Relevant to the provided resume and JD.","follow_up_questions":["What tradeoff would you consider?"]} for i,category in enumerate(["technical"]*6+["project"]*4+["behavioral"]*4+["scenario"]*4+["HR"]*2)],
        "preparation_plan":[{"day":i,"focus":"Review skills","tasks":["Review your real project and practice answers."]} for i in range(1,6)],
        "questions_to_ask":["How does your team review code?"],
        "limitations":["Practice questions are not guaranteed actual interview questions."],
    }
def response_context(data):
    return io.BytesIO(json.dumps(data).encode())
def response_data(result):
    return {"status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps(result)}]}]}

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CareerTests(TestCase):
    def setUp(self):
        self.client=APIClient()
        self.candidate=User.objects.create_user("careerowner",email="owner@career.example",password="good-password",role="candidate")
        self.other=User.objects.create_user("othercareer",email="other@career.example",password="good-password",role="candidate")
        self.recruiter=User.objects.create_user("careerhr",email="hr@career.example",password="good-password",role="recruiter")
        self.admin=User.objects.create_user("careeradmin",email="admin@career.example",password="good-password",role="admin")
        self.resume=Resume.objects.create(owner=self.candidate,title="Resume",text=TEXT,analysis={})
        self.report=CareerReport.objects.create(owner=self.candidate,resume=self.resume,title="Target job",job_description=JD,resume_snapshot=TEXT)
    def auth(self,user):
        self.client.force_authenticate(user=user)
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test-secret"})
    @patch("recruitment.career_views.enqueue_report")
    def test_generate_validates_and_schedules_once(self,enqueue):
        self.auth(self.candidate)
        with self.captureOnCommitCallbacks(execute=True):
            response=self.client.post("/api/career-reports/",{"resume":self.resume.id,"title":"Developer","job_description":JD,"consent":True},format="json")
        self.assertEqual(response.status_code,202,response.data)
        enqueue.assert_called_once_with(response.data["id"])
        created=CareerReport.objects.get(pk=response.data["id"])
        self.assertEqual(created.resume_snapshot,TEXT)
        self.assertNotIn("resume_snapshot",response.data)
    def test_no_access_to_someone_elses_coaching(self):
        for user in [self.other,self.recruiter,self.admin]:
            self.auth(user)
            self.assertEqual(self.client.get("/api/career-reports/").data,[])
            self.assertEqual(self.client.get(f"/api/career-reports/{self.report.id}/").status_code,404)
            self.assertEqual(self.client.delete(f"/api/career-reports/{self.report.id}/").status_code,404)
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test"})
    def test_foreign_resume_and_roles_denied(self):
        self.auth(self.other)
        body={"resume":self.resume.id,"job_description":JD,"consent":True}
        self.assertEqual(self.client.post("/api/career-reports/",body,format="json").status_code,403)
        self.auth(self.recruiter)
        self.assertEqual(self.client.post("/api/career-reports/",body,format="json").status_code,403)
    def test_consent_and_jd_validation(self):
        self.auth(self.candidate)
        self.assertEqual(self.client.post("/api/career-reports/",{"resume":self.resume.id,"job_description":JD,"consent":False},format="json").status_code,400)
        self.assertEqual(self.client.post("/api/career-reports/",{"resume":self.resume.id,"job_description":"too short","consent":True},format="json").status_code,400)
    @patch.dict("os.environ",{"OPENAI_API_KEY":""})
    def test_missing_config_clear_error_and_no_secret_response(self):
        self.auth(self.candidate)
        self.assertEqual(self.client.post("/api/career-reports/",{"resume":self.resume.id,"job_description":JD,"consent":True},format="json").status_code,503)
        config=self.client.get("/api/career-config/").data
        self.assertFalse(config["configured"])
        self.assertNotIn("key",config)
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test"})
    def test_pending_limit(self):
        CareerReport.objects.create(owner=self.candidate,resume=self.resume,title="Second",job_description=JD,resume_snapshot=TEXT)
        self.auth(self.candidate)
        self.assertEqual(self.client.post("/api/career-reports/",{"resume":self.resume.id,"job_description":JD,"consent":True},format="json").status_code,429)
    def test_interrupted_report_is_marked_failed(self):
        CareerReport.objects.filter(pk=self.report.id).update(updated_at=timezone.now()-timedelta(minutes=9))
        self.auth(self.candidate)
        result=self.client.get(f"/api/career-reports/{self.report.id}/")
        self.assertEqual(result.data["status"],"failed")
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test-secret","CAREER_AI_MODEL":"gpt-4.1-mini"})
    @patch("recruitment.career_ai.urllib.request.urlopen")
    def test_provider_structured_request_and_weighted_coverage(self,http):
        http.return_value=response_context(response_data(sample_result()))
        result,model=generate_report(TEXT,JD)
        self.assertEqual(result["coverage_score"],67)
        self.assertEqual(len(result["interview_questions"]),20)
        request=http.call_args.args[0];payload=json.loads(request.data)
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["format"]["type"],"json_schema")
        self.assertNotIn("test-secret",payload["input"])
        self.assertIn("never invent",payload["instructions"].lower())
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test"})
    @patch("recruitment.career_ai.urllib.request.urlopen")
    def test_unverified_evidence_does_not_count(self,http):
        fixture=sample_result()
        fixture["requirements"][0]["resume_evidence"]="Invented experience"
        fixture["resume_edits"][0]["original"]="Invented source text"
        http.return_value=response_context(response_data(fixture))
        result,_=generate_report(TEXT,JD)
        self.assertEqual(result["coverage_score"],0)
        self.assertTrue(result["resume_edits"][0]["needs_confirmation"])
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test-secret"})
    @patch("recruitment.career_ai.urllib.request.urlopen")
    def test_quota_error_does_not_expose_provider_or_key(self,http):
        http.side_effect=HTTPError("https://api.openai.com/v1/responses",429,"test-secret",{},None)
        with self.assertRaises(CareerAIError) as error:
            generate_report(TEXT,JD)
        self.assertIn("billing",str(error.exception))
        self.assertNotIn("test-secret",str(error.exception))
    @patch.dict("os.environ",{"OPENAI_API_KEY":"test"})
    @patch("recruitment.career_ai.urllib.request.urlopen")
    def test_invalid_output_not_marked_successful(self,http):
        fixture=sample_result();fixture["interview_questions"]=[]
        http.return_value=response_context(response_data(fixture))
        with self.assertRaises(CareerAIError):
            generate_report(TEXT,JD)
    @patch("recruitment.career_ai.connections.close_all")
    @patch("recruitment.career_ai.close_old_connections")
    @patch("recruitment.career_ai.generate_report",side_effect=CareerAIError("OpenAI quota or rate limit reached."))
    def test_worker_persists_failure(self,generator,close_old,close_all):
        run_report(self.report.id)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status,"failed")
        self.assertEqual(self.report.result,{})
        self.assertIn("quota",self.report.error)
    @patch("recruitment.career_ai.connections.close_all")
    @patch("recruitment.career_ai.close_old_connections")
    @patch("recruitment.career_ai.generate_report")
    def test_worker_stores_successful_report(self,generator,close_old,close_all):
        result=sample_result();result["coverage_score"]=67
        generator.return_value=(result,"gpt-4.1-mini")
        run_report(self.report.id)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status,"completed")
        self.assertEqual(len(self.report.result["interview_questions"]),20)