from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts import views as accounts_views
from concept_central import views as core_views

handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.dashboard, name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("inscription/", accounts_views.student_signup, name="student_signup"),

    # === Password reset flow ===
    path(
        "accounts/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url="/accounts/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/password-reset/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/accounts/password-reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("students/", include("students.urls")),
    path("education/", include("education.urls")),
    path("wellbeing/", include("wellbeing.urls")),
    path("famille/", include("family.urls")),
    path("notifications/", include("notifications.urls")),
    path("compliance/", include("compliance.urls")),
    path("meetings/", include("meetings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
