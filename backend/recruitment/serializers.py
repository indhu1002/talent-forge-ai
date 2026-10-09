from rest_framework import serializers
from .models import User, Resume, Job, Application
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "role"]
class ResumeSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.first_name", read_only=True)
    class Meta:
        model = Resume
        fields = ["id", "title", "text", "analysis", "created_at", "owner_name"]
        read_only_fields = ["analysis", "created_at", "owner_name"]
class JobSerializer(serializers.ModelSerializer):
    application_count = serializers.IntegerField(source="applications.count", read_only=True)
    class Meta:
        model = Job
        fields = ["id", "title", "company", "location", "salary", "kind", "description", "skills", "active", "created_at", "application_count"]
    def validate_skills(self, value):
        if not isinstance(value, list) or not value or len(value) > 30 or any(not isinstance(s, str) or not s.strip() or len(s) > 60 for s in value):
            raise serializers.ValidationError("Provide 1–30 nonempty skills, each up to 60 characters.")
        return [s.strip() for s in value]
class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.first_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company = serializers.CharField(source="job.company", read_only=True)
    resume_score = serializers.SerializerMethodField()
    class Meta:
        model = Application
        fields = ["id", "job", "resume", "status", "candidate_name", "job_title", "company", "resume_score", "created_at"]
        read_only_fields = ["status", "candidate_name", "job_title", "company", "resume_score", "created_at"]
    def get_resume_score(self, obj):
        return obj.resume.analysis.get("score", 0)