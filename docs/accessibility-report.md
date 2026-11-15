# Digital Bridge Assistant — WCAG 2.2 AA Conformance & Accessibility Report

**Lead Accessibility Engineer:** Koket
**Track:** 3 — Multilingual Assistant and Live Help

## 1. Conformance Status
The Digital Bridge embeddable widget (`frontend/widget/bridge.js`) and supporting backend services have been built to conform with **WCAG 2.2 Level AA**.

## 2. Accessibility Checklist & Implementations

| WCAG Criterion | Description | Implementation in Digital Bridge | Status |
|---|---|---|---|
| **1.3.1 Info and Relationships** | Structure & semantics | Native `<dialog role="dialog" aria-modal="true">`, `<header>`, `<main>`, `<button>` tags. | PASS |
| **1.4.3 Contrast (Minimum)** | 4.5:1 text contrast | Normal mode contrast ratio > 7:1; High-contrast mode > 15:1. | PASS |
| **1.4.4 Resize Text** | 200% zoom reflow | Relative `rem`/`em` sizing without horizontal overflow or clipped text. | PASS |
| **2.1.1 Keyboard** | Keyboard accessible | Every feature is operable via `Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`. | PASS |
| **2.1.2 No Keyboard Trap** | Focus can move away | Focus is managed inside the modal and restored upon close. | PASS |
| **2.4.7 Focus Visible** | Visible focus indicator | 3px high-contrast outline on all interactive elements in `:focus-visible`. | PASS |
| **3.1.2 Language of Parts** | Multilingual Amharic/English | Dynamic `dir="ltr"` / `dir="rtl"` and Ethiopic script font loading. | PASS |
| **4.1.3 Status Messages** | Screen reader announcements | `aria-live="polite"` polite live region announces incoming assistant replies. | PASS |

## 3. Assistive Technology Verification
- **NVDA / TalkBack**:
  - Open widget announcement: "Digital Bridge Assistant dialog, active."
  - Incoming response announcement: "New message from Digital Bridge Assistant: [content]."
  - Citations read out with document title and page number.
- **Keyboard-only User**:
  - `Tab` navigates through Launcher -> Language Switcher -> Settings -> Human Help -> Messages -> Input -> Send.
  - `Escape` dismisses the widget and returns focus to the launcher button.

## 4. Live Help, Accommodations & Career Gateway Accessibility (Yensew)

| Feature | Accessibility Standard | Implementation & Safeguard | Status |
|---|---|---|---|
| **One-Click Human Help** | WCAG 2.5.8 (Target Size), 3.3.1 (Error Identification) | Large, high-contrast button (>44px); immediate ticket creation without lengthy prerequisite forms. | PASS |
| **Learner Chat Consent** | Plain Language / Privacy | Plain-language consent check before sharing chat history; agent only sees what the learner permits. | PASS |
| **Learner-Controlled Screen Sharing** | WCAG 2.1.1 (Keyboard), Learner Autonomy | Strictly learner-initiated; persistent high-contrast "Stop Sharing" control operable via single keystroke (`Esc`). | PASS |
| **Low-Bandwidth 3G Fallback** | Resilience & Cognitive Ease | Static DOM / visual snapshot fallback for unstable connections where video streaming fails. | PASS |
| **Confidential Interview Accommodations** | Privacy-First / Zero Medical Diagnosis | Strictly functional adjustment choices (screen reader compatibility, 1.5x/2x extra time, sign language interpretation); zero disability diagnosis or medical records required. | PASS |
| **Cognitive "Simple Mode"** | Plain Language / Cognitive Accessibility | Translates dense corporate job postings into clear, digestible, plain-language bullet points. | PASS |
| **Telegram & SMS Job Alerts** | Screen Reader Friendly / Compact SMS | Clean Markdown without noisy decorative emojis; compact $\le 160$-char SMS alerts with one-step unsubscribe. | PASS |


