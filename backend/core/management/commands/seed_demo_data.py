from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.models import AppUser, UserProfile


class Command(BaseCommand):
    help = "Seed demo users and profiles"

    def handle(self, *args, **options):
        django_user_model = get_user_model()
        django_admin, created = django_user_model.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "is_active": True},
        )
        django_admin.is_staff = True
        django_admin.is_superuser = True
        django_admin.is_active = True
        django_admin.set_password("changeme")
        django_admin.save()
        self.stdout.write(
            self.style.SUCCESS(
                "Django superuser ensured: admin/changeme"
                if created
                else "Django superuser updated: admin/changeme"
            )
        )

        if AppUser.objects.filter(username="admin").exists():
            self.stdout.write(self.style.SUCCESS("App demo users already seeded"))
            return

        admin = AppUser(username="admin")
        admin.set_password("admin123")
        admin.save()
        UserProfile.objects.create(user=admin, app_scope="auth-app", role="auth-admin", context=None)

        alice = AppUser(username="alice")
        alice.set_password("alice123")
        alice.save()
        UserProfile.objects.create(user=alice, app_scope="org-app", role="org-app", context="org-001")
        UserProfile.objects.create(user=alice, app_scope="org-app", role="org-third", context="org-001")

        self.stdout.write(self.style.SUCCESS("App demo users seeded"))
