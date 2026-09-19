from html.parser import HTMLParser

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
