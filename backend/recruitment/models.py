import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

def resume_path(instance, filename):
    return f"resumes/{instance.owner_id}/{uuid.uuid4().hex}.pdf"

class User(AbstractUser):
    role = models.CharField(max_length=12, choices=[("candidate", "Candidate"), ("recruiter", "Recruiter"), ("admin", "Administrator")], default="candidate")
    email = models.EmailField(unique=True)

class Resume(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to=resume_path, blank=True)
    text = models.TextField()
    analysis = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class Job(models.Model):
    recruiter = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    salary = models.CharField(max_length=100, blank=True)
    kind = models.CharField(max_length=50, default="Full-time")
    description = models.TextField()
    skills = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Application(models.Model):
    candidate = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="applied", choices=[("applied", "Applied"), ("shortlisted", "Shortlisted"), ("interview", "Interview"), ("rejected", "Rejected"), ("hired", "Hired")])
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["candidate", "job"], name="one_application_per_job")]
class CareerReport(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="career_reports")
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="career_reports")
    title = models.CharField(max_length=150)
    job_description = models.TextField()
    resume_snapshot = models.TextField()
    status = models.CharField(max_length=12, default="queued", choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")])
    result = models.JSONField(default=dict)
    error = models.CharField(max_length=300, blank=True)
    model = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class ResumeBlob(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    data = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
