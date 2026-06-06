from django.urls import path

from notifications import views

app_name = "notifications"

urlpatterns = [
    path("", views.list_view, name="list"),
    path("ouvrir/<int:pk>/", views.open_notification, name="open"),
    path("tout-lu/", views.mark_all_read_view, name="mark_all_read"),
]
