"""Public CI tests: intentionally no Authkits wheel or optional SDK required."""

import os
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values

from config.integrations import require_extra, social_providers

ROOT = Path(__file__).resolve().parents[1]


def settings(**overrides):
    environment = {key: value or "" for key, value in dotenv_values(ROOT / ".env.example").items()}
    environment.update(overrides)
    with patch.dict(os.environ, environment, clear=True), patch("dotenv.load_dotenv"):
        return runpy.run_module("config.settings")


class HostContract(unittest.TestCase):
    def test_base_environment_without_optional_imports(self):
        with patch("config.integrations.find_spec", side_effect=AssertionError("optional import")):
            config = settings()
        self.assertTrue(config["DEBUG"])
        self.assertIn("127.0.0.1", config["ALLOWED_HOSTS"])
        self.assertFalse(config["AUTHKITS"]["API"]["ENABLED"])
        self.assertFalse(config["AUTHKITS"]["SOCIAL"]["ENABLED"])
        self.assertTrue(config["AUTHKITS"]["ADMIN"]["ENABLED"])
        self.assertTrue(config["AUTHKITS"]["ADMIN"]["REQUIRE_MFA"])
        self.assertTrue(config["AUTHKITS"]["ADMIN"]["REQUIRE_VERIFIED_EMAIL"])
        self.assertEqual(config["AUTHKITS"]["ADMIN"]["FRESH_MFA_TTL"], 300)
        self.assertIn("authkits.admin.AdminSecurityMiddleware", config["MIDDLEWARE"])
        self.assertNotIn("allauth", config["INSTALLED_APPS"])
        self.assertNotIn("rest_framework", config["INSTALLED_APPS"])
        self.assertEqual(config["AUTHKITS"]["LICENSING"]["LICENSE_KEY"], "")
        self.assertEqual(config["AUTHKITS"]["LICENSING"]["ENTITLEMENT_FILE"], "")

    def test_api_opt_in(self):
        with patch("config.integrations.find_spec", return_value=object()):
            config = settings(AUTHKITS_API_ENABLED="1")
        self.assertTrue(config["AUTHKITS"]["API"]["ENABLED"])
        self.assertIn("rest_framework", config["INSTALLED_APPS"])

    def test_missing_extras_are_actionable(self):
        for module, extra, flag in (
            ("rest_framework", "api", "AUTHKITS_API_ENABLED"),
            ("allauth", "social", "AUTHKITS_SOCIAL_ENABLED"),
        ):
            with self.subTest(extra=extra), patch("config.integrations.find_spec", return_value=None):
                with self.assertRaisesRegex(ImproperlyConfigured, extra):
                    require_extra(module, extra)
                with self.assertRaisesRegex(ImproperlyConfigured, extra):
                    settings(**{flag: "1"})

    def test_social_requires_credentials(self):
        with patch("config.integrations.find_spec", return_value=object()):
            with self.assertRaisesRegex(ImproperlyConfigured, "complete GitHub or Google"):
                settings(AUTHKITS_SOCIAL_ENABLED="1")

    def test_incomplete_credentials_do_not_leak(self):
        for suffix in ("CLIENT_ID", "CLIENT_SECRET"):
            with self.assertRaises(ImproperlyConfigured) as caught:
                social_providers({f"AUTHKITS_GOOGLE_{suffix}": "do-not-print-me"})
            self.assertNotIn("do-not-print-me", str(caught.exception))
            self.assertIn("AUTHKITS_GOOGLE_CLIENT_SECRET", str(caught.exception))

    def test_one_or_both_managed_providers(self):
        for selected in (("github",), ("google",), ("github", "google")):
            with self.subTest(selected=selected):
                env = {"AUTHKITS_SOCIAL_ENABLED": "1"}
                for provider in selected:
                    env[f"AUTHKITS_{provider.upper()}_CLIENT_ID"] = "local-test-id"
                    env[f"AUTHKITS_{provider.upper()}_CLIENT_SECRET"] = "local-test-secret"
                with patch("config.integrations.find_spec", return_value=object()):
                    config = settings(**env)
                self.assertEqual(set(config["AUTHKITS"]["SOCIAL"]["PROVIDERS"]), set(selected))
                for provider in selected:
                    self.assertIn(f"allauth.socialaccount.providers.{provider}", config["INSTALLED_APPS"])
                self.assertTrue(config["SOCIALACCOUNT_ONLY"])
                self.assertFalse(config["SOCIALACCOUNT_EMAIL_AUTHENTICATION"])
                self.assertFalse(config["SOCIALACCOUNT_LOGIN_ON_GET"])
                self.assertEqual(config["SOCIALACCOUNT_ADAPTER"],
                                 "authkits.integrations.social.AuthkitsSocialAccountAdapter")
                middleware = config["MIDDLEWARE"]
                self.assertLess(middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"),
                                middleware.index("allauth.account.middleware.AccountMiddleware"))

    def test_production_requires_secret(self):
        with self.assertRaisesRegex(RuntimeError, "DJANGO_SECRET_KEY"):
            settings(DJANGO_DEBUG="0", DJANGO_SECRET_KEY="")

    def test_totp_session_and_license_controls(self):
        config = settings(AUTHKITS_TOTP_KEYS="first,second", AUTHKITS_SESSION_TRACKING="0",
                          AUTHKITS_TRUSTED_DEVICES="1", AUTHKITS_LICENSE_KEY="local-test-key")
        self.assertEqual(config["AUTHKITS"]["MFA"]["ENCRYPTION_KEYS"], ("first", "second"))
        self.assertTrue(config["AUTHKITS"]["MFA"]["TOTP_ENABLED"])
        self.assertFalse(config["AUTHKITS"]["SECURITY"]["SESSION_TRACKING"])
        self.assertTrue(config["AUTHKITS"]["SECURITY"]["TRUSTED_DEVICES"])
        self.assertEqual(config["AUTHKITS"]["LICENSING"]["LICENSE_KEY"], "local-test-key")
