from django.contrib import admin
from .models import EmailSubscriber


@admin.register(EmailSubscriber)
class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "utm_source", "utm_campaign", "is_active", "subscribed_at")
    list_filter = ("is_active", "source", "utm_source")
    search_fields = ("email", "referral_code", "utm_campaign")
    date_hierarchy = "subscribed_at"
