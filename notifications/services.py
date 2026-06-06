from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import Notification


def notify(*, event, title, message="", link="", recipient_user=None,
           recipient_email="", payload=None, also_email=False):
    if not recipient_user and not recipient_email:
        raise ValueError("Une notification doit avoir un destinataire.")

    notif = Notification.objects.create(
        recipient_user=recipient_user,
        recipient_email=recipient_email or "",
        channel=Notification.Channel.IN_APP if recipient_user else Notification.Channel.EMAIL,
        event=event,
        title=title,
        message=message,
        link=link,
        payload=payload or {},
    )

    target_email = recipient_email or (recipient_user.email if recipient_user else None)
    if (also_email or not recipient_user) and target_email:
        _send_email(target_email, title, message, link, notif)

    return notif


def _send_email(to_email, title, message, link, notif):
    try:
        body = [message or ""]
        if link:
            body.append(f"\nLien : {link}")
        send_mail(
            subject=f"[{getattr(settings, 'SITE_NAME', 'Concept Central')}] {title}",
            message="\n".join(body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        notif.sent_via_email_at = timezone.now()
        notif.save(update_fields=["sent_via_email_at"])
    except Exception:
        pass


def mark_all_read(user):
    return Notification.objects.filter(
        recipient_user=user, read_at__isnull=True
    ).update(read_at=timezone.now())


def unread_count(user):
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(
        recipient_user=user, read_at__isnull=True
    ).count()
