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
