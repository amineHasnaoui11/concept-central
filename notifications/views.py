from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.models import Notification
from notifications.services import mark_all_read


@login_required
def list_view(request):
    qs = Notification.objects.filter(recipient_user=request.user)
    unread_only = request.GET.get("filter") == "unread"
    if unread_only:
        qs = qs.filter(read_at__isnull=True)
    return render(request, "notifications/list.html", {
        "notifications": qs[:100],
        "unread_only": unread_only,
    })


@login_required
def open_notification(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient_user=request.user)
    if not notif.read_at:
        notif.read_at = timezone.now()
        notif.save(update_fields=["read_at"])
    if notif.link:
        return HttpResponseRedirect(notif.link)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read_view(request):
    mark_all_read(request.user)
    return redirect("notifications:list")
