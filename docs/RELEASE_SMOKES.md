# Customer release smoke runbook

This reference host supports the operator checks in the private package's
`docs/V1_READINESS.md`. Use the readiness document from the **exact candidate
revision** as the authority. These are operator procedures, not evidence that live
production work has completed. Do not publish licenses, tokens, OAuth secrets, private
keys, console emails or customer information in this public repo.

Record sanitized evidence privately: candidate package revision/version, wheel
SHA-256, host commit, Python/Django versions, profile, date, operator and pass/fail.
Do not reuse a version number for different wheel bytes.

## 1. Release and signing prerequisites (operator, outside this repo)

Before claiming customer readiness:

1. Choose the intended RC/stable PEP 440 version. Update package metadata, status
   classifier, changelog and README in the package repo; rebuild the exact candidate.
2. Pass the package release matrix, database gates and artifact validators. Run its
   `python scripts/check_release.py /path/to/candidate.whl` (also `--stable` when
   making a stable release) and clean-wheel checks on that artifact.
3. Coordinate the signing rollout. The inspected package includes public key ID
   `entitlement-2026-09`, fingerprint
   `4b894a7c2c7ee771d89ff1dd659297d112971bb51968fc82ad39eb697ae43cdb`.
   Reconfirm the intended key in the exact candidate. Keep private key material
   only in the Authkits.com production secret manager. Install/release the wheel
   carrying that public key **before** enabling matching customer signing.
4. Verify Authkits.com's production settings:
   `AUTHKITS_ENTITLEMENT_SIGNING_PRIVATE_KEY`, `AUTHKITS_ENTITLEMENT_SIGNING_KEY_ID`,
   and independent `AUTHKITS_ACTIVATION_FINGERPRINT_SECRET`. Retain older public keys
   during rotations. No signing-key generation or production secret changes occur here.
5. Finalize the commercial terms and display them in the purchase/download flow.
   Confirm package and site wording agree with the actual terms.

These gates cannot be replaced by synthetic keys, local test tokens or this host's CI.

## 2. Hosted download and fresh customer install

1. Upload the exact validated candidate through Authkits admin Downloads and associate
   it with product `django-authentication`.
2. Confirm public release metadata discovers the intended version (the package's
   explicit `python manage.py authkits_check` is available for update discovery).
3. Download using a real entitled customer/test account. Verify a non-entitled account
   and an account entitled only to a different product cannot obtain the wheel.
4. Compare SHA-256 of the downloaded bytes against the validated candidate. For example:

   ```bash
   python -c "import hashlib,pathlib; p=pathlib.Path('/absolute/path/downloaded.whl'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
   ```

5. Run the fresh installer against those **downloaded bytes**, outside package source:

   ```bash
   python scripts/smoke_wheel.py "/absolute/path/authkits_django-<version>-py3-none-any.whl"
   ```

   All five profiles must pass. Use `--django 5.2` and, on Python 3.12+, `--django 6.0`
   when validating both supported lines. This is host integration coverage, not a
   substitute for the private package's full supported-Python/database matrix.
6. Create a persistent fresh clone/venv using README setup, install the same downloaded
   wheel, migrate and check. Use this host for the real license and browser smokes below.

A wheel built privately from `main` can validate integration but does not prove
hosted download entitlements or a finalized release artifact.

## 3. Real license activation and local verification

Use an actual entitled disposable Authkits account/license for `django-authentication`.
Keep the key in this host's untracked `.env`/secret manager; do not put it in a shell
command, ticket, screenshot or CI log. Start with no configured entitlement source.

```dotenv
AUTHKITS_LICENSE_KEY=<set privately>
AUTHKITS_ENTITLEMENT_FILE=
AUTHKITS_ACTIVATION_URL=https://authkits.com/api/v1/licenses/activate
```

From the host root:

```bash
python manage.py authkits_activate --output .authkits/entitlement.jws
```

Success means the package verified the signed response before persisting it. Set
`AUTHKITS_ENTITLEMENT_FILE=.authkits/entitlement.jws` in `.env`, then restart the host.
Verify in a fresh process without printing the token:

