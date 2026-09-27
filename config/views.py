from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def home(request):
    return render(request, "home.html", {
        "api_enabled": settings.AUTHKITS_API_ENABLED,
        "social_enabled": settings.AUTHKITS_SOCIAL_ENABLED,
    })
