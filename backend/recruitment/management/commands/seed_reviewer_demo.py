from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from recruitment.models import User, Resume, Job, Application
from recruitment.analysis import analyze
from unittest.mock import patch

# Intentionally public credentials for isolated, read-only reviewer accounts.
DEMO_PASSWORD = "TalentForgeDemo!2026"
TEXT = """Alex Morgan (fictional demo candidate)
alex@example.invalid | github.com/example | linkedin.com/in/example
SUMMARY
Full-stack developer building accessible React interfaces and reliable Django REST APIs.
SKILLS
Python, Django, React, JavaScript, MySQL, SQL, REST, Git, HTML, CSS
EXPERIENCE
Software Developer | Demo Studio | 2024-2026
- Built a React and Django recruitment platform serving 1,000 users.
- Implemented JWT authentication and permissions for three user roles.
- Added database indexes and reduced API response time by 30%.
- Collaborated with five developers and wrote integration tests.
PROJECTS
Talent Forge: resume scoring, skill-based job matching, analytics and resume builder.
EDUCATION
Bachelor of Technology in Computer Science | Demo University | 2020-2024
"""

class Command(BaseCommand):
    help = "Create isolated, read-only public candidate and recruiter demos (never an administrator)."

    @transaction.atomic
    def handle(self, *args, **options):
        accounts = {}
        for role, name in [("candidate", "Alex Demo"), ("recruiter", "Sam Demo")]:
            user, created = User.objects.get_or_create(username="demo-"+role, defaults={
                "email": "demo-"+role+"@talentforge.invalid", "first_name": name,
                "role": role, "is_demo": True})
            if not user.is_demo or user.role != role or user.is_staff or user.is_superuser:
                raise CommandError("Refusing to modify a non-demo or privileged account.")
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            accounts[role] = user
        with patch.dict("os.environ", {"ENABLE_AI_FEEDBACK": "0"}):
            resume, _ = Resume.objects.get_or_create(owner=accounts["candidate"], title="Alex Morgan — fictional sample resume",
                defaults={"text": TEXT, "analysis": analyze(TEXT)})
        for title, skills, status in [
            ("Full-stack Developer", ["React", "Python", "Django", "MySQL"], "interview"),
            ("Frontend Developer", ["React", "JavaScript", "HTML", "CSS"], "shortlisted"),
            ("Backend Engineer", ["Python", "Django", "SQL", "Docker"], None)]:
            job, _ = Job.objects.get_or_create(recruiter=accounts["recruiter"], title=title, company="Demo Studio (fictional)",
                defaults={"location": "Remote", "salary": "Example: ₹6–10 LPA", "skills": skills,
                "description": "Fictional reviewer opportunity. Build accessible web applications, secure REST APIs, and reliable database integrations. Collaborate with engineers, review code, and write tests. Required skills: "+", ".join(skills)+"."})
            if status:
                Application.objects.get_or_create(candidate=accounts["candidate"], job=job,
                    defaults={"resume": resume, "status": status})
        self.stdout.write(self.style.SUCCESS("Read-only candidate and recruiter demos ready. No privileged accounts created."))
