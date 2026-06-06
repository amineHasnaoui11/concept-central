from django.urls import path

from wellbeing import views

app_name = "wellbeing"

urlpatterns = [
    path("", views.dossier_list, name="dossier_list"),
    path("nouveau/<int:student_id>/", views.create_dossier, name="create_dossier"),
    path("<int:pk>/", views.dossier_detail, name="dossier_detail"),
]
