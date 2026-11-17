from rest_framework import serializers


class CartLineSchema(serializers.Serializer):
    id = serializers.IntegerField()
    product = serializers.DictField()
    variant = serializers.DictField(allow_null=True)
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class CartSchema(serializers.Serializer):
    items = CartLineSchema(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    item_count = serializers.IntegerField()


class CouponInputSchema(serializers.Serializer):
    code = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
