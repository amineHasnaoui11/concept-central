from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("invitations/<int:student_id>/generer/", views.invitation_generate, name="invitation_generate"),
    path("invitations/<int:pk>/revoquer/", views.invitation_revoke, name="invitation_revoke"),
]
