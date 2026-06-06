from django.urls import path

from family import views

app_name = "family"

urlpatterns = [
    path("", views.request_access, name="request_access"),
    path("acces/<str:token>/", views.verify, name="verify"),
    path("portail/", views.dashboard, name="dashboard"),
    path("deconnexion/", views.logout_view, name="logout"),
]
