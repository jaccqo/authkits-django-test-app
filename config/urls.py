from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.decorators.http import require_safe

from .views import home

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("auth/", include("authkits.urls")),
]


if settings.AUTHKITS_API_ENABLED:
    urlpatterns += [path("api/v1/auth/", include("authkits.api.urls"))]

if settings.AUTHKITS_SOCIAL_ENABLED:
    from authkits.accounts.views import logout_view

    urlpatterns += [
        path("accounts/logout/", logout_view),
        path("accounts/login/", require_safe(RedirectView.as_view(pattern_name="authkits:login"))),
        path(
            "accounts/3rdparty/",
            require_safe(RedirectView.as_view(pattern_name="authkits:social_accounts")),
        ),
        path("accounts/", include("allauth.urls")),
    ]
