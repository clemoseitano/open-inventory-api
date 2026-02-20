import random
from django.db import models
from django.contrib.auth.models import User
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


class Tenant(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(
        User, related_name="owned_tenants", on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name


class TenantMember(BaseModel):
    ROLE_CHOICES = [("admin", "Admin"), ("staff", "Staff")]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tenant_memberships"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="staff")

    class Meta:
        unique_together = ("user", "tenant")

    def __str__(self):
        return f"{self.user.username} ({self.role}) @ {self.tenant.name}"


class SyncPushLog(BaseModel):
    """Temporary storage for raw incoming batches. Purgeable."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    tenant_member = models.ForeignKey(TenantMember, on_delete=models.CASCADE)
    data = models.JSONField()


class SyncJournal(BaseModel):
    """The sequenced stream of finalized actions for pulls."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="sync_journal"
    )
    tenant_member = models.ForeignKey(TenantMember, on_delete=models.CASCADE)
    action_id = models.CharField(max_length=255, unique=True)
    action_type = models.CharField(max_length=50)
    payload = models.JSONField()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.action_type} @ {self.created_at}"


class AdminConfiguration(BaseModel):
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
    part_number = models.CharField(max_length=100, null=True, blank=True, default=None)
    age_rating = models.PositiveIntegerField(null=True, blank=True, default=None)
    additional_info = models.JSONField(default=dict, null=True, blank=True)
    country_of_origin = models.TextField(null=True, blank=True, default=None)
    ingredients = models.JSONField(default=list, null=True, blank=True)
    materials = models.JSONField(default=list, null=True, blank=True)
    warnings = models.JSONField(default=list, null=True, blank=True)
    usage_directions = models.TextField(null=True, blank=True, default=None)
