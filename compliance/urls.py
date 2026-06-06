from django.urls import path

from compliance import views

app_name = "compliance"

urlpatterns = [
    path("", views.compliance_dashboard, name="dashboard"),
]
