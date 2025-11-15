"""
URL configuration for tutor_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import custom admin site
from tutor_platform.admin import admin_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-panel/", admin_site.urls),
    path("admin-panel/", include("admin_portal.urls")),
    path("", include("accounts.urls")),
    # Search URLs
    path("search/", include("search.urls", namespace="search")),
    # Requirements URLs
    path("requirements/", include("requirements.urls", namespace="requirements")),
    # Messaging URLs
    path("messages/", include("messaging.urls", namespace="messaging")),
    # Notifications URLs
    path("notifications/", include("notifications.urls", namespace="notifications")),
    # Payments URLs
    path("payments/", include("paymentsdetails.urls", namespace="paymentsdetails")),
    # PayPal Integration URLs
    path("paypal/", include("paypal_integration.urls", namespace="paypal_integration")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
