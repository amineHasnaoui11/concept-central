from django.urls import path

from education import views

app_name = "education"

urlpatterns = [
    path("saisie/", views.weekly_entry_create, name="weekly_create"),
    path("import-csv/", views.csv_upload, name="csv_upload"),
    path("alertes/", views.alert_list, name="alert_list"),
    path("alertes/<int:pk>/", views.alert_detail, name="alert_detail"),
    path("interventions/<int:pk>/outcome/", views.intervention_outcome, name="intervention_outcome"),
    path("seuils/", views.risk_config, name="risk_config"),
    path("export/", views.export_report, name="export_report"),
    path("demandes/creer/", views.teacher_request_create, name="teacher_request_create"),
    path("demandes/mes-demandes/", views.teacher_request_list, name="teacher_request_list"),
    path("demandes/conseiller/", views.counselor_request_list, name="counselor_request_list"),
    path("demandes/<int:pk>/", views.teacher_request_detail, name="teacher_request_detail"),
]
