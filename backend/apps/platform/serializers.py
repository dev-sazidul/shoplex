from rest_framework import serializers

from apps.platform.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "category", "title", "body", "payload", "read_at", "created_at"]
        read_only_fields = fields
