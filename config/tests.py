from copy import deepcopy
from html.parser import HTMLParser
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class Inputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and "name" in attrs:
            self.values[attrs["name"]] = attrs.get("value", "")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountSecurityIntegration(TestCase):
    def post(self, name, data):
        data = {**data, "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("authkits:" + name),
                data,
                HTTP_ORIGIN="http://testserver",
            )

    def code(self):
        fields = dict(
            line.split(": ", 1)
            for line in mail.outbox[-1].body.splitlines()
            if ": " in line
        )
        return {
            "challenge_id": fields["Challenge ID"],
            "secret": fields["Verification code"],
        }

    def test_home_links_and_protected_center(self):
        response = self.client.get("/")
        self.assertContains(response, reverse("authkits:signup"))
        self.assertContains(response, reverse("authkits:security_center"))
        self.assertEqual(
            self.client.get(reverse("authkits:security_center")).status_code, 302
        )

    def test_signup_mfa_and_session_integration(self):
        self.client = Client(enforce_csrf_checks=True)
        signup_page = self.client.get(reverse("authkits:signup"))
        self.assertEqual(signup_page["Referrer-Policy"], "same-origin")
        password = "Reference-Uncommon-Password-632!"
        result = self.post(
            "signup",
            {
                "username": "example",
                "email": "example@example.com",
                "password": password,
                "password_confirm": password,
            },
        )
        self.assertEqual(result.status_code, 302)
        self.assertContains(self.post("verify_email", self.code()), "Email verified")
        self.assertEqual(
            self.post(
                "login", {"identifier": "example", "password": password}
            ).status_code,
            302,
        )
        result = self.post(
            "mfa_management", {"action": "mfa.setup.email", "password": password}
        )
        setup = Inputs(result.content.decode()).values
        self.assertContains(
            self.post("mfa_confirm", {**setup, "code": self.code()["secret"]}),
            "MFA enabled",
        )
        self.post("logout", {})
        self.assertEqual(
            self.post("login", {"identifier": "example", "password": password}).url,
            reverse("authkits:mfa_login"),
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.post("mfa_login", {"method": "email", "action": "send_email"})
        result = self.post(
            "mfa_login", {"method": "email", "code": self.code()["secret"]}
        )
        self.assertEqual(result.status_code, 302)
        self.assertContains(
            self.client.get(reverse("authkits:security_center")), "Account security"
        )
        self.assertContains(
            self.client.get(reverse("authkits:security_sessions")), "Current session"
        )
        self.assertEqual(self.client.post(reverse("authkits:logout")).status_code, 403)
        self.assertEqual(self.post("logout", {}).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_totp_setup_uses_package_qr_and_confirms_normally(self):
        from cryptography.fernet import Fernet
        from django.contrib.auth import get_user_model

        from authkits.mfa.totp import code_at

        password = "Reference-Totp-Password-746!"
        user = get_user_model().objects.create_user(
            username="totp-example",
            email="totp@example.com",
            password=password,
        )
        configuration = deepcopy(settings.AUTHKITS)
        configuration["ACCOUNTS"] = {
            **configuration["ACCOUNTS"],
            "REQUIRE_EMAIL_VERIFICATION": False,
        }
        configuration["MFA"] = {
            **configuration["MFA"],
            "TOTP_ENABLED": True,
            "ENCRYPTION_KEYS": [Fernet.generate_key().decode()],
        }

        with self.settings(AUTHKITS=configuration):
            self.client = Client(enforce_csrf_checks=True)
            self.client.get(reverse("authkits:signup"))
            self.assertEqual(
                self.post(
                    "login",
                    {"identifier": user.username, "password": password},
                ).status_code,
                302,
            )
            result = self.post(
                "mfa_management",
                {"action": "mfa.setup.totp", "password": password},
            )
            self.assertEqual(result.status_code, 200)
            setup = result.context["setup"]
            self.assertEqual(result.context["totp_uri"], setup.uri)
            self.assertContains(result, 'class="ak-totp-qr"')
            self.assertContains(result, setup.secret)
            fields = Inputs(result.content.decode()).values
            with patch("authkits.mfa.totp.time.time", return_value=3000):
                confirmed = self.post(
                    "mfa_confirm",
                    {**fields, "code": code_at(setup.secret, 100)},
                )

        self.assertContains(confirmed, "MFA enabled")
        self.assertNotContains(confirmed, 'class="ak-totp-qr"')



@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountLifecycleIntegration(TestCase):
    """One customer journey through the wheel's lifecycle routes, no service mocks."""

    def post(self, name, data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                reverse("authkits:" + name),
                {**data, "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value},
                HTTP_ORIGIN="http://testserver",
            )

    def test_lifecycle_and_management_links(self):
        from django.contrib.auth import get_user_model

        self.client = Client(enforce_csrf_checks=True)
        password = "Reference-LifeCycle-632!"
        new_password = "Reference-LifeCycle-975!"
        self.client.get(reverse("authkits:signup"))
        response = self.post("signup", {
            "username": "lifecycle", "email": "lifecycle@example.com",
            "password": password, "password_confirm": password,
        })
        self.assertEqual(response.status_code, 302)
        fields = dict(line.split(": ", 1) for line in mail.outbox[-1].body.splitlines() if ": " in line)
        self.post("verify_email", {"challenge_id": fields["Challenge ID"],
                                   "secret": fields["Verification code"]})
        self.post("login", {"identifier": "lifecycle", "password": password})
        home = self.client.get("/")
        for name in ("password_change", "account_delete", "security_center",
                     "security_sessions", "mfa_management"):
            with self.subTest(name=name):
                self.assertContains(home, reverse("authkits:" + name))
                self.assertEqual(self.client.get(reverse("authkits:" + name)).status_code, 200)
        if settings.AUTHKITS_SOCIAL_ENABLED:
            from allauth.socialaccount.models import SocialAccount

            providers = self.client.get(reverse("authkits:social_accounts"))
            self.assertEqual(providers.status_code, 200)
            for provider in settings.AUTHKITS["SOCIAL"]["PROVIDERS"]:
                self.assertContains(providers, f'value="{provider}"')
            if "google" in settings.AUTHKITS["SOCIAL"]["PROVIDERS"]:
                SocialAccount.objects.create(
                    user=get_user_model().objects.get(username="lifecycle"),
                    provider="google", uid="reference-fixture-identity",
                )
                if "github" in settings.AUTHKITS["SOCIAL"]["PROVIDERS"]:
                    SocialAccount.objects.create(
                        user=get_user_model().objects.get(username="lifecycle"),
                        provider="github", uid="reference-fixture-second-identity",
                    )
                providers = self.client.get(reverse("authkits:social_accounts"))
                self.assertTrue(providers.context["reauth_accounts"])
                if "github" in settings.AUTHKITS["SOCIAL"]["PROVIDERS"]:
                    self.assertContains(providers, "Verify with Google to disconnect")
                    self.assertContains(providers, "Disconnect Google")
        # Merely opening the deletion page does not delete anything.
        self.assertTrue(get_user_model().objects.filter(username="lifecycle").exists())
        proof = self.post("password_change", {"password": password})
        authorization = Inputs(proof.content.decode()).values["authorization"]
        response = self.post("password_change", {
            "authorization": authorization, "password": new_password,
            "password_confirm": new_password,
        })
        self.assertContains(response, "Password changed")
        self.assertTrue(get_user_model().objects.get(username="lifecycle").check_password(new_password))
        proof = self.post("account_delete", {"password": new_password})
        authorization = Inputs(proof.content.decode()).values["authorization"]
        response = self.post("account_delete", {"authorization": authorization, "confirmation": "DELETE"})
        self.assertContains(response, "Account deleted")
        self.assertFalse(get_user_model().objects.filter(username="lifecycle").exists())
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdminSecurityIntegration(TestCase):
    def test_admin_is_gated_by_authkits_and_requires_staff_mfa(self):
        from django.contrib.auth import get_user_model

        password = "Reference-Admin-Password-842!"
        user = get_user_model().objects.create_user(
            username="admin-example",
            email="admin@example.com",
            password=password,
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(user)

        first = self.client.get("/admin/")
        self.assertEqual(first.status_code, 302)
        self.assertTrue(first.url.startswith(reverse("authkits:admin_access")))

        gate = self.client.get(first.url)
        self.assertContains(gate, "requires multi-factor authentication")
        self.assertContains(gate, reverse("authkits:mfa_management"))
