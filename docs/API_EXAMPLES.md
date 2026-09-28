# Using the Authkits API

This guide shows how to call the Authkits Django API from your application.

Install your licensed wheel with `[api]`, set `AUTHKITS_API_ENABLED=1`, migrate,
and restart. If you also need social OAuth, install `[social]` and complete the
OAuth setup in the main README. Authkits mounts its API under `/api/v1/auth/`;
your project only needs to include the package routes as shown by this reference app.

The examples below use same-origin JavaScript and do not require a frontend build.
Adapt them to your own client layer. Values such as passwords, email codes, transaction
IDs, and resource IDs come from the user or from a previous Authkits response. Keep
secrets in memory for the active flow; never log bearer or transaction tokens, place
them in URLs or localStorage, or capture sensitive request/response bodies in analytics.
Use HTTPS in production and a secure credential store for native clients. CORS and
cross-origin deployment policy remain application-level decisions.

## Shared transport

```js
const prefix = "/api/v1/auth/";

async function request(path, {body, token, cookies = false, csrf} = {}) {
  const headers = {Accept: "application/json"};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  if (csrf) headers["X-CSRFToken"] = csrf;
  const response = await fetch(prefix + path, {
    method: body === undefined ? "GET" : "POST",
    credentials: cookies ? "same-origin" : "omit",
    headers,
    ...(body === undefined ? {} : {body: JSON.stringify(body)}),
  });
  const result = await response.json();
  if (!response.ok || !result.ok) {
    throw new Error(result.error?.code || "request_failed");
  }
  return result.data;
}

async function sessionPost(path, body) {
  // Refresh on each mutation: login rotates the CSRF cookie.
  const bootstrap = await request("csrf/", {cookies: true});
  return request(path, {body, cookies: true, csrf: bootstrap.csrf_token});
}

const bearerGet = (path, token) => request(path, {token});
const bearerPost = (path, token, body = {}) => request(path, {token, body});
const headlessPost = (path, body) => request(path, {body});
```

Success uses `{ok: true, data: ...}`; failures use `{ok: false, error: {code, message,
details?}}`. Branch on `state` and stable error codes; HTTP 202 may mean a pending
flow, not completed authentication. Do not automatically retry mutations or consumed
proofs. Enrollment-required and verification-required responses need user action.

## Browser-session signup, login, verification, recovery, logout

```js
async function signup(username, email, password, passwordConfirm) {
  return sessionPost("signup/", {
    fields: {username, email}, password, password_confirm: passwordConfirm,
  });
}
const requestVerification = email => sessionPost("email-verification/request/", {email});
const verifyEmail = (challengeId, code) => sessionPost("email-verification/complete/", {
  challenge_id: challengeId, secret: code,
});
const login = (identifier, password) => sessionPost("login/", {identifier, password});
const logout = () => sessionPost("logout/", {});
const requestReset = email => sessionPost("password-reset/request/", {email});
const verifyReset = (challengeId, code) => sessionPost("password-reset/verify/", {
  challenge_id: challengeId, secret: code,
});
const completeReset = (reset, password, passwordConfirm) => sessionPost("password-reset/complete/", {
  token: reset.token, password, password_confirm: passwordConfirm,
});
```

Read verification/reset challenge IDs and codes from the local console email.
Signup normally returns `verification_required` in this host. Request endpoints use
generic responses. Pass the result of `verifyReset` into `completeReset` before its
short-lived authorization expires.

Session `login/` returns `authenticated` or `mfa_required`. For the latter, continue
in the **same browser session** at `/auth/login/mfa/`; do not pass that session flow
to the headless completion endpoint. Choose the next section when the client needs
fully headless MFA. `logout/` ends a browser session; bearer logout is self-revocation.

## Bearer issue, current, rotate, revoke

```js
const issueCredential = () => sessionPost("credentials/issue/", {label: "web client"});
const currentCredential = token => bearerGet("credentials/current/", token);
const rotateCredential = token => bearerPost("credentials/rotate/", token);
const revokeCredential = token => bearerPost("credentials/revoke/", token);
```

Issue only after completed session login and recent Authkits assurance. OAuth alone
is not recent password proof. Issue/rotate returns `data.credential.token` once;
keep the new token and discard the old token after rotation. Current/inventory never
reveal it. Omitting `scopes` uses the package's default management scope set:
`credential.read`, `credential.rotate`, `credential.revoke`, `security.read`, and
`security.step_up`. Request a subset if appropriate; rotation cannot add scopes.

## Fully headless password login and MFA

```js
const headlessLogin = (identifier, password) => headlessPost("headless/login/", {
  identifier, password, label: "headless client",
});
const sendLoginEmail = transaction => headlessPost("headless/mfa/email/send/", {transaction});
const finishLogin = (transaction, method, code) => headlessPost("headless/mfa/complete/", {
  transaction, method, code, label: "headless reference",
});
```

Without required MFA, login returns `state=authenticated` and `credential.token`.
Otherwise retain `transaction` from `state=mfa_required` and inspect `methods` and
`enrollment_required`. For `email`, call `sendLoginEmail`, then supply the delivered
code to `finishLogin`. For `totp` or `recovery`, go directly to `finishLogin`.
Completion returns the bearer; no authenticated Django cookie session is created.
Enroll factors through `/auth/security/mfa/` first. An enforced but unenrolled user
cannot mint a credential. If requesting custom scopes, supply the intended subset
on the headless issuance/completion calls; do not assume default scopes are minimal.

