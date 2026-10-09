"""Private database storage for small free-hosted installations.

Downloads pass through the existing authorized API. No public file URLs exist.
"""
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db.models import Sum
from django.utils.deconstruct import deconstructible

@deconstructible
class DatabaseResumeStorage(Storage):
    def _model(self):
        from .models import ResumeBlob
        return ResumeBlob

    def _open(self, name, mode="rb"):
        if mode not in ("r", "rb"):
            raise ValueError("Resume files are read-only after upload.")
        try:
            blob = self._model().objects.get(pk=name)
        except self._model().DoesNotExist:
            raise FileNotFoundError(name) from None
        return ContentFile(bytes(blob.data), name=name)

    def _save(self, name, content):
        import os
        from rest_framework.exceptions import ValidationError
        data = b"".join(content.chunks())
        if len(data) > 5 * 1024 * 1024:
            raise ValidationError("PDF must be smaller than 5 MB.")
        used = self._model().objects.aggregate(total=Sum("size"))["total"] or 0
        if used + len(data) > int(os.getenv("MAX_RESUME_STORAGE_MB", "128")) * 1024 * 1024:
            raise ValidationError("Resume storage is full. Delete unused resumes before uploading another.")
        self._model().objects.create(name=name, data=data, size=len(data))
        return name

    def exists(self, name):
        return self._model().objects.filter(pk=name).exists()

    def delete(self, name):
        self._model().objects.filter(pk=name).delete()

    def size(self, name):
        return self._model().objects.values_list("size", flat=True).get(pk=name)

    def url(self, name):
        raise ValueError("Resumes are private; use the authorized download API.")
