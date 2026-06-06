from django import template

from notifications.services import unread_count

register = template.Library()


@register.inclusion_tag("notifications/_bell.html", takes_context=True)
def notification_bell(context):
    request = context.get("request")
    user = getattr(request, "user", None) if request else None
    return {
        "unread": unread_count(user) if user and user.is_authenticated else 0,
    }
