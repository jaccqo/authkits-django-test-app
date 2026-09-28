# Authkits Django Reference App

A complete reference Django application for integrating Authkits Django into a real
project. It installs the licensed Authkits wheel and demonstrates the current browser,
MFA, session, social-auth, API, account-security, and licensing flows without copying
Authkits package internals into your application.

The app provides a small host project with environment loading, Django settings, URLs,
SQLite, console email, and simple grayscale templates so you can see the integration
surface clearly. No frontend build is required.

**Keep your licensed wheel, license key, entitlement token, OAuth credentials, and
other production secrets outside version control.** This repository is an integration
example, not a turnkey production deployment configuration.

## What it demonstrates

| Area | Reference entry point |
| --- | --- |
| Signup, verification, login/logout, password recovery | `/auth/signup/`, `/auth/login/`, `/auth/password/reset/` |
| Email MFA, TOTP, recovery codes, fresh step-up | `/auth/security/mfa/` |
| Security Center and safe recent activity | `/auth/security/` |
| Session inventory and revocation | `/auth/security/sessions/` |
| Password change | `/auth/security/password/` |
| Permanent account deletion | `/auth/security/delete-account/` |
| Optional trusted devices (HTTPS required) | `/auth/security/devices/` |
| Optional GitHub/Google login, connect/disconnect, Google reauthentication | `/auth/login/`, `/auth/security/social/` |
| Optional DRF/session and headless bearer APIs, MFA, lifecycle, inventories, OAuth | `/api/v1/auth/`; [client examples](docs/API_EXAMPLES.md) |
| Explicit activation and offline entitlement verification | [release smoke guide](docs/RELEASE_SMOKES.md) |

The homepage links to these packaged routes and labels optional integrations according
to the current configuration. Authkits templates remain package-owned and overrideable, so you can start with the
default UI and replace individual templates when your application needs custom markup
or styling.

## Base install

Use Python 3.10+ with Django 5.2, or Python 3.12+ for Django 6.0. The requirements
allow both supported Django lines; choose one deliberately for your application.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Download the licensed wheel from your entitled Authkits account and keep it outside
this checkout. Substitute its actual version/path in these commands:

```bash
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl"
```

The public `requirements.txt` intentionally does not install Authkits. Install the
wheel you downloaded from your Authkits account so your application uses the same
packaged artifact you would deploy. Avoid copying package source into your project or
depending on an editable checkout.

## Optional installs

Install extras from the **same downloaded wheel**, not an assumed public package index:

```bash
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[mfa]"
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[api]"
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[social]"
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[api,social]"
```

| Package extra | Current dependency contract |
| --- | --- |
| `authkits-django[mfa]` | Historical compatibility extra; `cryptography>=44` is already a base dependency |
| `authkits-django[api]` | `djangorestframework>=3.18,<4` |
| `authkits-django[social]` | `django-allauth[socialaccount]>=65.19.4,<66` |
| `authkits-django[api,social]` | Both optional boundaries |

Installing an extra does not enable it. Both flags default off. Explicitly enabling
an integration without its dependency fails with an install instruction. Social mode
also requires at least one complete credential pair. No OAuth setup or DRF install is
needed for base account/security flows.

## Local environment and startup

Edit the untracked `.env` using `.env.example`. Environment variables already set in
your shell take precedence. Defaults are **local development only**:

- SQLite, Django development server, and console email.
- Required email verification; session tracking on.
- Email MFA available; TOTP enabled when encryption keys are supplied.
- Global MFA enforcement, trusted devices, API, and social auth off.
- No configured entitlement file until activation has created one.

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Use the same hostname
throughout OAuth and email flows. Optionally set
`AUTHKITS_EMAIL_BASE_URL=http://127.0.0.1:8000` for local email links. Restart after
changing settings and run migrations after enabling social auth.

`DJANGO_CSRF_TRUSTED_ORIGINS` is a comma-separated list of exact origins when needed;
do not add wildcards to solve a mismatched local hostname. No production proxy, CORS,
SMTP, database, or static-file deployment configuration is implied by this host.

## MFA and session setup

