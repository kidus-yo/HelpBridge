# Platform integration and tenant context

HelpBridge attaches to an external **Platform** (LMS, job portal, career portal, inclusive recruitment, or other) used by an **Institution**. A **PlatformIntegration** is the authorized relationship.

## Who mints tokens

The **host platform server** stores the raw integration API key in its secret
store and uses it to mint a short-lived context token for each learner page
load. The raw key is shown once when the integration is created; it must never
be sent to the browser.

The **browser widget** receives only the short-lived token. A script tag is not
authentication. The token currently expires after 15 minutes by default; the
host should mint a fresh token when rendering/reloading the learner page.

```http
POST /api/v1/platform-context/tokens/
Authorization: Api-Key hb_...
Content-Type: application/json

{
  "user_ref": "opaque-learner-ref",
  "context_type": "course",
  "context_id": "<matching HelpBridge course UUID>",
  "preferred_language": "am",
  "scopes": ["courses:read", "knowledge:read", "support:write"]
}
```

Map the Savanna course identifier to the corresponding **HelpBridge** course
UUID before issuing the token. `user_ref` must be pseudonymous. Do not send
names, emails, disability status, or government IDs.

The integration must permit every requested scope. The token endpoint is
`POST /api/v1/platform-context/tokens/` and returns a bearer token. Keep the
integration key on the server; do not put it in JavaScript, HTML, or a browser
request.

## Embed the widget in Savanna

After minting the token on the Savanna server, render the script tag on the
course page:

```html
<script
  src="https://HELPBRIDGE_HOST/static/widget/bridge.js"
  data-api="https://HELPBRIDGE_HOST"
  data-context-token="SHORT_LIVED_TOKEN"
  data-lang="en"
  defer>
</script>
```

Set `CORS_ALLOWED_ORIGINS` on HelpBridge to the exact Savanna origin, including
scheme and port where applicable. For example:
`CORS_ALLOWED_ORIGINS=https://savanna.example.org`. Use HTTPS for both systems.
The widget does not refresh an expired token in-place yet; reload the course
page to obtain a new one.

## See a local demo

From the repository root on Windows:

1. Copy `.env.example` to `.env`, set `CORS_ALLOWED_ORIGINS=http://localhost:8001`,
   then run `python backend\manage.py migrate`.
2. Run `python backend\manage.py seed_local_savanna_demo`. It creates a local
   sample tenant, a published bilingual course and source material, then prints
   a temporary widget token. It is disabled when `DEBUG=False` or in production.
3. Keep the token in the terminal. In a second terminal run
   `python -m http.server 8001 --directory frontend`.
4. Open `http://localhost:8001/widget/demo.html`, paste the short-lived token,
   select a language and load the widget. Ask **“What helps learners practice
   new ideas?”** to see a grounded answer and citation.

This local seed is a Savanna-style demonstration only; it does not connect to
the live ALX Savanna service or import its courses.

## Using the token

```http
GET /api/v1/platform-context/
Authorization: Bearer <token>
```

Validated fields:

- `platform_id`, `platform_type`
- `institution_id`
- `user_ref`
- `context_type` (`course`, `job`, `application`, `general`, `support`)
- `context_id`
- `scopes`
- `preferred_language`
- `token_issuer`, `token_audience` (`helpbridge`), `token_expiry`

Validation covers signature, issuer, audience, expiry, and permitted scopes. Client-supplied institution IDs cannot override the token.

## Python interface for other apps

```python
from platforms.services.context import get_platform_context

context = get_platform_context(request)
if context is None:
    ...
institution_id = context.institution_id
```

Do not ask the LLM to decide tenant identity.

## Staff APIs

Creating platforms, institutions, and integrations requires a Django staff session. The raw API key is returned **once** on `POST /api/v1/platform-integrations/`.
