from django.contrib import admin

from .models import AppUser, UserProfile


admin.site.register(AppUser)
admin.site.register(UserProfile)
