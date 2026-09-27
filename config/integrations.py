"""Host-owned optional dependency and environment validation (no Authkits imports)."""

from importlib.util import find_spec

from django.core.exceptions import ImproperlyConfigured


def require_extra(module, extra):
    if find_spec(module) is None:
        raise ImproperlyConfigured(
            f"Install the licensed Authkits wheel with [{extra}] before enabling "
            f"this integration (authkits-django[{extra}])."
        )


def social_providers(environ):
    providers = {}
    for provider in ("github", "google"):
        prefix = f"AUTHKITS_{provider.upper()}"
        client_id = environ.get(f"{prefix}_CLIENT_ID", "").strip()
        client_secret = environ.get(f"{prefix}_CLIENT_SECRET", "").strip()
        if bool(client_id) != bool(client_secret):
            raise ImproperlyConfigured(
                f"Set both {prefix}_CLIENT_ID and {prefix}_CLIENT_SECRET."
            )
        if client_id:
            providers[provider] = {"CLIENT_ID": client_id, "CLIENT_SECRET": client_secret}
    if not providers:
        raise ImproperlyConfigured(
            "AUTHKITS_SOCIAL_ENABLED requires a complete GitHub or Google credential pair."
        )
    return providers
