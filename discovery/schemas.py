import graphene
from graphene_django import DjangoObjectType

from discovery.models import Product, ProductMetadata


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"


class ProductMetadataType(DjangoObjectType):
    class Meta:
        model = ProductMetadata
        fields = "__all__"


class Query(graphene.ObjectType):
    all_products = graphene.List(ProductType)
    product_by_name = graphene.Field(ProductType, name=graphene.String(required=True))

    def resolve_all_products(root, info):
        return Product.objects.prefetch_related("metadata").all()

    def resolve_product_by_name(root, info, name):
        try:
            return Product.objects.get(name=name)
        except Product.DoesNotExist:
            return None


schema = graphene.Schema(query=Query)