```bash
python manage.py check
python manage.py shell -c "from authkits.licensing.runtime import get_verified_entitlement; get_verified_entitlement(required=True); print('Local entitlement verification passed')"
python manage.py authkits_check --security
```

On POSIX, inspect permissions without reading the contents:

```bash
python -c "from pathlib import Path; p=Path('.authkits/entitlement.jws'); assert p.is_file(); assert p.stat().st_mode & 0o777 == 0o600; print('Entitlement file mode is 0600')"
```

Check the parent directory too (newly created activation directories are 0700).
On Windows, inspect and restrict the file/directory ACL to the intended operator or
service identity; POSIX mode bits do not demonstrate Windows access control.
Review logs/audit using a secret-safe process and verify that no raw license key or
JWS was recorded. Never paste matching secret-bearing log lines into evidence.
`authkits_check --security` may flag this development host; resolve deployment-specific
findings before production. Its output is not a deployment certification.

## 4. Authkits.com outage smoke

After successful activation, leave the verified entitlement and Django/TOTP keys intact.

1. In an isolated local test host, use a reversible firewall/DNS/network policy to deny
   outbound access to `authkits.com`. Keep localhost, your test email delivery and OAuth
   provider access available if exercising those features. Do not change the real
   production site's networking. Record the exact local block and how to remove it.
2. Verify the block from the host without sending a license or token. A bounded
   connection to `https://authkits.com` must fail. Do not merely change the activation
   URL; that would not prove runtime independence from the actual service.
3. Restart Django and run the local entitlement verification and `manage.py check`
   commands above. They must succeed offline.
4. On fresh disposable accounts, repeat signup/email verification, password login,
   MFA enrollment/login, password recovery, recovery-code login and session inventory/
   revocation. Check the rejected browser after revocation. Normal auth must succeed
   under the block. The console email backend keeps local delivery testable.
5. Run the explicit `authkits_activate` and `authkits_check` update-discovery commands
   under the block. Only these network-dependent operator actions should report a
   controlled network failure/unavailability. A failed activation must leave the
   previously verified entitlement untouched; verify it locally again.
6. Remove the local block, confirm connectivity is restored, and record sanitized
   pass/fail evidence. Keep all readiness boxes open until the actual test is done.

The clean-wheel runner deliberately excludes real entitlement state, so it cannot
substitute for this activated-host outage test.

## 5. Live OAuth callbacks and Authkits security handoff

Automated host tests validate configuration, discovery, protected management pages,
Google proof controls, and the headless launch/pending exchange without contacting
providers. To finish real provider validation:

1. Configure both real local OAuth clients using README callbacks and run migrations/checks.
2. Create and verify a disposable password account. From `/auth/security/social/`,
   connect GitHub with fresh password proof and finish the real provider callback.
3. Connect Google deliberately from the same management page. Confirm both connections
   appear. Sign out and test GitHub and Google login separately.
4. Enroll email/TOTP MFA and repeat OAuth login. Confirm Authkits requires the factor
   before completed access, records the session, and shows safe security activity.
5. From provider management choose **Verify with Google** to disconnect the other
   provider. Complete the provider-native prompt as the exact connected identity,
   then complete Authkits MFA if required. Confirm the connection change succeeds.
6. Reconnect as needed and test password + MFA disconnect. This host's social-only
   allauth setting preserves the last connected social provider; that refusal is
   expected even though Authkits also supports password login.
7. Repeat the API examples' headless social begin → browser callback → exchange flow.
   With MFA enabled use the returned `mfa_transaction` and final social-MFA endpoint.
   Confirm the bearer works and the temporary browser login is not retained.
8. Test a new social-only account too. Provider-verified email must satisfy Authkits'
   verification policy; otherwise verify email first. Normal GitHub login is not
   forced fresh proof. Password-primary operations require a usable local password.

## Completion record

Keep a private record with explicit outcomes for: candidate validation/version,
production key/secret rollout, real activation, local signature verification and file
permissions, outage behavior, entitled/wrong-product downloads, downloaded-wheel
profiles, live provider callbacks/MFA, and commercial terms. Leave incomplete items
marked **pending**, with their owner and failed/missing evidence. This public repo
contains no assertion that those production-only gates have passed.
