from django.db import migrations


PERMISSION_KEY = "platform.analytics.read"


def grant_analytics_permission(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    RolePermission = apps.get_model("authorization", "RolePermission")
    permission, _ = Permission.objects.get_or_create(
        key=PERMISSION_KEY,
        defaults={"description": "View authorized marketplace business analytics"},
    )
    for role_key in ("owner", "manager"):
        role = Role.objects.get(key=role_key)
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_analytics_permission(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.filter(key=PERMISSION_KEY).delete()


class Migration(migrations.Migration):
    dependencies = [("authorization", "0003_marketplace_review_permissions")]
    operations = [migrations.RunPython(grant_analytics_permission, remove_analytics_permission)]
