from django.db import migrations


MANAGER_PERMISSIONS = [
    ("manager.analytics.business", "View authorized business analytics and performance"),
    ("manager.reports.sellers", "View authorized seller performance reports"),
    ("manager.reports.products", "View authorized product compliance reports"),
    ("manager.reports.orders", "View authorized order and sales reports"),
    ("manager.reports.finance", "View authorized financial and revenue reports"),
    ("manager.admins.monitor", "Monitor assigned Admin accounts and team activity"),
    ("manager.shares.read", "View own authorized business share allocations and offers"),
    ("manager.shares.documents", "View own authorized business ownership documents"),
]

DEFAULT_MANAGER_GRANTS = {
    "manager.analytics.business",
    "manager.reports.orders",
    "manager.admins.monitor",
    "manager.shares.read",
    "manager.shares.documents",
}


def seed_manager_and_share_permissions(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    RolePermission = apps.get_model("authorization", "RolePermission")
    owner_role = Role.objects.get(key="owner")
    manager_role = Role.objects.get(key="manager")
    for key, description in MANAGER_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(key=key, defaults={"description": description})
        RolePermission.objects.get_or_create(role=owner_role, permission=permission)
        if key in DEFAULT_MANAGER_GRANTS:
            RolePermission.objects.get_or_create(role=manager_role, permission=permission)


def remove_manager_and_share_permissions(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.filter(key__in=[key for key, _ in MANAGER_PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("authorization", "0004_platform_analytics_permission")]
    operations = [migrations.RunPython(seed_manager_and_share_permissions, remove_manager_and_share_permissions)]
