import os

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole


class Command(BaseCommand):
    help = "Create or activate the initial SHOPLEX owner using OWNER_EMAIL and OWNER_PASSWORD."

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.getenv("OWNER_EMAIL", "").strip().lower()
        password = os.getenv("OWNER_PASSWORD", "")
        if not email or not password:
            raise CommandError("Set OWNER_EMAIL and OWNER_PASSWORD in the environment.")
        role = Role.objects.get(key=Role.Key.OWNER)
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(email=email, first_name="Platform", last_name="Owner")
        validate_password(password, user=user)
        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.status = User.Status.ACTIVE
        user.email_verified_at = user.email_verified_at or timezone.now()
        user.save()
        UserRole.objects.get_or_create(user=user, role=role)
        self.stdout.write(self.style.SUCCESS(f"Owner account is ready for {user.email}."))
