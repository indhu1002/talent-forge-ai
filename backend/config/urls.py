from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from recruitment import views
from recruitment.career_views import CareerReportViewSet, career_config
router = DefaultRouter()
router.register("career-reports", CareerReportViewSet, basename="career-reports")
router.register("resumes", views.ResumeViewSet, basename="resumes")
router.register("jobs", views.JobViewSet, basename="jobs")
router.register("applications", views.ApplicationViewSet, basename="applications")
urlpatterns = [path("api/career-config/", career_config), path("admin/", admin.site.urls), path("api/auth/register/", views.register), path("api/auth/login/", views.LoginView.as_view()), path("api/auth/refresh/", TokenRefreshView.as_view()), path("api/auth/logout/", TokenBlacklistView.as_view()), path("api/auth/me/", views.me), path("api/analytics/", views.analytics), path("api/users/", views.users), path("api/", include(router.urls))]