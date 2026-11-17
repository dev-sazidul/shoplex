from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.platform.audit import record_audit
from apps.platform.models import SellerApplication, SellerDocument
from apps.sellers.services import reviewer_role_for


class SellerDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={(200, "application/octet-stream"): OpenApiResponse(response=OpenApiTypes.BINARY, description="Private business verification document")})
    def get(self, request, application_id, document_id):
        reviewer_role = reviewer_role_for(request.user)
        application = get_object_or_404(SellerApplication, pk=application_id)
        document = get_object_or_404(SellerDocument, pk=document_id, application=application)
        record_audit(
            request,
            "seller_application.document_viewed",
            resource_type="seller_document",
            resource_id=document.pk,
            metadata={"application_id": application.pk, "reviewer_role": reviewer_role},
        )
        response = FileResponse(document.file.open("rb"), content_type=document.content_type)
        response["Content-Disposition"] = f'attachment; filename="{document.original_name.replace(chr(34), "")}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response
