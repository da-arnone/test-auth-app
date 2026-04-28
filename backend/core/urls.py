from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health),
    path("admin/auth/users", views.admin_users),
    path("admin/auth/users/<str:user_id>", views.admin_user_detail),
    path("admin/auth/users/<str:user_id>/suspended", views.admin_user_suspended),
    path("admin/auth/users/<str:user_id>/profiles", views.admin_user_profiles),
    path("admin/auth/users/<str:user_id>/password", views.admin_user_password),
    path("third/auth/token", views.third_token),
    path("third/auth/validate", views.third_validate),
    path("third/auth/whois", views.third_whois),
    path("third/auth/authorize", views.third_authorize),
    path("org/health", views.org_health),
    path("api/org/contracts", views.org_contracts),
]
