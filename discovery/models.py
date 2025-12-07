import random
import time

from django.db import models
import uuid

from discovery.utils import id_generator


class BaseModelManager(models.Manager):
    def bulk_create(self, objs, *args, **kwargs):
        for obj in objs:
            if not obj.id:
                obj.id = random.getrandbits(48)
        return super().bulk_create(objs, *args, **kwargs)


class BaseModel(models.Model):
    id = models.BigAutoField(unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = BaseModelManager()

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = id_generator.generate_id()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AdminConfiguration(BaseModel):
    """
    This class is for storing configurable values
    """

    key = models.CharField(max_length=64)
    value = models.CharField(max_length=128)
    type = models.CharField(max_length=64)


class Product(BaseModel):
    name = models.TextField()
    description = models.TextField(null=True, blank=True, default=None)
    category = models.CharField(max_length=255, null=True, blank=True, default=None)
    manufacturer = models.TextField(null=True, blank=True, default=None)
    production_date = models.DateField(null=True, blank=True, default=None)
    expiry_date = models.DateField(null=True, blank=True, default=None)
    distributor = models.TextField(null=True, blank=True, default=None)
    barcode = models.CharField(max_length=100, null=True, blank=True, default=None)

    def __str__(self):
        return self.name


class ProductMetadata(BaseModel):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="metadata"
    )
    net_weight = models.CharField(max_length=50, null=True, blank=True, default=None)
    volume = models.CharField(max_length=50, null=True, blank=True, default=None)
    quantity_in_package = models.PositiveIntegerField(
        null=True, blank=True, default=None
    )
    size = models.CharField(max_length=50, null=True, blank=True, default=None)
    part_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        default=None,
        help_text="Part number of the product, OEM or aftermarket. Stored as text to support alphanumeric values.",
    )
    age_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Age rating of the product (e.g., 18 for 18+).",
    )
    additional_info = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="A dictionary for any other relevant metadata.",
    )
    country_of_origin = models.TextField(null=True, blank=True, default=None)
    ingredients = models.JSONField(default=list, null=True, blank=True)
    materials = models.JSONField(default=list, null=True, blank=True)
    warnings = models.JSONField(default=list, null=True, blank=True)
    usage_directions = models.TextField(null=True, blank=True, default=None)

    def __str__(self):
        return f"Metadata for {self.product.name}"
