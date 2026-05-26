"""
Fundraising app.

FundraisingCampaign and Donation are managed in Django.
FundraisingSale now references Shopify order IDs instead of the old
Django Order FK — orders live in Shopify.
"""

from django.db import models
from django.conf import settings


class FundraisingCampaign(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    story = models.TextField(blank=True)
    image = models.ImageField(upload_to="fundraising/", blank=True)
    goal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    raised_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    beneficiary = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def percent_raised(self):
        if self.goal_amount > 0:
            return int((self.raised_amount / self.goal_amount) * 100)
        return 0


class Donation(models.Model):
    campaign = models.ForeignKey(FundraisingCampaign, on_delete=models.CASCADE, related_name="donations")
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    donor_name = models.CharField(max_length=200)
    donor_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    shopify_order_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="Shopify order ID associated with this donation, if applicable.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        name = "Anonymous" if self.is_anonymous else self.donor_name
        return f"{name}: ${self.amount}"


class FundraisingOrganization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    contact_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    payout_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FundraisingSale(models.Model):
    """
    Records a sale attributed to a fundraising campaign.
    Shopify order ID is used in place of the old Django Order FK.
    Use Shopify Admin API (server-side) to look up order details when needed.
    """

    campaign = models.ForeignKey(FundraisingCampaign, on_delete=models.CASCADE, related_name="sales")
    organization = models.ForeignKey(
        FundraisingOrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="fundraising_sales"
    )
    shopify_order_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="Shopify order GID or order number attributed to this sale.",
    )
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campaign.title} sale ${self.gross_amount}"
