"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from common.auth_views import LoginView
from django.http import HttpResponse

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
    ),
    path(
        'google4c2e35c31a92bd53.html', 
        lambda request: HttpResponse("google-site-verification: google4c2e35c31a92bd53.html")
    ),
    path("login/", LoginView.as_view(), name="direct-login"),
    path("", include("main.v1.urls")),
    path("", include("client.v1.urls")),
    path("api/v1/consultants/", include("consultation.v1.urls")),
    path("", include("scheduling.v1.urls")),
    path("", include("notification.v1.urls")),
    path("admin-portal/", include("admin_portal.urls")),
    path("", include("payment.v1.urls")),
    path("api/", include("common.urls")),
    path("pm/", include("pm.urls")),
]

# Serve media files in both development and production
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
