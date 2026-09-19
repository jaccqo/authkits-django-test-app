"""Django settings for the public Authkits Django reference application.

The project intentionally behaves like a normal customer-owned host application.
Authkits owns authentication/security behavior; this project owns deployment,
environment loading, email, database, middleware and Django configuration.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

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
}
