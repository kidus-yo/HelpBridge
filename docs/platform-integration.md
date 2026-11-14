# Platform integration and tenant context

HelpBridge attaches to an external **Platform** (LMS, job portal, career portal, inclusive recruitment, or other) used by an **Institution**. A **PlatformIntegration** is the authorized relationship.

## Who mints tokens

The **host platform server** authenticates with a hashed API key and mints a short-lived context token for the learner session.

The **browser widget** receives only that token. A script tag is not authentication.

```http
POST /api/v1/platform-context/tokens/
Authorization: Api-Key hb_...
Content-Type: application/json

{
  "user_ref": "opaque-learner-ref",
  "context_type": "course",
  "context_id": "<host course id or uuid>",
  "preferred_language": "am",
  "scopes": ["courses:read", "knowledge:read"]
}
```

`user_ref` must be pseudonymous. Do not send names, emails, disability status, or government IDs.

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
