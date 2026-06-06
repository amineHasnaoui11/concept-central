from django.urls import path

from meetings import views

app_name = "meetings"

urlpatterns = [
    path("", views.meeting_list, name="list"),
    path("dashboard-eleve/", views.student_dashboard, name="student_dashboard"),
    path("dossier/<int:dossier_id>/proposer/", views.propose_meeting, name="propose"),
    path("<int:pk>/", views.meeting_detail, name="detail"),
    path("<int:pk>/repondre/", views.respond_to_meeting, name="respond"),
    path("<int:pk>/annuler/", views.student_cancel_meeting, name="student_cancel"),
    path("<int:pk>/rejoindre/", views.join_meeting, name="join"),
]
