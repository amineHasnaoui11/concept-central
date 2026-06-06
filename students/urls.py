from django.urls import path

from students import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("create/", views.student_create, name="create"),
    path("bulk-import/", views.student_bulk_import, name="bulk_import"),
    path("<int:pk>/", views.student_detail, name="detail"),
    path("<int:pk>/edit/", views.student_edit, name="edit"),
    path("<int:pk>/delete/", views.student_delete, name="delete"),
    path("<int:pk>/consents/", views.student_consents, name="consents"),
    path("<int:pk>/export/", views.student_data_export, name="data_export"),
]
