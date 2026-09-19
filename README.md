# Authkits Django Example App

This repository is the public reference and integration sandbox for **Authkits Django**.

It intentionally behaves like a normal customer-owned Django application rather than part of the Authkits package itself.

## What belongs here

- minimal Authkits installation examples
- signup, login, verification, recovery, and MFA examples
- host-project settings and URL configuration
- template and styling overrides
- custom user-model examples
- django-allauth examples
- API/headless examples when those integrations ship
- regression checks for the real wheel-install experience

The paid Authkits package source does **not** live in this repository.

## Local setup

Create and activate a virtual environment, then install a licensed Authkits wheel containing the completed MFA/security flows (package checkpoint 11 or later).

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install /path/to/authkits_django-<version>-py3-none-any.whl
python manage.py migrate
python manage.py runserver
```

Then open `http://localhost:8000/`.

## Safety

Do not commit real credentials, production secrets, databases, license keys, or wheel files to this repository.



## Try account security

1. Create an account. The development console email backend delivers verification
   instructions locally; verify before signing in.
2. Sign in to `/auth/security/`, open MFA settings and confirm your password to
   enroll email codes. Confirm the setup code. Authenticator setup is optional below.
3. Generate recovery codes after password/MFA verification. They appear once;
   store them privately. Sign out and exercise an MFA code or a recovery code.
4. Sign in from a second browser and revoke it on the sessions page. Its next
   authenticated request is rejected by the registry middleware.
5. Enable trusted devices over HTTPS to explicitly trust this browser after password
   and MFA verification. Trust rotates, expires, and can be revoked. Security changes
   still require fresh verification.

These routes and security implementations come from the installed package. This
repository only contains host configuration, navigation and integration tests.
The existing neutral home styling is preserved; packaged pages use their normal
Django templates and grayscale stylesheet.

## Optional TOTP and trusted devices

Install your licensed wheel with its optional extra for encrypted authenticator secrets:

```bash
python -m pip install "/path/to/authkits_django-<version>-py3-none-any.whl[mfa]"
```

Generate a Fernet key with `cryptography.fernet.Fernet.generate_key()` and supply it
through `AUTHKITS_TOTP_KEYS`. Never commit it or reuse Django SECRET_KEY. Multiple
comma-separated keys support the package's rotation procedure (new key first).
Key presence enables TOTP enrollment. Without keys, email MFA works with Django alone.

Set `AUTHKITS_TRUSTED_DEVICES=1` only with correctly configured HTTPS. It defaults
to off for local HTTP development. Hosts must configure TLS, allowed hosts, secure
session/CSRF cookies, production secrets and a real email backend before deployment.
Never use the console email backend in production or capture secret-bearing bodies.

Session tracking is enabled immediately after AuthenticationMiddleware. Untracked
sessions are rejected: sign in through `/auth/login/`. Staff can then access admin
with that registered session. Standalone admin/other login flows need an explicit
completed-policy session-registration hook; admin MFA policy is outside this example.
Do not remove registry middleware while relying on revocation, including signed-cookie
revocation. Enroll before enforcing MFA; already-enforced unenrolled accounts need
trusted provisioning. This app and the package remain pre-alpha.

## Validation

With the wheel installed:

```bash
python manage.py check
python manage.py test config
```

Tests use locmem email, normal password hashing, CSRF checks and public package routes.
Public CI checks Python syntax without downloading the proprietary wheel. Full
integration testing requires a licensed wheel; no private package source, wheel,
credentials or implementation is copied into this repository or public Actions.
