# Authkits Django deployment verification

Use this guide after you download an Authkits Django wheel and before you rely on it
in a production deployment. The goal is to verify that the exact artifact you received
installs cleanly, activates correctly, continues to verify its entitlement locally,
and behaves as expected with the integrations you enable.

Keep license keys, entitlement tokens, OAuth secrets, private signing material, email
codes, and customer data out of screenshots, tickets, CI logs, and public artifacts.

## 1. Verify the downloaded wheel

Download the wheel from your entitled Authkits account and keep the original filename,
for example:

```text
authkits_django-<version>-py3-none-any.whl
```

Record its SHA-256 before moving it between systems:

```bash
python -c "import hashlib,pathlib; p=pathlib.Path('/absolute/path/authkits_django-<version>-py3-none-any.whl'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

If your team stores approved build hashes, compare against that record before install.

For a clean integration check, run the reference app's wheel smoke runner outside an
Authkits package source checkout:

```bash
python scripts/smoke_wheel.py "/absolute/path/authkits_django-<version>-py3-none-any.whl"
```

The default run creates fresh environments for the base package plus the `mfa`,
`api`, `social`, and `api,social` installation profiles. You can also select one
profile or supported Django line:

```bash
python scripts/smoke_wheel.py "/absolute/path/authkits_django-<version>-py3-none-any.whl" --profile api-social --django 5.2
```

On Python 3.12+, also verify Django 6.0 if that is the line you plan to deploy.

## 2. Install into your application

Create or activate your application's virtual environment and install the downloaded
wheel directly:

```bash
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl"
```

Install optional boundaries only when you use them:

```bash
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[api]"
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[social]"
python -m pip install "/absolute/path/authkits_django-<version>-py3-none-any.whl[api,social]"
```

Then run:

```bash
python manage.py migrate
python manage.py check
```

If you are using this reference app, also run:

```bash
python manage.py test config -v 2
```

## 3. Activate the license

Put the license key only in your untracked environment or secret manager:

```dotenv
AUTHKITS_LICENSE_KEY=<set privately>
AUTHKITS_ENTITLEMENT_FILE=
AUTHKITS_ACTIVATION_URL=https://authkits.com/api/v1/licenses/activate
```

Activate once and write the signed entitlement locally:

```bash
python manage.py authkits_activate --output .authkits/entitlement.jws
```

After successful activation, configure:

```dotenv
AUTHKITS_ENTITLEMENT_FILE=.authkits/entitlement.jws
```

Restart the application and verify the entitlement in a fresh process:

```bash
python manage.py check
python manage.py shell -c "from authkits.licensing.runtime import get_verified_entitlement; get_verified_entitlement(required=True); print('Local entitlement verification passed')"
python manage.py authkits_check --security
```

The entitlement is verified locally during normal runtime. Do not print or log the
compact JWS itself.

On POSIX systems, restrict the entitlement file and containing directory to the
service identity. On Windows, apply an ACL appropriate for the account running Django.

## 4. Verify offline runtime behavior

After activation, test that normal authentication does not depend on Authkits.com.

In a disposable local environment, temporarily remove network access or block outbound
access to `authkits.com`. Keep the existing entitlement file and your local TOTP
encryption keys unchanged.

While offline, restart Django and run:

```bash
python manage.py check
python manage.py shell -c "from authkits.licensing.runtime import get_verified_entitlement; get_verified_entitlement(required=True); print('Local entitlement verification passed')"
```

Then exercise the flows your application uses, such as:

- signup and email verification
- password login and logout
- password recovery
- email MFA and TOTP MFA
- recovery-code login
- Security Center
- session inventory and revocation
- password change
- account deletion on a disposable account

These normal runtime flows should continue to work with the previously verified local
entitlement. Explicit activation and update-discovery commands are network-dependent
and should fail cleanly while the service is unreachable without damaging the existing
entitlement.

Restore network access when the test is complete.

## 5. Verify TOTP setup

If you enable TOTP, configure a Fernet key in `AUTHKITS_TOTP_KEYS` and open
`/auth/security/mfa/`.

The default Authkits setup page should show:

- a locally generated QR code
- the manual TOTP secret
- the authenticator deep link
- the six-digit confirmation field

Scan the QR code in an authenticator app and confirm setup with the generated code.
If you override the MFA template, use the documented Authkits template context/helper
rather than rebuilding the provisioning URI yourself.

## 6. Verify social authentication

If you enable `[social]`, configure your own GitHub and/or Google OAuth applications
using the callback URLs documented in the README.

Verify each provider you ship:

1. Sign in with the provider.
2. Connect the provider to an existing password account.
3. Confirm deliberate disconnect behavior from `/auth/security/social/`.
4. With MFA enabled, confirm OAuth hands off to Authkits MFA before completed access.
5. For Google, verify the package's fresh-provider reauthentication flow where required.
6. If you also enable the API, test the headless social begin → callback → exchange
   flow from [the API guide](API_EXAMPLES.md).

Use disposable test accounts and keep provider credentials out of source control.

## 7. Verify API and headless flows

If `AUTHKITS_API_ENABLED=1`, walk through the examples in
[API_EXAMPLES.md](API_EXAMPLES.md) for the flows your client uses:

- browser-session signup/login/recovery
- bearer credential issue, rotation, and revocation
- fully headless password + MFA login
- bearer-bound step-up
- security/session inventories
- password change and account deletion
- headless social OAuth

Verify both successful and expected-denial paths. Do not weaken Authkits checks to make
a test pass.

## 8. Production checklist

Before deploying, confirm your application has production-appropriate settings for:

- HTTPS and secure cookies
- `ALLOWED_HOSTS` and CSRF trusted origins
- email delivery
- database and backups
- static-file hosting
- proxy/header trust
- secret management
- logging and analytics redaction
- entitlement-file permissions
- OAuth callback URLs and credentials, if enabled
- trusted-device HTTPS requirements, if enabled
- admin and any alternate authentication entry points

Authkits protects the package routes it owns. Your Django deployment, infrastructure,
admin policy, and any additional authentication surfaces remain your responsibility.

## Recommended record

For repeatable deployments, keep a private deployment record containing the Authkits
version, wheel SHA-256, Python/Django versions, enabled extras, application commit,
activation date, and the pass/fail result of the checks above. Do not include raw
license keys, entitlement tokens, OAuth secrets, or MFA recovery codes.
