from django.contrib import admin
from .models import TastingNote, BrewingGuide


@admin.register(TastingNote)
class TastingNoteAdmin(admin.ModelAdmin):
    list_display = ("product_name", "title", "origin", "rating", "created_at")
    search_fields = ("product_name", "product_handle", "title", "tags")
    list_filter = ("rating",)


@admin.register(BrewingGuide)
class BrewingGuideAdmin(admin.ModelAdmin):
    list_display = ("title", "guide_type", "audience_level", "is_published", "created_at")
    list_filter = ("guide_type", "audience_level", "is_published")
    search_fields = ("title", "product_handle", "tags")
    prepopulated_fields = {"slug": ("title",)}
