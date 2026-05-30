from django.contrib import admin
from .models import (
    Page, BlogPost, ContentBlock,
    WholesaleInquiry, WholesaleInquiryNote,
    AmbassadorInquiry, AmbassadorInquiryNote,
    RitualJournalEntry,
)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "entry_type", "status", "author", "published_at")
    list_filter = ("status", "entry_type")
    search_fields = ("title", "tags")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("label", "page_key", "section_key", "is_active", "sort_order")
    list_filter = ("page_key", "is_active")
    search_fields = ("label", "section_key")
    ordering = ("page_key", "sort_order")


class WholesaleInquiryNoteInline(admin.TabularInline):
    model = WholesaleInquiryNote
    extra = 1


@admin.register(WholesaleInquiry)
class WholesaleInquiryAdmin(admin.ModelAdmin):
    list_display = ("company_name", "name", "email", "location", "created_at")
    search_fields = ("company_name", "name", "email")
    inlines = [WholesaleInquiryNoteInline]
    date_hierarchy = "created_at"


class AmbassadorInquiryNoteInline(admin.TabularInline):
    model = AmbassadorInquiryNote
    extra = 1


@admin.register(AmbassadorInquiry)
class AmbassadorInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "primary_platform", "social_handle", "created_at")
    search_fields = ("name", "email", "social_handle")
    inlines = [AmbassadorInquiryNoteInline]
    date_hierarchy = "created_at"


@admin.register(RitualJournalEntry)
class RitualJournalEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "brew_method", "is_public", "created_at")
    list_filter = ("is_public",)
    search_fields = ("title", "body")
