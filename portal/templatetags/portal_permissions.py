from django import template

register = template.Library()


@register.filter(name="has_portal_perm")
def has_portal_perm(user, permission_key):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_staff
