from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField()
    image = models.ImageField(upload_to="pages/", blank=True)
    image_alt = models.CharField(max_length=200, blank=True)
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    ENTRY_TYPE_CHOICES = [
        ("slow_living", "Slow Living"),
        ("ritual_routines", "Ritual-Based Routines"),
        ("seasonal_reflections", "Seasonal Reflections"),
        ("brewing_philosophy", "Brewing Philosophy"),
        ("brand_storytelling", "Brand Storytelling"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("unpublished", "Unpublished"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, default="slow_living")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    tags = models.CharField(max_length=300, blank=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to="blog/", blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        if self.status == "published":
            self.is_published = True
            if not self.published_at:
                from django.utils import timezone
                self.published_at = timezone.now()
        elif self.status in ["draft", "unpublished"]:
            self.is_published = False
        elif self.status == "scheduled":
            if self.published_at:
                from django.utils import timezone
                if self.published_at <= timezone.now():
                    self.status = "published"
                    self.is_published = True
                else:
                    self.is_published = False
            else:
                self.is_published = False

        super().save(*args, **kwargs)


class RitualJournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="journal_entries")
    title = models.CharField(max_length=200)
    body = models.TextField()
    brew_method = models.CharField(max_length=100, blank=True)
    product_handle = models.CharField(
        max_length=200,
        blank=True,
        help_text="Shopify product handle associated with this journal entry (optional).",
    )
    mood = models.CharField(max_length=50, blank=True)
    tags = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "ritual journal entries"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class JournalPost(BlogPost):
    class Meta:
        proxy = True
        verbose_name = "journal post"
        verbose_name_plural = "journal posts"


class WholesaleInquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    company_name = models.CharField(max_length=180)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=160, blank=True)
    monthly_volume = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_wholesale_inquiries",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_wholesale_inquiries",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.email})"


class AmbassadorInquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    social_handle = models.CharField(max_length=120)
    primary_platform = models.CharField(max_length=80)
    audience_size = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=120, blank=True)
    pitch = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_ambassador_inquiries",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_ambassador_inquiries",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.primary_platform})"


class WholesaleInquiryNote(models.Model):
    inquiry = models.ForeignKey(WholesaleInquiry, on_delete=models.CASCADE, related_name="internal_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Wholesale note #{self.pk}"


class AmbassadorInquiryNote(models.Model):
    inquiry = models.ForeignKey(AmbassadorInquiry, on_delete=models.CASCADE, related_name="internal_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ambassador note #{self.pk}"


class ContentBlock(models.Model):
    """Editable content block that can be placed on any storefront page."""

    PAGE_CHOICES = [
        ("home", "Home"),
        ("about", "About"),
        ("contact", "Contact"),
        ("policies", "Policies"),
        ("brewing_guides", "Brewing Guides"),
        ("ritual", "Ritual"),
        ("shop", "Shop / Product List"),
        ("custom", "Custom Page"),
    ]

    page_key = models.CharField(max_length=80, choices=PAGE_CHOICES, default="home")
    section_key = models.CharField(
        max_length=80,
        help_text="Unique slot identifier on that page, e.g. 'hero', 'intro', 'banner_1'.",
    )
    label = models.CharField(max_length=200, help_text="Admin-facing name shown in the portal.")
    body = models.TextField(
        blank=True,
        help_text="HTML content. Use basic tags: &lt;p&gt;, &lt;h2&gt;, &lt;strong&gt;, &lt;em&gt;, &lt;a&gt;, &lt;ul&gt;, &lt;li&gt;, &lt;img&gt;.",
    )
    image = models.ImageField(upload_to="content_blocks/", blank=True)
    image_alt = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first when multiple blocks share the same section.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page_key", "sort_order", "section_key"]
        verbose_name = "content block"
        verbose_name_plural = "content blocks"

    def __str__(self):
        return f"{self.get_page_key_display()} › {self.label}"
