# Authkits Django Reference App

This repository is the public customer-style integration sandbox for **Authkits Django**.

It is intentionally a normal Django host application. The private Authkits package
owns authentication and account-security behavior; this repository owns Django
settings, environment loading, email, database, middleware, templates and deployment
choices.

The paid Authkits package source and wheel are never committed here.

## What this app demonstrates

- signup and email verification
- login and logout
- password recovery
- email MFA
- encrypted authenticator/TOTP MFA
- recovery codes
- step-up authentication
- security center
- session inventory and revocation
- trusted-device configuration hooks
- host-owned environment and Django configuration

Social/django-allauth examples will be added when the provider-flow checkpoints ship.
Headless/DRF examples remain a later phase.

## 1. Create the host environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
```

The real `.env` is gitignored.

## 2. Install the Authkits wheel

Build the private package first, then install that wheel into this virtual environment.

Base account/security install:

```powershell
python -m pip install "C:\path\to\authkits-django\dist\authkits_django-0.1.0a1-py3-none-any.whl"
```

For authenticator/TOTP testing, install the wheel with the MFA extra:

```powershell
python -m pip install "C:\path\to\authkits-django\dist\authkits_django-0.1.0a1-py3-none-any.whl[mfa]"
```

The public `requirements.txt` deliberately does **not** install Authkits. A customer
receives the licensed wheel separately.

## 3. Configure `.env`

The checked-in `.env.example` contains every local setting used by this reference
app. Its defaults are safe for local development only.

For TOTP/authenticator testing, generate a Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output into:

```env
AUTHKITS_TOTP_KEYS=YOUR_GENERATED_KEY
```

Do not reuse Django `SECRET_KEY` as the TOTP encryption key.

Leave this disabled during ordinary HTTP development:

```env
AUTHKITS_TRUSTED_DEVICES=0
```

Trusted devices require correctly configured HTTPS and secure cookies.

## 4. Run the app

```powershell
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Authkits routes are mounted under `/auth/`.

## Manual test flow

Use a fresh account and walk through the package as a customer would:

1. Create an account at `/auth/signup/`.
2. Read the console email and complete email verification.
3. Sign in and open `/auth/security/`.
4. Enroll email MFA.
5. Generate recovery codes and verify that a used code cannot replay.
6. If `AUTHKITS_TOTP_KEYS` is configured, enroll an authenticator app.
7. Exercise MFA-gated login.
8. Exercise password-protected/step-up security changes.
9. Sign in from a second browser and revoke that session.
10. Test trusted devices separately over HTTPS.

The console email backend is intentional for local testing so verification, password
reset and email-MFA codes are visible in the terminal. Never use it in production.

## Environment contract

The most useful local controls are:

```env
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
AUTHKITS_REQUIRE_EMAIL_VERIFICATION=1
AUTHKITS_SESSION_TRACKING=1
AUTHKITS_MFA_ENFORCED=0
AUTHKITS_MFA_ALLOWED_METHODS=totp,email
AUTHKITS_TOTP_KEYS=
AUTHKITS_TRUSTED_DEVICES=0
```

`AUTHKITS_TOTP_KEYS` may contain multiple comma-separated Fernet keys during key
rotation, newest first.

## Validation

With the licensed wheel installed:

```powershell
python manage.py check
python manage.py test config
```

The integration suite uses normal password hashing, CSRF enforcement, locmem email
and public Authkits routes. It exercises signup, verification, login, MFA, session
security and logout through the installed package rather than importing private source.

Public GitHub Actions cannot download the proprietary Authkits wheel. Public CI
therefore validates the host dependencies, environment/settings contract and Python
syntax. Full package integration testing happens locally and in the private package CI.

## Production boundaries

This is a development/reference host, not a deployment template.

A production application must supply its own production secrets, HTTPS, secure cookie
settings, email provider, database, static-file deployment, proxy configuration,
monitoring and retention policy. Authkits does not silently own those host concerns.
