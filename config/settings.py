"""
Django settings for the public Authkits Django example application.

This project intentionally stays close to a normal host Django project so that
Authkits integration examples reflect the customer experience.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# Development-only fallback. Production deployments must provide DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-authkits-reference-app-development-only",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

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

# Keep email local and visible while exercising verification/recovery examples.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"



# Host-supplied configuration; never commit real keys.
_totp_keys = tuple(filter(None, os.environ.get("AUTHKITS_TOTP_KEYS", "").split(",")))
AUTHKITS = {
    "ACCOUNTS": {"REQUIRE_EMAIL_VERIFICATION": True},
    "UI": {"LOGIN_REDIRECT": "/auth/security/"},
    "SECURITY": {
        "SESSION_TRACKING": True,
        "TRUSTED_DEVICES": os.environ.get("AUTHKITS_TRUSTED_DEVICES", "0") == "1",
        "DEVICE_TTL": 2592000,
    },
    "MFA": {
        "TOTP_ENABLED": bool(_totp_keys),
        "TOTP_ISSUER": "Authkits Example",
        "ENCRYPTION_KEYS": _totp_keys,
    },
}
