import io
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from pypdf import PdfReader
from .models import User, Resume, Job, Application
from .serializers import UserSerializer, ResumeSerializer, JobSerializer, ApplicationSerializer
from .analysis import analyze, match

class LoginThrottle(AnonRateThrottle):
    scope = "login"
class LoginView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]

def require_role(user, *roles):
    if user.role not in roles:
        raise PermissionDenied("Your role does not permit this action.")

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def register(request):
    data = request.data
    if data.get("role", "candidate") not in ["candidate", "recruiter"]:
        return Response({"detail": "Choose candidate or recruiter."}, status=400)
    serializer = UserSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    try:
        password = data.get("password", "")
        validate_password(password, User(**serializer.validated_data))
        with transaction.atomic():
            user = User.objects.create_user(**serializer.validated_data, password=password)
    except ValidationError as exc:
        return Response({"detail": list(exc.messages)}, status=400)
    except IntegrityError:
        return Response({"detail": "Username or email already exists."}, status=400)
    return Response(UserSerializer(user).data, status=201)

@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Resume.objects.all().order_by("-created_at")
        if user.role == "recruiter":
            return Resume.objects.filter(application__job__recruiter=user).distinct().order_by("-created_at")
        return Resume.objects.filter(owner=user).order_by("-created_at")
    def create(self, request):
        require_role(request.user, "candidate")
        uploaded = request.FILES.get("file")
        text = request.data.get("text", "")
        if uploaded:
            if uploaded.size > 5 * 1024 * 1024:
                return Response({"detail": "PDF must be smaller than 5 MB."}, status=400)
            raw = uploaded.read()
            if not raw.startswith(b"%PDF-"):
                return Response({"detail": "Upload a valid PDF file."}, status=400)
            try:
                reader = PdfReader(io.BytesIO(raw))
                if reader.is_encrypted or len(reader.pages) > 20:
                    raise ValueError()
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return Response({"detail": "Cannot read this PDF. Use an unencrypted PDF up to 20 pages."}, status=400)
            uploaded.seek(0)
        if len(text.strip()) < 80 or len(text) > 100000:
            return Response({"detail": "Provide 80–100,000 characters of readable resume text. Scanned PDFs require OCR first."}, status=400)
        serializer = self.get_serializer(data={"title": request.data.get("title", "My resume"), "text": text})
        serializer.is_valid(raise_exception=True)
        resume = serializer.save(owner=request.user, analysis=analyze(text), file=uploaded or "")
        return Response(self.get_serializer(resume).data, status=201)
    def perform_destroy(self, instance):
        if instance.owner != self.request.user and self.request.user.role != "admin":
            raise PermissionDenied()
        if instance.file:
            instance.file.delete(save=False)
        instance.delete()
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        resume = self.get_object()
        if not resume.file:
            return Response({"detail": "This resume was built from text."}, status=404)
        return FileResponse(resume.file.open("rb"), as_attachment=True, filename="resume.pdf")

class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    def get_queryset(self):
        user = self.request.user
        qs = Job.objects.all()
        if user.role == "candidate":
            qs = qs.filter(active=True)
        if self.request.query_params.get("mine") == "1" and user.role != "admin":
            qs = qs.filter(recruiter=user)
        return qs.order_by("-created_at")
    def perform_create(self, serializer):
        require_role(self.request.user, "recruiter", "admin")
        serializer.save(recruiter=self.request.user)
    def guard(self, instance):
        if self.request.user.role != "admin" and (self.request.user.role != "recruiter" or instance.recruiter != self.request.user):
            raise PermissionDenied()
    def perform_update(self, serializer):
        self.guard(serializer.instance)
        serializer.save()
    def perform_destroy(self, instance):
        self.guard(instance)
        instance.delete()
    @action(detail=False, methods=["get"])
    def matches(self, request):
        require_role(request.user, "candidate")
        resume_id = request.query_params.get("resume", "")
        if not str(resume_id).isdigit():
            return Response({"detail": "Select a valid resume."}, status=400)
        resume = get_object_or_404(Resume, pk=int(resume_id), owner=request.user)
        jobs = [{**JobSerializer(job).data, "match": match(resume.text, job.skills)} for job in self.get_queryset()]
        return Response(sorted(jobs, key=lambda j: j["match"]["score"], reverse=True))

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    def get_queryset(self):
        user = self.request.user
        qs = Application.objects.select_related("candidate", "job", "resume")
        if user.role == "candidate":
            qs = qs.filter(candidate=user)
        elif user.role == "recruiter":
            qs = qs.filter(job__recruiter=user)
        return qs.order_by("-created_at")
    def create(self, request):
        require_role(request.user, "candidate")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["resume"].owner != request.user or not data["job"].active:
            raise PermissionDenied("Select your own resume and an active job.")
        try:
            with transaction.atomic():
                application = serializer.save(candidate=request.user)
        except IntegrityError:
            return Response({"detail": "You already applied to this job."}, status=400)
        return Response(self.get_serializer(application).data, status=201)
    def partial_update(self, request, pk=None):
        require_role(request.user, "recruiter", "admin")
        application = self.get_object()
        state = request.data.get("status")
        if state not in dict(Application._meta.get_field("status").choices):
            return Response({"detail": "Invalid application status."}, status=400)
        application.status = state
        application.save(update_fields=["status"])
        return Response(self.get_serializer(application).data)

@api_view(["GET"])
def analytics(request):
    user = request.user
    resumes = Resume.objects.all() if user.role == "admin" else Resume.objects.filter(owner=user) if user.role == "candidate" else Resume.objects.filter(application__job__recruiter=user).distinct()
    jobs = Job.objects.filter(active=True) if user.role != "recruiter" else Job.objects.filter(recruiter=user)
    apps = Application.objects.all()
    if user.role == "candidate":
        apps = apps.filter(candidate=user)
    elif user.role == "recruiter":
        apps = apps.filter(job__recruiter=user)
    scores = [r.analysis.get("score", 0) for r in resumes]
    return Response({"resumes": len(scores), "average_score": round(sum(scores) / len(scores)) if scores else 0, "jobs": jobs.count(), "applications": apps.count(), "pipeline": list(apps.values("status").annotate(count=Count("id"))), "recent_resumes": ResumeSerializer(resumes.order_by("-created_at")[:5], many=True).data})

@api_view(["GET", "PATCH"])
def users(request):
    require_role(request.user, "admin")
    if request.method == "PATCH":
        user = get_object_or_404(User, pk=request.data.get("id"))
        if user == request.user:
            return Response({"detail": "Cannot change your own role."}, status=400)
        role = request.data.get("role")
        if role not in ["candidate", "recruiter", "admin"]:
            return Response({"detail": "Invalid role."}, status=400)
        user.role = role
        user.save(update_fields=["role"])
    return Response(UserSerializer(User.objects.all().order_by("id"), many=True).data)