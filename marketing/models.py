"""
Marketing app — email subscriber list only.

Coupons and discount codes are now managed in Shopify Admin.
Campaign management is handled by Shopify Email / Klaviyo / Mailchimp.
"""

from django.db import models


class EmailSubscriber(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=100, blank=True)
    referral_code = models.CharField(max_length=80, blank=True)
    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=120, blank=True)
    landing_path = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email
