from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(template_name="operations/login.html"), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("", include("operations.urls")),
]
