"""
Accounts app — simplified for Shopify-backed storefront.

The portal role-based permission system is removed since the backend
now runs on Shopify Admin. Only customer-facing accounts remain.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model. Commerce data (orders, addresses) now lives in Shopify.
    This model is used for staff logins to the Django content admin only.
    """

    phone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email or self.username
