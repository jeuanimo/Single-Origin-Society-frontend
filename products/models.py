"""
Products app — content models only.

Product catalog (prices, inventory, variants) is now managed in Shopify.
This app retains BrewingGuide and TastingNote which are editorial content
created by staff and displayed alongside Shopify products.
"""

from django.db import models
from django.utils.text import slugify


class TastingNote(models.Model):
    """
    Editorial tasting notes written by staff.
    Linked to a Shopify product via handle (not a DB FK).
    """

    product_name = models.CharField(max_length=200, blank=True, help_text="Product display name")
    product_handle = models.CharField(
        max_length=200,
        blank=True,
        help_text="Shopify product handle (slug) for linking to the product page.",
    )
    title = models.CharField(max_length=100)
    body = models.TextField()
    aroma = models.CharField(max_length=200, blank=True)
    flavor = models.CharField(max_length=200, blank=True)
    finish = models.CharField(max_length=200, blank=True)
    origin = models.CharField(max_length=200, blank=True)
    pairings = models.CharField(max_length=200, blank=True)
    style_notes = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=250, blank=True)
    rating = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.product_name or "Untitled product"
        return f"{name} — {self.title}"


class BrewingGuide(models.Model):
    GUIDE_TYPE_CHOICES = [
        ("pour_over", "Pour-Over"),
        ("french_press", "French Press"),
        ("espresso_basics", "Espresso Basics"),
        ("tea_steeping", "Tea Steeping"),
        ("matcha_preparation", "Matcha Preparation"),
        ("other", "Other"),
    ]
    AUDIENCE_LEVEL_CHOICES = [
        ("beginner", "Beginner-Friendly"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    product_handle = models.CharField(
        max_length=200,
        blank=True,
        help_text="Shopify product handle this guide is associated with (optional).",
    )
    guide_type = models.CharField(max_length=30, choices=GUIDE_TYPE_CHOICES, default="other")
    audience_level = models.CharField(max_length=20, choices=AUDIENCE_LEVEL_CHOICES, default="beginner")
    tags = models.CharField(max_length=200, blank=True)
    is_premium_featured = models.BooleanField(default=False)
    method = models.CharField(max_length=100)
    description = models.TextField()
    instructions = models.TextField()
    water_temp = models.CharField(max_length=50, blank=True)
    brew_time = models.CharField(max_length=50, blank=True)
    grind_size = models.CharField(max_length=50, blank=True)
    ratio = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to="guides/", blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class BrewGuide(BrewingGuide):
    class Meta:
        proxy = True
        verbose_name = "brew guide"
        verbose_name_plural = "brew guides"
