# Digital Bridge Assistant — Embeddable Widget (`bridge.js`)

**Role:** Developer 2 — Koket (Conversation Platform & Accessibility Engineer)

## Overview
`bridge.js` is an accessible, lightweight, embeddable script-tag plugin that integrates directly into existing LMS pages (e.g. ALX Savanna) without taking over host page styles or navigation.

## Features
- **Script-tag integration** with a short-lived host-minted context token.
- **Accessibility-oriented implementation**:
  - Dialog semantics and an ARIA live region are present.
  - Keyboard focus handling, visible outlines, and Escape-to-close are implemented but not manually tested.
  - Responsive styling is present; 200% zoom reflow has not been verified.
- **Multilingual Support**:
  - Instant toggle between English (`en`) and Amharic (`am`).
  - Clear Ethiopic script typography and layout.
- **Accessibility Modes**:
  - **Simple Mode**: Reduces visual distractions and clutter for neurodivergent or overwhelmed learners.
  - **High Contrast**: Stronger foreground/background contrast.
  - **Text Scaling**: Normal, Large, and Extra Large font sizes.
- **Evidence-Grounded Citations**:
  - Displays source PDF/DOCX document titles and page numbers.
- **Live Human Escalation**:
  - One-click "Talk to a human" button with explicit learner consent for chat sharing.
- **Speech Alternative**:
  - Speech recognition with immediate graceful fallback if unsupported.

These are implementation features, not a verified WCAG conformance claim. Manual
keyboard, screen-reader, zoom/reflow, and contrast testing is still required.

## Installation

The host platform server must mint and periodically refresh a short-lived
platform context token. Never expose an integration API key or signing secret
in the page. Configure the LMS page's exact origin in `CORS_ALLOWED_ORIGINS`;
the API does not allow cross-origin requests by default.

```html
<!-- Inside the LMS page <head> or before </body> -->
<script
  src="http://localhost:8000/static/widget/bridge.js"
  data-api="http://localhost:8000"
  data-context-token="<SHORT_LIVED_TOKEN_FROM_HOST_SERVER>"
  data-lang="en">
</script>
```

Use HTTPS in production for both the host page and HelpBridge API. A reverse
proxy or static host may serve collected assets in production; run
`python backend/manage.py collectstatic` as part of deployment.

For a complete local setup, including the seeded sample course and short-lived
token command, follow [the platform integration walkthrough](../../docs/platform-integration.md).

