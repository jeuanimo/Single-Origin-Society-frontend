from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def render_block(page_key, section_key):
    """
    Render a ContentBlock for the given page/section.
    Returns safe HTML string if an active block exists, otherwise empty string.

    Usage in templates:
        {% load content_blocks %}
        {% render_block "home" "hero_text" %}
    """
    from content.models import ContentBlock  # local import avoids circular deps at module load

    try:
        block = ContentBlock.objects.get(page_key=page_key, section_key=section_key, is_active=True)
    except ContentBlock.DoesNotExist:
        return ""
    except ContentBlock.MultipleObjectsReturned:
        # When multiple blocks share the same slot, take the lowest sort_order
        block = ContentBlock.objects.filter(
            page_key=page_key, section_key=section_key, is_active=True
        ).order_by("sort_order").first()

    parts = []
    if block.image:
        alt = block.image_alt or ""
        parts.append(
            f'<img src="{block.image.url}" alt="{alt}" class="content-block-img">'
        )
    if block.body:
        parts.append(block.body)

    return mark_safe("".join(parts))


@register.inclusion_tag("content/blocks_section.html")
def render_blocks(page_key, section_key):
    """
    Render all active ContentBlocks for the given page/section in order.
    Use this tag when you expect multiple blocks in one slot.

    Usage:
        {% load content_blocks %}
        {% render_blocks "home" "banner" %}
    """
    from content.models import ContentBlock

    blocks = ContentBlock.objects.filter(
        page_key=page_key, section_key=section_key, is_active=True
    ).order_by("sort_order")
    return {"blocks": blocks}
