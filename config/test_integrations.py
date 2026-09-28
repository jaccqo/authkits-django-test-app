"""Installed-wheel wiring checks; run in separate base/API/social environments."""

from django.conf import settings
from django.test import Client, TestCase
from django.urls import Resolver404, resolve, reverse


class OptionalIntegrationWiring(TestCase):
    def test_api_mount_is_opt_in(self):
        if not settings.AUTHKITS_API_ENABLED:
            with self.assertRaises(Resolver404):
                resolve("/api/v1/auth/csrf/")
            return
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("authkits_api:csrf"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrf_token", response.json()["data"])
        self.assertIn("csrftoken", response.cookies)
        response = client.post(reverse("authkits_api:login"), {}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_social_mount_and_discovery_are_opt_in(self):
        if not settings.AUTHKITS_SOCIAL_ENABLED:
            with self.assertRaises(Resolver404):
                resolve("/accounts/github/login/")
            return
        page = self.client.get(reverse("authkits:login"))
        for provider in settings.AUTHKITS["SOCIAL"]["PROVIDERS"]:
            self.assertContains(page, reverse(f"{provider}_login"))
            self.assertEqual(reverse(f"{provider}_callback"), f"/accounts/{provider}/login/callback/")
        self.assertRedirects(self.client.get("/accounts/3rdparty/"),
                             reverse("authkits:social_accounts"), fetch_redirect_response=False)
        # allauth must not expose a second password reset/change flow.
        for path in ("/accounts/password/reset/", "/accounts/password/change/"):
            with self.assertRaises(Resolver404):
                resolve(path)
        self.assertEqual(self.client.post("/accounts/login/", {}).status_code, 405)


class APIReferenceIntegration(TestCase):
    def setUp(self):
        if not settings.AUTHKITS_API_ENABLED:
            self.skipTest("Enable AUTHKITS_API_ENABLED to exercise the installed API extra")
        self.client = Client(enforce_csrf_checks=True)

    def api(self, name, body=None, *, bearer=None, method="post"):
        headers = {}
        if bearer:
            headers["HTTP_AUTHORIZATION"] = "Bearer " + bearer
        elif "csrftoken" in self.client.cookies:
            headers["HTTP_X_CSRFTOKEN"] = self.client.cookies["csrftoken"].value
        with self.captureOnCommitCallbacks(execute=True):
            return getattr(self.client, method)(
                reverse("authkits_api:" + name), body or {},
                content_type="application/json", **headers,
            )

    def test_documented_api_routes(self):
        routes = {
            "csrf": "csrf/", "signup": "signup/", "login": "login/", "logout": "logout/",
            "verification_request": "email-verification/request/",
            "verification_complete": "email-verification/complete/",
            "password_reset_request": "password-reset/request/",
            "password_reset_verify": "password-reset/verify/",
            "password_reset_complete": "password-reset/complete/",
            "credential_issue": "credentials/issue/", "credential_current": "credentials/current/",
            "credential_rotate": "credentials/rotate/", "credential_revoke": "credentials/revoke/",
            "headless_login": "headless/login/", "headless_mfa_email": "headless/mfa/email/send/",
            "headless_mfa_complete": "headless/mfa/complete/",
            "step_up_begin": "step-up/begin/", "step_up_email": "step-up/email/send/",
            "step_up_complete": "step-up/complete/",
            "account_password_change": "account/password/change/", "account_delete": "account/delete/",
            "security_events": "security/events/", "security_credentials": "security/credentials/",
            "security_credential_revoke": "security/credentials/revoke/",
            "security_credential_revoke_others": "security/credentials/revoke-others/",
            "security_sessions": "security/sessions/",
            "security_session_revoke": "security/sessions/revoke/",
            "security_session_revoke_all": "security/sessions/revoke-all/",
            "headless_social_begin": "headless/social/begin/",
            "headless_social_exchange": "headless/social/exchange/",
            "headless_social_mfa_complete": "headless/social/mfa/complete/",
        }
        documentation = (settings.BASE_DIR / "docs" / "API_EXAMPLES.md").read_text()
        for name, suffix in routes.items():
            with self.subTest(name=name):
                self.assertIn(suffix, documentation)
                self.assertEqual(reverse("authkits_api:" + name), "/api/v1/auth/" + suffix)
                self.assertTrue(resolve("/api/v1/auth/" + suffix).func.__module__.startswith("authkits."))

    def test_customer_session_and_headless_bearer_journey(self):
        from django.core import mail
        from django.test import override_settings

        password = "Reference-API-Password-753!"
        self.api("csrf", method="get")
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            response = self.api("signup", {
                "fields": {"username": "api-example", "email": "api@example.com"},
                "password": password, "password_confirm": password,
            })
            self.assertEqual(response.status_code, 201)
            fields = dict(line.split(": ", 1) for line in mail.outbox[-1].body.splitlines() if ": " in line)
            response = self.api("verification_complete", {
                "challenge_id": fields["Challenge ID"], "secret": fields["Verification code"],
            })
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api("login", {"identifier": "api-example", "password": password}).status_code, 200)
        issued = self.api("credential_issue", {"label": "reference session"})
        self.assertEqual(issued.status_code, 201)
        token = issued.json()["data"]["credential"]["token"]
        for name in ("credential_current", "security_events", "security_credentials", "security_sessions"):
            self.assertEqual(self.api(name, bearer=token, method="get").status_code, 200)
        rotated = self.api("credential_rotate", bearer=token)
        self.assertEqual(rotated.status_code, 201)
        replacement = rotated.json()["data"]["credential"]["token"]
        self.assertEqual(self.api("credential_current", bearer=token, method="get").status_code, 401)
        self.assertEqual(self.api("credential_revoke", bearer=replacement).status_code, 200)
        self.assertEqual(self.api("logout").status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

        # Cookie-free authentication consumes the same wheel, without session login.
        self.client = Client(enforce_csrf_checks=True)
        response = self.api("headless_login", {"identifier": "api-example", "password": password})
        self.assertEqual(response.status_code, 200)
        token = response.json()["data"]["credential"]["token"]
        self.assertNotIn("sessionid", self.client.cookies)
        context = {"action": "account.password.change", "target": "", "assurance": "policy"}
        pending = self.api("step_up_begin", {**context, "password": password}, bearer=token)
        self.assertEqual(pending.status_code, 202)
        grant = self.api("step_up_complete", {
            **context, "transaction": pending.json()["data"]["transaction"],
        }, bearer=token)
        self.assertEqual(grant.status_code, 200)
        response = self.api("account_password_change", {
            "authorization": grant.json()["data"]["authorization"],
            "password": "Reference-API-New-975!", "password_confirm": "Reference-API-New-975!",
        }, bearer=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api("credential_current", bearer=token, method="get").status_code, 401)

    def test_headless_social_launch_wiring(self):
        if not settings.AUTHKITS_SOCIAL_ENABLED:
            self.skipTest("Enable social auth for the combined OAuth handoff")
        provider = next(iter(settings.AUTHKITS["SOCIAL"]["PROVIDERS"]))
        result = self.api("headless_social_begin", {"provider": provider})
        self.assertEqual(result.status_code, 202)
        data = result.json()["data"]
        browser = Client(enforce_csrf_checks=True)
        page = browser.get(data["authorization_url"])
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, reverse(f"{provider}_login"))
        self.assertNotContains(page, data["transaction"])
        self.assertEqual(self.api("headless_social_exchange", {
            "transaction": data["transaction"],
        }).json()["data"]["state"], "pending")
