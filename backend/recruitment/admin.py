from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Resume, Job, Application
admin.site.register(User, UserAdmin)
admin.site.register([Resume, Job, Application])