## Bearer-bound step-up

```js
async function beginStepUp(token, password, action, target = "") {
  const pending = await bearerPost("step-up/begin/", token, {
    password, action, target, assurance: "policy",
  });
  return {pending, context: {
    transaction: pending.transaction, action, target, assurance: "policy",
  }};
}
const sendStepUpEmail = (token, step) => bearerPost("step-up/email/send/", token, step.context);
const finishStepUp = (token, step, factor = {}) => bearerPost("step-up/complete/", token, {
  ...step.context, ...factor,
});
```

Keep the same bearer and exact action/target/assurance throughout. If
`pending.mfa_required` is false, call `finishStepUp` without `factor`. Otherwise:

- Email: `sent = await sendStepUpEmail(token, step)`, then pass
  `{method: "email", code, email_challenge_id: sent.email_challenge_id}`.
- Authenticator/recovery: pass `{method: "totp", code}` or `{method: "recovery", code}`.
- If enrollment is required, stop and enroll; do not downgrade assurance.

The completion result contains `authorization`, a single-use grant, not a new login
token. Use it immediately for the exact sensitive operation below. A grant is tied
to the bearer that obtained it; rotating that bearer first invalidates the context.

## Security inventories, revocation, and account lifecycle

```js
const securityEvents = token => bearerGet("security/events/?limit=20", token);
const credentialInventory = token => bearerGet("security/credentials/", token);
const sessionInventory = token => bearerGet("security/sessions/", token);
const revokeOtherCredential = (token, grant, id) => bearerPost("security/credentials/revoke/", token, {
  authorization: grant.authorization, credential_id: id,
});
const revokeOtherCredentials = (token, grant) => bearerPost("security/credentials/revoke-others/", token, {
  authorization: grant.authorization,
});
const revokeSession = (token, grant, id) => bearerPost("security/sessions/revoke/", token, {
  authorization: grant.authorization, session_id: id,
});
const revokeAllSessions = (token, grant) => bearerPost("security/sessions/revoke-all/", token, {
  authorization: grant.authorization,
});
const changePassword = (token, grant, password, passwordConfirm) => bearerPost("account/password/change/", token, {
  authorization: grant.authorization, password, password_confirm: passwordConfirm,
});
const deleteAccount = (token, grant, confirmation) => bearerPost("account/delete/", token, {
  authorization: grant.authorization, confirmation,
});
```

Mint a **new** grant for each mutation with this exact context:

| Operation | Step-up action | Target | Mutation input beyond authorization |
| --- | --- | --- | --- |
| Revoke another credential | `credential.revoke_other` | Inventory credential ID | `credential_id` with the same ID |
| Revoke other credentials | `credential.revoke_others` | `""` | None |
| Revoke one browser session | `session.revoke` | Inventory session ID | `session_id` with the same ID |
| Revoke all browser sessions | `session.revoke_all` | `""` | None |
| Change password | `account.password.change` | `""` | New `password`, `password_confirm` |
| Delete account permanently | `account.delete` | `""` | User-entered `confirmation: "DELETE"` |

Read inventories before selecting IDs. `security.read` is required for events and
sessions; `credential.read` for credential inventory. Remote credential mutations
require `credential.revoke` plus `security.step_up`; session mutations require
`security.step_up` (reading their inventory additionally requires `security.read`). The default scopes cover these examples.

Password change revokes existing credentials, including the calling bearer; sign in
again. Account deletion is permanent and must have an explicit user confirmation.
Use a disposable account for the example. A bearer is not a browser session:
revoking all browser sessions leaves the bearer usable. When session tracking is
disabled, session inventory reports `enabled=false` with an empty list.

## Headless social OAuth (API + social)

```js
const beginSocial = provider => headlessPost("headless/social/begin/", {
  provider, label: "social client",
});
const exchangeSocial = transaction => headlessPost("headless/social/exchange/", {transaction});
const finishSocialMFA = (socialTransaction, mfaTransaction, method, code) =>
  headlessPost("headless/social/mfa/complete/", {
    transaction: socialTransaction, mfa_transaction: mfaTransaction, method, code,
  });
```

1. Call `beginSocial("github")` or `beginSocial("google")`.
2. Keep `transaction` in the client. Open the returned `authorization_url` in a
   browser and submit the package's CSRF-protected provider button. Do not append the
   exchange transaction to the URL. The launch URL contains its own separate secret;
   redact it from access logs and do not share it.
3. Finish provider login/callback, then return to the client. Call
   `exchangeSocial(transaction)`. `pending` means the callback has not completed;
   retry deliberately with a delay, not a tight polling loop.
4. `authenticated` returns the bearer. `mfa_required` instead returns
   `mfa_transaction`. For email, call `sendLoginEmail(mfa_transaction)`.
5. Call `finishSocialMFA` with **both** transactions and the selected factor. Retain
   the resulting bearer in the client. Scopes/label were fixed at social begin.

The OAuth browser never receives the final bearer or the client exchange secret.
Its temporary authentication is cleared by the package. Trusted-device cookies do
not bypass headless MFA. A normal Google login is not provider-native step-up;
connected-provider management and Google reauthentication use `/auth/security/social/`.
There is no social connection-management API in this v1 surface.
