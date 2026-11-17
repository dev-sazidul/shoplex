from django.db import migrations


ROLES = [
    ("customer", "Customer"),
    ("seller", "Seller"),
    ("admin", "Admin"),
    ("manager", "Manager"),
    ("owner", "Owner"),
]
PERMISSIONS = [
    ("authorization.roles.read", "View platform roles"),
    ("authorization.permissions.read", "View platform permissions"),
    ("authorization.users.assign_role", "Assign non-owner roles to users"),
    ("platform.settings.manage", "Manage platform settings"),
    ("audit.read", "View audit history"),
]


def seed_foundation_access(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    RolePermission = apps.get_model("authorization", "RolePermission")
    roles = {key: Role.objects.get_or_create(key=key, defaults={"name": name})[0] for key, name in ROLES}
    permissions = [Permission.objects.get_or_create(key=key, defaults={"description": description})[0] for key, description in PERMISSIONS]
    for permission in permissions:
        RolePermission.objects.get_or_create(role=roles["owner"], permission=permission)


def remove_foundation_access(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    Role.objects.filter(key__in=[key for key, _ in ROLES]).delete()
    Permission.objects.filter(key__in=[key for key, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("authorization", "0001_initial")]
    operations = [migrations.RunPython(seed_foundation_access, remove_foundation_access)]
