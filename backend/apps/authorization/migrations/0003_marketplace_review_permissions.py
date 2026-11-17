from django.db import migrations


PERMISSIONS = [
    ("seller.applications.review", "Review seller applications"),
    ("catalog.products.review", "Review product submissions"),
    ("commerce.commissions.manage", "Manage marketplace commission rules"),
    ("commerce.shipping.manage", "Manage marketplace shipping rules"),
]


def grant_review_permissions(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    RolePermission = apps.get_model("authorization", "RolePermission")
    admin_role = Role.objects.get(key="admin")
    owner_role = Role.objects.get(key="owner")
    for key, description in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(key=key, defaults={"description": description})
        role = admin_role if key in {"seller.applications.review", "catalog.products.review"} else owner_role
        RolePermission.objects.get_or_create(role=role, permission=permission)


def remove_review_permissions(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.filter(key__in=[key for key, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("authorization", "0002_seed_roles_and_permissions")]
    operations = [migrations.RunPython(grant_review_permissions, remove_review_permissions)]
