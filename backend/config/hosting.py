from django.conf import settings
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)

@require_GET
def frontend(request):
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return JsonResponse({"detail": "Frontend build is unavailable."}, status=503)
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response
