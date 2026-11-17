from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.authorization.models import Role
from apps.catalog.models import (
    Brand,
    Category,
    MarketingBanner,
    NewsletterSubscription,
    Product,
    ProductApproval,
    ProductImage,
    ProductReview,
    ProductVariant,
)
from apps.catalog.serializers import (
    BrandSerializer,
    CategorySerializer,
    MarketingBannerSerializer,
    ProductApprovalSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
    ProductModerationSerializer,
    ProductReviewSerializer,
    ProductVariantSerializer,
    PublicProductSerializer,
    SellerProductSerializer,
)
from apps.catalog.services import review_product, reviewer_role_for, submit_product
from apps.platform.audit import record_audit
from apps.platform.models import Notification, SellerProfile
from apps.sellers.permissions import IsActiveSeller


class PublicProductQuerysetMixin:
    def public_products(self):
        return Product.objects.filter(
            status=Product.Status.PUBLISHED,
            category__is_active=True,
            seller__is_active=True,
            seller__user__is_active=True,
        ).select_related("category", "brand", "seller").prefetch_related("images", "variants").annotate(
            rating_average=Avg("reviews__rating", filter=Q(reviews__is_published=True)),
            rating_count=Count("reviews", filter=Q(reviews__is_published=True), distinct=True),
        )


class ProductListView(PublicProductQuerysetMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicProductSerializer

    def get_queryset(self):
        queryset = self.public_products()
        params = self.request.query_params
        search = params.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
                | Q(brand__name__icontains=search) | Q(category__name__icontains=search)
                | Q(seller__business_name__icontains=search)
            )
        if params.get("category"):
            queryset = queryset.filter(category__slug=params["category"])
        if params.get("brand"):
            queryset = queryset.filter(brand__slug=params["brand"])
        if params.get("seller"):
            queryset = queryset.filter(seller__store_slug=params["seller"])
        try:
            if params.get("min_price"):
                queryset = queryset.filter(price__gte=params["min_price"])
            if params.get("max_price"):
                queryset = queryset.filter(price__lte=params["max_price"])
        except (ValueError, TypeError):
            raise ValidationError({"price": "Price filters must be valid decimal amounts."})
        if params.get("in_stock") == "true":
            queryset = queryset.filter(Q(stock_quantity__gt=0) | Q(variants__stock_quantity__gt=0, variants__is_active=True)).distinct()
        ordering = {
            "price_asc": "price",
            "price_desc": "-price",
            "newest": "-published_at",
            "rating": "-rating_average",
            "popular": "-sales_count",
        }.get(params.get("sort", "newest"), "-published_at")
        if ordering == "-sales_count":
            queryset = queryset.annotate(sales_count=Count("order_lines", distinct=True))
        return queryset.order_by(ordering, "id")


class ProductDetailView(PublicProductQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return self.public_products()


class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True).select_related("parent")


class BrandListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BrandSerializer
    queryset = Brand.objects.filter(is_active=True)


class StorefrontView(PublicProductQuerysetMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: dict})
    def get(self, request):
        products = self.public_products()
        sellers = SellerProfile.objects.filter(is_active=True, products__status=Product.Status.PUBLISHED).annotate(
            product_count=Count("products", distinct=True),
        ).order_by("-product_count", "business_name")[:8]
        banners = MarketingBanner.objects.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=timezone.now()),
            Q(ends_at__isnull=True) | Q(ends_at__gte=timezone.now()),
        )
        return Response({
            "categories": CategorySerializer(Category.objects.filter(is_active=True, parent__isnull=True)[:12], many=True).data,
            "banners": MarketingBannerSerializer(banners, many=True, context={"request": request}).data,
            "featured_products": PublicProductSerializer(products.filter(is_featured=True)[:8], many=True, context={"request": request}).data,
            "trending_products": PublicProductSerializer(products.annotate(sales=Count("order_lines", distinct=True)).order_by("-sales", "-published_at")[:8], many=True, context={"request": request}).data,
            "best_sellers": PublicProductSerializer(products.annotate(sales=Count("order_lines", distinct=True)).order_by("-sales", "-published_at")[:8], many=True, context={"request": request}).data,
            "new_arrivals": PublicProductSerializer(products.order_by("-published_at")[:8], many=True, context={"request": request}).data,
            "special_offers": PublicProductSerializer(products.filter(compare_at_price__gt=0)[:8], many=True, context={"request": request}).data,
            "featured_sellers": [{"store_slug": item.store_slug, "business_name": item.business_name, "store_description": item.store_description, "product_count": item.product_count} for item in sellers],
        })


class ProductSuggestionView(PublicProductQuerysetMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=serializers.ListSerializer(child=serializers.DictField()))
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        products = self.public_products().filter(name__icontains=query).values("name", "slug")[:8]
        return Response(list(products))


class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductReviewSerializer

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    def get_product(self):
        return get_object_or_404(Product, slug=self.kwargs["slug"], status=Product.Status.PUBLISHED, seller__is_active=True)

    def get_queryset(self):
        return ProductReview.objects.filter(product=self.get_product(), is_published=True).select_related("customer")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["product"] = self.get_product()
        return context

    def perform_create(self, serializer):
        serializer.save()


class CustomerReviewListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductReviewSerializer

    def get_queryset(self):
        return ProductReview.objects.filter(customer=self.request.user).select_related("product").order_by("-created_at")


class SellerProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user.seller_profile).select_related("category", "brand").prefetch_related("approval_history")


class SellerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user.seller_profile).select_related("category", "brand").prefetch_related("approval_history")

    def perform_destroy(self, instance):
        if instance.status not in [Product.Status.DRAFT, Product.Status.REJECTED, Product.Status.CHANGES_REQUESTED]:
            raise ValidationError("Only draft or returned products may be deleted.")
        instance.delete()


class SellerProductSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]

    @extend_schema(request=None, responses=SellerProductSerializer)
    def post(self, request, product_id):
        product = submit_product(request, product_id)
        return Response(SellerProductSerializer(product, context={"request": request}).data, status=status.HTTP_202_ACCEPTED)


class SellerProductImageView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProductImageUploadSerializer

    def get_product(self):
        return get_object_or_404(Product, pk=self.kwargs["product_id"], seller=self.request.user.seller_profile)

    def get_queryset(self):
        return self.get_product().images.all()

    def get_serializer_class(self):
        return ProductImageSerializer if self.request.method == "GET" else ProductImageUploadSerializer

    def perform_create(self, serializer):
        product = self.get_product()
        if product.images.count() >= 8:
            raise ValidationError("A product may have up to eight images.")
        serializer.save(product=product)
        if product.status == Product.Status.PUBLISHED:
            product.status = Product.Status.PENDING_APPROVAL
            product.approval_version += 1
            product.published_at = None
            product.save(update_fields=["status", "approval_version", "published_at", "updated_at"])
            from apps.catalog.services import notify_product_reviewers
            notify_product_reviewers(product)


class SellerProductVariantListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = ProductVariantSerializer

    def get_product(self):
        return get_object_or_404(Product, pk=self.kwargs["product_id"], seller=self.request.user.seller_profile)

    def get_queryset(self):
        return self.get_product().variants.all()

    def perform_create(self, serializer):
        product = self.get_product()
        if product.status not in [Product.Status.DRAFT, Product.Status.REJECTED, Product.Status.CHANGES_REQUESTED]:
            raise ValidationError("Product variations can only be changed while the product is a draft or returned for changes.")
        serializer.save(product=product)


class SellerProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = ProductVariantSerializer

    def get_queryset(self):
        return ProductVariant.objects.filter(product_id=self.kwargs["product_id"], product__seller=self.request.user.seller_profile)

    def perform_update(self, serializer):
        variant = self.get_object()
        product = variant.product
        sensitive_fields = {"name", "options", "price"}
        requires_review = product.status == Product.Status.PUBLISHED and any(
            field in serializer.validated_data and serializer.validated_data[field] != getattr(variant, field)
            for field in sensitive_fields
        )
        serializer.save()
        if requires_review:
            product.status = Product.Status.PENDING_APPROVAL
            product.approval_version += 1
            product.published_at = None
            product.save(update_fields=["status", "approval_version", "published_at", "updated_at"])
            from apps.catalog.services import notify_product_reviewers
            notify_product_reviewers(product)
            record_audit(self.request, "product.variant_sensitive_change_submitted", resource_type="product", resource_id=product.pk, metadata={"version": product.approval_version})

    def perform_destroy(self, instance):
        if instance.product.status not in [Product.Status.DRAFT, Product.Status.REJECTED, Product.Status.CHANGES_REQUESTED]:
            raise ValidationError("Variants may only be removed while a product is a draft or returned for changes.")
        instance.delete()


class ProductApprovalQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductModerationSerializer

    def get_queryset(self):
        reviewer_role_for(self.request.user)
        return Product.objects.filter(status=Product.Status.PENDING_APPROVAL).select_related("seller", "category", "brand").prefetch_related("images", "approval_history")


class ProductReviewActionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ProductApprovalSerializer, responses=ProductModerationSerializer)
    def post(self, request, product_id):
        serializer = ProductApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = review_product(request, product_id, serializer.validated_data["decision"], serializer.validated_data.get("reason", ""))
        return Response(ProductModerationSerializer(product, context={"request": request}).data)


class NewsletterInputSerializer(serializers.Serializer):
    email = serializers.EmailField()


class NewsletterSubscribeView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "anon"

    @extend_schema(request=NewsletterInputSerializer, responses={200: dict, 201: dict})
    def post(self, request):
        serializer = NewsletterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription, created = NewsletterSubscription.objects.get_or_create(email=serializer.validated_data["email"], defaults={"is_active": True})
        if not subscription.is_active:
            subscription.is_active = True
            subscription.unsubscribed_at = None
            subscription.save(update_fields=["is_active", "unsubscribed_at"])
        return Response({"detail": "Subscription confirmed."}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
