"""Django settings for the public Authkits Django reference application.

The project intentionally behaves like a normal customer-owned host application.
Authkits owns authentication/security behavior; this project owns deployment,
environment loading, email, database, middleware and Django configuration.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from .integrations import require_extra, social_providers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=()):
    raw = os.environ.get(name)
    if raw is None:
        return tuple(default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


DEBUG = env_bool("DJANGO_DEBUG", True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-authkits-reference-app-development-only"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG is disabled.")

ALLOWED_HOSTS = list(env_list("DJANGO_ALLOWED_HOSTS", ("127.0.0.1", "localhost")))
CSRF_TRUSTED_ORIGINS = list(env_list("DJANGO_CSRF_TRUSTED_ORIGINS"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "authkits",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "authkits.security.middleware.SessionSecurityMiddleware",
    "authkits.admin.AdminSecurityMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL",
    "Authkits Example <authkits@localhost>",
)

_totp_keys = env_list("AUTHKITS_TOTP_KEYS")
_allowed_mfa_methods = env_list("AUTHKITS_MFA_ALLOWED_METHODS", ("totp", "email"))

AUTHKITS = {
    "ACCOUNTS": {
        "REQUIRE_EMAIL_VERIFICATION": env_bool(
            "AUTHKITS_REQUIRE_EMAIL_VERIFICATION",
            True,
        ),
    },
    "UI": {
        "LOGIN_REDIRECT": os.environ.get(
            "AUTHKITS_LOGIN_REDIRECT",
            "/auth/security/",
        ),
    },
    "EMAIL": {
        "BASE_URL": os.environ.get("AUTHKITS_EMAIL_BASE_URL", "").strip(),
    },
    "SECURITY": {
        "SESSION_TRACKING": env_bool("AUTHKITS_SESSION_TRACKING", True),
        "TRUSTED_DEVICES": env_bool("AUTHKITS_TRUSTED_DEVICES", False),
        "DEVICE_TTL": int(os.environ.get("AUTHKITS_DEVICE_TTL", "2592000")),
    },
    "ADMIN": {
        "ENABLED": env_bool("AUTHKITS_ADMIN_ENABLED", True),
        "REQUIRE_MFA": env_bool("AUTHKITS_ADMIN_REQUIRE_MFA", True),
        "REQUIRE_VERIFIED_EMAIL": env_bool(
            "AUTHKITS_ADMIN_REQUIRE_VERIFIED_EMAIL",
            True,
        ),
        "FRESH_MFA_TTL": int(
            os.environ.get("AUTHKITS_ADMIN_FRESH_MFA_TTL", "300")
        ),
    },
    "MFA": {
        "ENFORCED": env_bool("AUTHKITS_MFA_ENFORCED", False),
        "ALLOWED_METHODS": _allowed_mfa_methods,
        "TOTP_ENABLED": bool(_totp_keys),
        "TOTP_ISSUER": os.environ.get(
            "AUTHKITS_TOTP_ISSUER",
            "Authkits Example",
        ),
        "ENCRYPTION_KEYS": _totp_keys,
    },
    "LICENSING": {
        "LICENSE_KEY": os.environ.get("AUTHKITS_LICENSE_KEY", "").strip(),
        "ENTITLEMENT_FILE": os.environ.get(
            "AUTHKITS_ENTITLEMENT_FILE",
            "",
        ).strip(),
        "ACTIVATION_URL": os.environ.get(
            "AUTHKITS_ACTIVATION_URL",
            "https://authkits.com/api/v1/licenses/activate",
        ).strip(),
        "CONNECT_TIMEOUT": int(
            os.environ.get("AUTHKITS_ACTIVATION_CONNECT_TIMEOUT", "5")
        ),
        "READ_TIMEOUT": int(
            os.environ.get("AUTHKITS_ACTIVATION_READ_TIMEOUT", "10")
        ),
    },
}


# Optional boundaries are opt-in; a base wheel never imports DRF or allauth.
AUTHKITS_API_ENABLED = env_bool("AUTHKITS_API_ENABLED", False)
AUTHKITS_SOCIAL_ENABLED = env_bool("AUTHKITS_SOCIAL_ENABLED", False)
AUTHKITS["API"] = {
    "ENABLED": AUTHKITS_API_ENABLED,
    "CREDENTIAL_TTL": int(os.environ.get("AUTHKITS_API_CREDENTIAL_TTL", "604800")),
    "CREDENTIAL_MAX_ACTIVE": int(os.environ.get("AUTHKITS_API_CREDENTIAL_MAX_ACTIVE", "10")),
}
AUTHKITS["SOCIAL"] = {"ENABLED": AUTHKITS_SOCIAL_ENABLED, "MODE": "managed"}

if AUTHKITS_API_ENABLED:
    require_extra("rest_framework", "api")
    INSTALLED_APPS += ["rest_framework"]

if AUTHKITS_SOCIAL_ENABLED:
    require_extra("allauth", "social")
    AUTHKITS["SOCIAL"]["PROVIDERS"] = social_providers(os.environ)
    INSTALLED_APPS += [
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
        *[
            f"allauth.socialaccount.providers.{provider}"
            for provider in AUTHKITS["SOCIAL"]["PROVIDERS"]
        ],
    ]
    AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
    MIDDLEWARE += ["allauth.account.middleware.AccountMiddleware"]
    SOCIALACCOUNT_ADAPTER = "authkits.integrations.social.AuthkitsSocialAccountAdapter"
    SOCIALACCOUNT_QUERY_EMAIL = True
    SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
    SOCIALACCOUNT_LOGIN_ON_GET = False
    SOCIALACCOUNT_STORE_TOKENS = False
    # Keep allauth's independent password/reset/email flows out of this host.
    # Authkits enforces verified email and MFA in its social adapter.
    SOCIALACCOUNT_ONLY = True
    ACCOUNT_EMAIL_VERIFICATION = "none"
    SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
    ACCOUNT_LOGIN_METHODS = {"username", "email"}
    ACCOUNT_SIGNUP_FIELDS = ["username*", "email*", "password1*", "password2*"]
    LOGIN_REDIRECT_URL = AUTHKITS["UI"]["LOGIN_REDIRECT"]
    LOGOUT_REDIRECT_URL = "/"
