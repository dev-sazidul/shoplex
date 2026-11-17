from django.db.models import Avg, Count
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import (
    Brand,
    Category,
    MarketingBanner,
    Product,
    ProductApproval,
    ProductImage,
    ProductReview,
    ProductVariant,
)
from apps.sellers.serializers import SellerProfilePublicSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "logo_url"]


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "sort_order"]

    def get_image_url(self, item) -> str:
        request = self.context.get("request")
        if not item.image:
            return ""
        url = item.image.url
        return request.build_absolute_uri(url) if request else url


class ProductVariantSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(max_length=80)

    class Meta:
        model = ProductVariant
        fields = ["id", "name", "sku", "options", "price", "stock_quantity", "is_active"]
        read_only_fields = ["id"]


class PublicProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    seller = SellerProfilePublicSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "sku", "price", "compare_at_price", "attributes",
            "category", "brand", "seller", "images", "variants", "average_rating", "review_count",
            "in_stock", "published_at",
        ]

    def get_average_rating(self, product) -> float | None:
        return getattr(product, "rating_average", None)

    def get_review_count(self, product) -> int:
        return getattr(product, "rating_count", 0)

    def get_in_stock(self, product) -> bool:
        return product.stock_quantity > 0 or any(variant.stock_quantity > 0 for variant in product.variants.all())


class ProductModerationSerializer(PublicProductSerializer):
    status = serializers.CharField(read_only=True)
    approval_version = serializers.IntegerField(read_only=True)
    approval_history = serializers.SerializerMethodField()

    class Meta(PublicProductSerializer.Meta):
        fields = [*PublicProductSerializer.Meta.fields, "status", "approval_version", "approval_history"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_approval_history(self, product) -> list[dict]:
        return [{
            "reviewer_role": approval.reviewer_role,
            "decision": approval.decision,
            "reason": approval.reason,
            "version": approval.version,
            "created_at": approval.created_at,
        } for approval in product.approval_history.select_related("reviewer").order_by("-created_at")[:12]]


class SellerProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.filter(is_active=True))
    brand = serializers.SlugRelatedField(slug_field="slug", queryset=Brand.objects.filter(is_active=True), required=False, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    approval_history = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "description", "sku", "price", "compare_at_price", "stock_quantity",
            "attributes", "category", "category_name", "brand", "status", "approval_version",
            "approval_history", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "status", "approval_version", "approval_history", "created_at", "updated_at"]

    def validate(self, attrs):
        price = attrs.get("price", getattr(self.instance, "price", None))
        compare = attrs.get("compare_at_price", getattr(self.instance, "compare_at_price", None))
        if compare is not None and price is not None and compare < price:
            raise serializers.ValidationError({"compare_at_price": "The original price must be greater than or equal to the current price."})
        if self.instance and self.instance.status == Product.Status.SUSPENDED:
            raise serializers.ValidationError("Suspended products cannot be edited until restored.")
        return attrs

    def create(self, validated_data):
        import uuid
        validated_data["seller"] = self.context["request"].user.seller_profile
        validated_data["slug"] = f"{slugify(validated_data['name'])[:190]}-{uuid.uuid4().hex[:8]}"
        return super().create(validated_data)

    def update(self, instance, validated_data):
        sensitive_fields = {"price", "compare_at_price", "category", "brand", "attributes"}
        requires_review = instance.status == Product.Status.PUBLISHED and any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in sensitive_fields
        )
        product = super().update(instance, validated_data)
        if requires_review:
            product.status = Product.Status.PENDING_APPROVAL
            product.approval_version += 1
            product.published_at = None
            product.save(update_fields=["status", "approval_version", "published_at", "updated_at"])
            from apps.catalog.services import notify_product_reviewers
            from apps.platform.audit import record_audit
            notify_product_reviewers(product)
            request = self.context.get("request")
            if request:
                record_audit(request, "product.sensitive_change_submitted", resource_type="product", resource_id=product.pk, metadata={"version": product.approval_version})
        elif product.status in [Product.Status.REJECTED, Product.Status.CHANGES_REQUESTED]:
            product.status = Product.Status.DRAFT
            product.save(update_fields=["status", "updated_at"])
        return product

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_approval_history(self, product) -> list[dict]:
        approvals = product.approval_history.select_related("reviewer").order_by("-created_at")[:8]
        return [{
            "reviewer_role": row.reviewer_role,
            "decision": row.decision,
            "reason": row.reason,
            "reviewer": row.reviewer.email,
            "version": row.version,
            "created_at": row.created_at,
        } for row in approvals]


class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "sort_order"]

    def validate_image(self, image):
        if image.size > 12 * 1024 * 1024:
            raise serializers.ValidationError("Image must be 12 MB or smaller.")
        if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise serializers.ValidationError("Upload a JPEG, PNG, or WebP image.")
        from PIL import Image, UnidentifiedImageError
        try:
            Image.open(image).verify()
        except (UnidentifiedImageError, OSError):
            raise serializers.ValidationError("The uploaded file is not a valid image.")
        finally:
            image.seek(0)
        return image


class ProductReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)

    class Meta:
        model = ProductReview
        fields = ["id", "rating", "title", "body", "is_verified_purchase", "customer_name", "product_name", "product_slug", "created_at"]
        read_only_fields = ["id", "is_verified_purchase", "customer_name", "created_at"]

    def get_customer_name(self, review) -> str:
        return review.customer.first_name

    def validate(self, attrs):
        from apps.commerce.models import OrderItem, SellerOrder
        product = self.context["product"]
        user = self.context["request"].user
        if ProductReview.objects.filter(product=product, customer=user).exists():
            raise serializers.ValidationError("You have already reviewed this product.")
        if not OrderItem.objects.filter(
            product=product,
            seller_order__order__customer=user,
            seller_order__status__in=[SellerOrder.Status.DELIVERED, SellerOrder.Status.COMPLETED],
        ).exists():
            raise serializers.ValidationError("A delivered purchase is required to review this product.")
        return attrs

    def create(self, validated_data):
        from apps.commerce.models import OrderItem, SellerOrder
        product = self.context["product"]
        user = self.context["request"].user
        has_purchase = OrderItem.objects.filter(
            product=product,
            seller_order__order__customer=user,
            seller_order__status__in=[SellerOrder.Status.DELIVERED, SellerOrder.Status.COMPLETED],
        ).exists()
        validated_data["customer"] = user
        validated_data["product"] = product
        validated_data["is_verified_purchase"] = has_purchase
        return super().create(validated_data)


class ProductApprovalSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ProductApproval.Decision.choices)
    reason = serializers.CharField(required=False, allow_blank=True)


class MarketingBannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MarketingBanner
        fields = ["title", "subtitle", "image_url", "target_url"]

    def get_image_url(self, banner) -> str:
        request = self.context.get("request")
        if not banner.image:
            return ""
        url = banner.image.url
        return request.build_absolute_uri(url) if request else url
