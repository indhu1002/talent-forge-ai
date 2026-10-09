import os
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.throttling import UserRateThrottle
from .models import Resume, CareerReport
from .career_ai import enqueue_report

class CareerCreateThrottle(UserRateThrottle):
    rate = "10/hour"
    scope = "career_generation"

class CareerReportSerializer(serializers.ModelSerializer):
    resume_title = serializers.CharField(source="resume.title", read_only=True)
    class Meta:
        model = CareerReport
        fields = ["id", "resume", "resume_title", "title", "job_description", "status", "result", "error", "model", "created_at", "updated_at"]
        read_only_fields = fields

class ReportInput(serializers.Serializer):
    resume = serializers.PrimaryKeyRelatedField(queryset=Resume.objects.all())
    title = serializers.CharField(max_length=150, default="My target opportunity")
    job_description = serializers.CharField(min_length=100, max_length=20000)
    consent = serializers.BooleanField()
    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError("Agree to send the selected resume text and JD to OpenAI to generate your report.")
        return value

class CareerReportViewSet(viewsets.ModelViewSet):
    serializer_class = CareerReportSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    def get_throttles(self):
        return [CareerCreateThrottle()] if self.action == "create" else super().get_throttles()
    def get_queryset(self):
        # Coaching reports are private even after a resume is shared with a recruiter.
        qs = CareerReport.objects.filter(owner=self.request.user).select_related("resume")
        qs.filter(status__in=["queued", "running"], updated_at__lt=timezone.now()-timedelta(minutes=8)).update(status="failed", error="This analysis was interrupted or timed out. Generate a new report to retry.")
        return qs.order_by("-created_at")
    def create(self, request):
        if request.user.role != "candidate":
            raise PermissionDenied("JD coaching is available in candidate accounts.")
        serializer = ReportInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["resume"].owner != request.user:
            raise PermissionDenied("Choose a resume from your own account.")
        if len(data["resume"].text) > 30000:
            return Response({"detail": "For JD coaching, use a resume under 30,000 characters."}, status=400)
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return Response({"detail": "OpenAI is not configured. Add OPENAI_API_KEY to backend/.env."}, status=503)
        with transaction.atomic():
            # Serialize per-user creation so concurrent clicks cannot bypass the limit.
            type(request.user).objects.select_for_update().get(pk=request.user.pk)
            if self.get_queryset().filter(status__in=["queued", "running"]).count() >= 2:
                return Response({"detail": "Two reports are already being generated. Wait for them to finish."}, status=429)
            report = CareerReport.objects.create(owner=request.user, resume=data["resume"], title=data["title"], job_description=data["job_description"], resume_snapshot=data["resume"].text)
            transaction.on_commit(lambda: enqueue_report(report.pk))
        return Response(self.get_serializer(report).data, status=202)
    def perform_destroy(self, instance):
        # In-flight provider work may finish, but cannot recreate a deleted report.
        instance.delete()

@api_view(["GET"])
def career_config(request):
    return Response({"configured": bool(os.getenv("OPENAI_API_KEY", "").strip()), "model": os.getenv("CAREER_AI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")), "question_count": 20})