# Digital Bridge Assistant — Embeddable Widget (`bridge.js`)

**Role:** Developer 2 — Koket (Conversation Platform & Accessibility Engineer)

## Overview
`bridge.js` is an accessible, lightweight, embeddable script-tag plugin that integrates directly into existing LMS pages (e.g. ALX Savanna) without taking over host page styles or navigation.

## Features
- **One-line integration**: `<script src=".../bridge.js" data-api="..." data-course="..."></script>`
- **WCAG 2.2 Level AA Compliant**:
  - Semantic HTML dialog (`role="dialog"`, `aria-modal="true"`).
  - ARIA polite live region (`aria-live="polite"`) announcing new assistant responses to screen readers.
  - Full keyboard accessibility with focus trapping, focus management, visible outline indicators, and Escape-to-close.
  - 200% zoom reflow and responsive fluid layout.
- **Multilingual Support**:
  - Instant toggle between English (`en`) and Amharic (`am`).
  - Clear Ethiopic script typography and layout.
- **Accessibility Modes**:
  - **Simple Mode**: Reduces visual distractions and clutter for neurodivergent or overwhelmed learners.
  - **High Contrast**: Enhanced contrast ratio exceeding WCAG AAA.
  - **Text Scaling**: Normal, Large, and Extra Large font sizes.
- **Evidence-Grounded Citations**:
  - Displays source PDF/DOCX document titles and page numbers.
- **Live Human Escalation**:
  - One-click "Talk to a human" button with explicit learner consent for chat sharing.
- **Speech Alternative**:
  - Speech recognition with immediate graceful fallback if unsupported.

## Installation Example

```html
<!-- Inside the LMS page <head> or before </body> -->
<script
  src="http://localhost:8000/static/bridge.js"
  data-api="http://localhost:8000"
  data-course="<COURSE_UUID>"
  data-institution="<INSTITUTION_UUID>"
  data-lang="en">
</script>
```

