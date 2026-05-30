from django.contrib import admin
from .models import FundraisingCampaign, Donation, FundraisingOrganization, FundraisingSale


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(FundraisingCampaign)
class FundraisingCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "goal_amount", "raised_amount", "percent_raised", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("title", "beneficiary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [DonationInline]
    readonly_fields = ("percent_raised",)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("donor_name", "campaign", "amount", "is_anonymous", "created_at")
    list_filter = ("is_anonymous", "campaign")
    search_fields = ("donor_name", "donor_email", "shopify_order_id")
    date_hierarchy = "created_at"


@admin.register(FundraisingOrganization)
class FundraisingOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "email", "payout_percentage", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "email")


@admin.register(FundraisingSale)
class FundraisingSaleAdmin(admin.ModelAdmin):
    list_display = ("campaign", "organization", "gross_amount", "payout_amount", "shopify_order_id", "created_at")
    search_fields = ("shopify_order_id", "reference")
    date_hierarchy = "created_at"
