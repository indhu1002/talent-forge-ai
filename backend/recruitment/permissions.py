from rest_framework.permissions import BasePermission, SAFE_METHODS

class DemoReadOnly(BasePermission):
    message = "Demo accounts are read-only. Create your own account to make changes."

    def has_permission(self, request, view):
        return (not getattr(request.user, "is_demo", False)
                or request.method in SAFE_METHODS
                or request.path == "/api/auth/logout/")
