from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("instavault.apps.landing.urls", namespace="index")),
    path("users/", include("instavault.apps.users.urls", namespace="users")),
    path("planner/", include("instavault.apps.planner.urls", namespace="planner")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