Generate a dedicated Fernet encryption key locally:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put it in `AUTHKITS_TOTP_KEYS` in `.env`. Do not reuse `DJANGO_SECRET_KEY`.
Rotation keys are comma-separated, newest first; retain old keys while encrypted
factors still need them. Leave blank for email MFA only. Enroll through
`/auth/security/mfa/`; the package-owned setup page shows a locally generated QR code,
the manual secret fallback, and the authenticator deep link. Save one-time recovery
codes privately, then test login and sensitive management with the enrolled factor.
No host migration, QR service, Pillow install, or template configuration is required.

Keep `AUTHKITS_MFA_ENFORCED=0` while enrolling initial accounts. Enabling global
MFA without usable enrolled factors can block login; do not disable checks to work
around this. `AUTHKITS_MFA_ALLOWED_METHODS` defaults to `totp,email`.

Session tracking uses the package's middleware after Django authentication middleware.
`AUTHKITS_TRUSTED_DEVICES=1` is for a correctly configured HTTPS host only; the secure
`__Host-` cookie does not work over ordinary HTTP. Trusted-device proof does not
replace fresh MFA for sensitive operations. Keep it off for the default local setup.

## API setup

Install `[api]`, then set:

```dotenv
AUTHKITS_API_ENABLED=1
AUTHKITS_API_CREDENTIAL_TTL=604800
AUTHKITS_API_CREDENTIAL_MAX_ACTIVE=10
```

Run `migrate` and `check`, then restart. The host conditionally mounts exactly:

```python
path("api/v1/auth/", include("authkits.api.urls"))
```

Disabled means unmounted: base startup does not import DRF. The package validates
supported dependencies/configuration; the host does not replace its API classes or
implement auth services. See [API examples](docs/API_EXAMPLES.md) for all v1 flows,
including CSRF bootstrap, session login, headless MFA, credentials, step-up, account
lifecycle, security/session management, and headless social OAuth.

## Social auth setup

Install `[social]` (or `[api,social]`), and create your own local OAuth applications
in the GitHub developer settings and Google Cloud OAuth configuration. Use a Web
application for Google, configure its consent screen and add test users if the app
is in testing mode. Register these exact local callbacks:

| Provider | Homepage / origin | Callback / authorized redirect URI |
| --- | --- | --- |
| GitHub | `http://127.0.0.1:8000` | `http://127.0.0.1:8000/accounts/github/login/callback/` |
| Google | `http://127.0.0.1:8000` | `http://127.0.0.1:8000/accounts/google/login/callback/` |

If you choose `localhost`, register that exact hostname and use it consistently in
browser URLs, allowed hosts, and email base URL. Production uses its own HTTPS
callbacks and credentials.

Set one or both **complete** credential pairs in the untracked environment:

```dotenv
AUTHKITS_SOCIAL_ENABLED=1
AUTHKITS_GITHUB_CLIENT_ID=
AUTHKITS_GITHUB_CLIENT_SECRET=
AUTHKITS_GOOGLE_CLIENT_ID=
AUTHKITS_GOOGLE_CLIENT_SECRET=
```

Fill the fields for each provider you want; leave the other pair blank. Then run
`python manage.py migrate`, `python manage.py check`, and restart. `/auth/login/`
discovers configured providers and renders CSRF-protected POST buttons.

The host configures Authkits-managed credentials, the Authkits social adapter,
provider apps, the allauth backend/middleware and `/accounts/` OAuth routes.
Do **not** add database `SocialApp` rows or `SOCIALACCOUNT_PROVIDERS` as a second
credential source. Credentials stay in environment-driven settings.

Authkits owns verified-email policy and the MFA/session/audit handoff. Silent local
account linking by matching email is disabled. Sign in to the existing account and
use `/auth/security/social/` to connect a provider deliberately.

This host sets allauth's `SOCIALACCOUNT_ONLY=True` to disable its independent local
password/reset/email flows; Authkits still supports local password authentication.
Legacy allauth login/logout/connections entry points are routed to Authkits.
The allauth safety check in this mode keeps the last connected social provider;
connect a second provider before demonstrating disconnect. Do not remove that guard
or enable alternate account flows just to bypass a disconnect refusal.

Connection changes use fresh password proof or a connected provider with supported
native reauthentication, followed by Authkits MFA when required. Google supplies
that native proof; use the package's **Verify with Google** action in provider
management. GitHub does not support equivalent forced fresh proof in this package.
OAuth is never treated as recent password assurance. Social-only accounts need a
usable local password (set through Authkits recovery) for password-primary lifecycle
operations such as account deletion. Headless social additionally requires the API
flag and uses the same provider configuration.

