import os, secrets
from pathlib import Path
from django.core.management.base import BaseCommand
from recruitment.models import User, Job, Resume, Application
from recruitment.analysis import analyze
class Command(BaseCommand):
    help = "Create illustrative local demo accounts and jobs (never use in production)."
    def handle(self, *args, **kwargs):
        password = os.getenv("DEMO_PASSWORD") or secrets.token_urlsafe(14)
        created = []
        for username, role, name in [("candidate", "candidate", "Alex Morgan"), ("recruiter", "recruiter", "Jordan Lee"), ("administrator", "admin", "Workspace Admin")]:
            user, new = User.objects.get_or_create(username=username, defaults={"email": username+"@talentforge.example", "first_name": name, "role": role})
            if new:
                user.set_password(password)
                user.is_staff = role == "admin"
                user.is_superuser = role == "admin"
                user.save()
                created.append(username)
        recruiter = User.objects.get(username="recruiter")
        for title, company, location, salary, skills in [
            ("Full-stack Developer", "Northstar Labs", "Bengaluru / Hybrid", "₹10–16 LPA", ["React", "Python", "Django", "MySQL", "Git"]),
            ("Frontend Engineer", "Orbit Studio", "Remote", "₹8–14 LPA", ["React", "TypeScript", "CSS", "HTML", "Git"]),
            ("Backend Developer", "Evergreen Systems", "Hyderabad", "₹9–15 LPA", ["Python", "Django", "SQL", "Docker", "AWS"]),
            ("Product Engineer", "Bloom Technologies", "Pune / Hybrid", "₹12–18 LPA", ["JavaScript", "React", "REST", "PostgreSQL"]),
        ]:
            Job.objects.get_or_create(title=title, company=company, recruiter=recruiter, defaults={"location":location, "salary":salary, "skills":skills, "description":"Illustrative demo opportunity. Build thoughtful digital products, collaborate with a small engineering team, and ship reliable features. Bring curiosity, strong fundamentals, and care for the people using your work."})
        if created:
            credentials = Path(__file__).resolve().parents[3] / "DEMO-CREDENTIALS.txt"
            credentials.write_text("LOCAL DEMO ONLY — generated credentials\n\nUsernames: "+", ".join(created)+"\nPassword: "+password+"\n\nDo not use these accounts or this password in production.\n", encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Demo credentials saved to {credentials}"))
        else:
            self.stdout.write("Demo users already exist; their passwords were preserved.")