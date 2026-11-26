from django.db import migrations


ADMIN_STAFF_PERMISSIONS = [
    ("admin.products.create", "Create platform-owned SHOPLEX products"),
    ("admin.products.edit", "Edit marketplace products"),
    ("admin.products.delete", "Delete marketplace products"),
    ("admin.products.publish", "Publish approved marketplace products"),
    ("admin.products.approve", "Approve submitted marketplace products"),
    ("admin.sellers.manage", "Manage seller applications and seller operations"),
    ("admin.customers.manage", "Manage customer accounts"),
    ("admin.orders.manage", "Manage marketplace orders and fulfillment"),
    ("admin.suppliers.manage", "Manage suppliers and supplier integrations"),
    ("admin.suppliers.import", "Import products from authorized suppliers"),
    ("admin.coupons.manage", "Manage coupons and promotions"),
    ("admin.shipping.manage", "Manage shipping rules and fulfillment zones"),
    ("admin.support.manage", "Handle customer support and disputes"),
    ("admin.reports.analytics", "View authorized operational reports and analytics"),
    ("admin.refunds.process", "Process authorized customer refunds"),
    ("admin.finance.reports", "View selected read-only financial reports authorized by Owner"),
]


def seed_admin_staff_permissions(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    Permission = apps.get_model("authorization", "Permission")
    RolePermission = apps.get_model("authorization", "RolePermission")
    owner_role = Role.objects.get(key="owner")
    # Grant all 16 permissions to Owner; Admin receives NONE automatically (Owner grants individually).
    for key, description in ADMIN_STAFF_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(key=key, defaults={"description": description})
        RolePermission.objects.get_or_create(role=owner_role, permission=permission)


def remove_admin_staff_permissions(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.filter(key__in=[key for key, _ in ADMIN_STAFF_PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("authorization", "0005_manager_and_share_permissions")]
    operations = [migrations.RunPython(seed_admin_staff_permissions, remove_admin_staff_permissions)]