## End-to-end verification flow

Use disposable local accounts. Verification/reset/email-MFA codes appear in the
local console; never use console email or publish its output in production.

1. Sign up, verify email, sign in by username and email, then sign out.
2. Request a password reset; verify the code and choose a new password.
3. Enroll email MFA; optionally TOTP. Save recovery codes and complete MFA login.
4. Open Security Center, then exercise a management action requiring fresh proof.
5. Sign in in two browsers, inspect sessions, revoke the other session, and confirm
   that browser is rejected on its next request.
6. Change password through `/auth/security/password/`; confirm other access is
   revoked. Delete a disposable account only after final `DELETE` confirmation.
7. With social enabled, test both provider callbacks, deliberate connect/disconnect,
   Google reauthentication and OAuth-to-MFA handoff. See the release guide's exact
   manual provider sequence.
8. With API enabled, follow the client examples for session and cookie-free bearer
   login, MFA, rotation/revocation, step-up, inventories and lifecycle changes.
9. Exercise trusted devices separately over HTTPS; inspect, use, rotate and revoke.
10. Verify activation, offline entitlement use, downloaded-wheel installation, and
    outage behavior using the [deployment verification guide](docs/RELEASE_SMOKES.md).

Abuse controls also apply to successful security operations. Use separate test
accounts/flows and respect retry windows if repeated manual actions exhaust budgets.
Do not weaken package checks to make a smoke pass.

## Licensed activation

Keep `AUTHKITS_ENTITLEMENT_FILE` blank for the initial development boot. Configure a
real license key only in the untracked environment, then run:

```bash
python manage.py authkits_activate --output .authkits/entitlement.jws
```

Only after successful activation, set:

```dotenv
AUTHKITS_ENTITLEMENT_FILE=.authkits/entitlement.jws
```

Restart and run `python manage.py check`. A configured missing/invalid file correctly
fails with `authkits.E006`; do not silence it. The package verifies the JWS locally
before atomic persistence. `.authkits/` is ignored. A valid local entitlement is
used without normal authentication depending on Authkits.com.

For a production deployment, also verify downloaded-wheel integrity, local entitlement
verification, outage behavior, and any enabled OAuth flows using
[the deployment verification guide](docs/RELEASE_SMOKES.md).

## Validation and CI

The repository's public CI does not require access to your licensed wheel:

```bash
python -m unittest discover -s host_tests -v
python -m compileall -q config host_tests scripts manage.py
```

It checks base defaults, opt-in flags, missing-extra failures, credential validation,
secret-safe errors, and host configuration without importing Authkits.

With your installed wheel and desired `.env` profile:

```bash
python manage.py check
python manage.py test config -v 2
```

The suite uses real package routes, normal password hashing and enforced CSRF. API
tests explicitly skip when disabled; combined OAuth launch tests require both flags.
Provider credentials in automated tests are inert fixtures: no real callback is
claimed. These host tests verify your integration surface. Authkits itself provides the
package-level security and provider-protocol behavior exercised through these routes.

Run customer-style clean installs outside any source checkout:

```bash
python scripts/smoke_wheel.py "/absolute/path/authkits_django-<version>-py3-none-any.whl"
# Or select a lane / supported Django line:
python scripts/smoke_wheel.py "/absolute/path/authkits_django-<version>-py3-none-any.whl" --profile api-social --django 5.2
```

The default runs fresh base, `[mfa]`, `[api]`, `[social]`, and `[api,social]` virtual
environments. It copies only host files, installs the supplied wheel, verifies its
installed location, migrates, checks, and tests. Base/MFA lanes assert allauth and DRF
are absent. Local secrets/entitlements are not copied; this runner **does not**
perform real activation or live OAuth. Use it locally or in CI that can access your licensed artifact. Do not publish the
wheel as a public build artifact or expose it in logs.

## Production boundaries

A real deployment must supply production secrets, HTTPS/cookie policy, trusted proxy
configuration, email delivery, database/backups, static hosting, application
permissions, telemetry redaction and retention/maintenance. Django admin remains a
host-owned login path; this example does not claim it is protected by Authkits MFA.
Do not expose admin or other alternate authentication without reviewing their policy.
Authkits does not make these deployment/security decisions for the host.
