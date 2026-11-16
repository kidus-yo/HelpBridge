/**
 * Digital Bridge Assistant - Embeddable Accessibility & Learner-Support Widget
 * ALX Digital Bridge Accessibility Hackathon 2026 — Track 3
 * 
 * Developer: Koket (Developer 2 — Conversation Platform & Accessibility Engineer)
 * Conformance: WCAG 2.2 Level AA, Keyboard-only navigation, ARIA live region announcements,
 * Multilingual (English & Amharic), 200% zoom reflow, high-contrast, simple mode, RTL.
 */

(function () {
  'use strict';

  // Read configuration from script tag
  const currentScript = document.currentScript || (function() {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const SCRIPT_URL = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
  const API_BASE = (currentScript && currentScript.getAttribute('data-api')) || (SCRIPT_URL && SCRIPT_URL.origin) || '';
  const CONTEXT_TOKEN = (currentScript && currentScript.getAttribute('data-context-token')) || '';
  const INITIAL_LANG = (currentScript && currentScript.getAttribute('data-lang')) || 'en';

  // State
  let sessionId = null;
  let isOpen = false;
  let viewMode = 'chat'; // 'chat' | 'settings'
  let simpleMode = false;
  let textSize = 'normal'; // 'normal' | 'large' | 'xlarge'
  let isRtl = false;
  let highContrast = false;
  let voiceEnabled = true;
  let messages = [];
  let isLoading = false;
  let previousFocusedElement = null;
  let keydownListenerAttached = false;

  function getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
      headers['X-HelpBridge-Context'] = authToken;
    }
    return headers;
  }

  // Bilingual UI Dictionary
  const I18N = {
    en: {
      launcherLabel: 'Open Digital Bridge Assistant',
      closeLabel: 'Close assistant dialog',
      title: 'Digital Bridge Assistant',
      subtitle: 'Multilingual Tutor & Live Help',
      placeholder: 'Ask a question about this course...',
      sendButton: 'Send message',
      talkToHuman: 'Talk to a human',
      settingsTitle: 'Accessibility Settings',
      settingsButton: 'Settings',
      backToChat: 'Back to Chat',
      simpleMode: 'Simple Mode',
      simpleModeDesc: 'Reduces visual clutter and uses simplified text',
      textSize: 'Text Size',
      language: 'Language',
      contrast: 'High Contrast',
      contrastDesc: 'Enhances border outlines and high-contrast colors',
      direction: 'Right-to-Left (RTL)',
      directionDesc: 'Aligns text and interface from right to left',
      voice: 'Voice Features',
      voiceDesc: 'Enable speech recognition dictation and audio feedback',
      normal: 'Normal',
      large: 'Large (115%)',
      xlarge: 'Extra Large (135%)',
      connecting: 'Connecting...',
      typing: 'Assistant is finding verified course evidence...',
      citationsTitle: 'Verified Sources:',
      page: 'Page',
      humanEscalated: 'Your request for live human help has been submitted. A support agent will join shortly.',
      consentPrompt: 'Share recent chat context with support agent?',
      confirmHuman: 'Confirm Request',
      cancel: 'Cancel',
      offlineFaqBadge: 'Offline FAQ',
      groundedBadge: 'Verified Course Material',
      errorNetwork: 'Unable to reach the assistant server. Please try again or request human help.',
      contextMissing: 'A secure platform context is required. Please reload this page from your learning platform.',
      supportSubmitted: 'Your human-support request was submitted.',
      supportUnavailable: 'Unable to submit your support request. Please try again.',
      voiceInput: 'Voice input (Dictate)',
      voiceUnsupported: 'Speech recognition is not supported on this browser. Please type your message.',
      liveNewMessagePrefix: 'New message from'
    },
    am: {
      launcherLabel: 'የዲጂታል ብሪጅ ረዳትን ክፈት',
      closeLabel: 'የረዳት መስኮቱን ዝጋ',
      title: 'ዲጂታል ብሪጅ ረዳት',
      subtitle: 'የትምህርት ረዳት እና የቀጥታ ድጋፍ',
      placeholder: 'ስለዚህ ኮርስ ማንኛውንም ጥያቄ ይጠይቁ...',
      sendButton: 'መልዕክት ላክ',
      talkToHuman: 'የሰው ድጋፍ',
      settingsTitle: 'የተደራሽነት ቅንብሮች',
      settingsButton: 'ቅንብሮች',
      backToChat: 'ወደ ውይይት ተመለስ',
      simpleMode: 'ቀላል ሁነታ (Simple Mode)',
      simpleModeDesc: 'የማያስፈልጉ ዝርዝሮችን በመቀነስ ጽሑፉን ያቃልላል',
      textSize: 'የጽሑፍ መጠን',
      language: 'ቋንቋ (Language)',
      contrast: 'ከፍተኛ ንፅፅር (High Contrast)',
      contrastDesc: 'ለዓይን ግልጽ የሆኑ ቀለሞችን እና መስመሮችን ያደምቃል',
      direction: 'ከቀኝ ወደ ግራ (RTL)',
      directionDesc: 'የጽሑፍ አቅጣጫውን ከቀኝ ወደ ግራ ያደርጋል',
      voice: 'የድምፅ ግብዓት (Voice)',
      voiceDesc: 'በድምፅ መልዕክት ማስገባትን ያነቃል',
      normal: 'መደበኛ',
      large: 'ትልቅ (115%)',
      xlarge: 'በጣም ትልቅ (135%)',
      connecting: 'በመገናኘት ላይ...',
      typing: 'ረዳቱ የተረጋገጠ የትምህርት መረጃ በማፈላለግ ላይ ነው...',
      citationsTitle: 'የተረጋገጡ ምንጮች፡',
      page: 'ገጽ',
      humanEscalated: 'የቀጥታ የሰው ድጋፍ ጥያቄዎ ደርሷል። የድጋፍ ሰጪ በቅርቡ ያነጋግርዎታል።',
      consentPrompt: 'የቅርብ ጊዜ የውይይት ታሪክ ለድጋፍ ሰጪው ይጋራ?',
      confirmHuman: 'ጥያቄውን አረጋግጥ',
      cancel: 'ሰርዝ',
      offlineFaqBadge: 'ከመስመር ውጭ FAQ',
      groundedBadge: 'የተረጋገጠ የኮርስ ሰነድ',
      errorNetwork: 'ከአገልጋዩ ጋር መገናኘት አልተቻለም። እባክዎ እንደገና ይሞክሩ ወይም የሰው ድጋፍ ይጠይቁ።',
      contextMissing: 'የደህንነት መድረክ አውድ ያስፈልጋል። እባክዎ ከትምህርት መድረኩ ገጹን እንደገና ይክፈቱ።',
      supportSubmitted: 'የሰው ድጋፍ ጥያቄዎ ተልኳል።',
      supportUnavailable: 'የድጋፍ ጥያቄዎን መላክ አልተቻለም። እባክዎ እንደገና ይሞክሩ።',
      voiceInput: 'በድምፅ መልዕክት አስገባ',
      voiceUnsupported: 'ይህ አሳሽ ድምፅን ወደ ጽሑፍ መቀየር አይደግፍም። እባክዎ በጽሑፍ ያስገቡ።',
      liveNewMessagePrefix: 'አዲስ መልዕክት ከ'
    }
  };

  function t(key) {
    const langDict = I18N[currentLang] || I18N.en;
    return langDict[key] || I18N.en[key] || key;
  }

  // Scoped Stylesheet for Host-Isolation & Accessibility
  const STYLES = `
    #digital-bridge-root {
      --db-primary: #1e3a8a;
      --db-primary-dark: #172554;
      --db-accent: #2563eb;
      --db-bg: #ffffff;
      --db-surface: #f8fafc;
      --db-text: #0f172a;
      --db-text-muted: #475569;
      --db-border: #cbd5e1;
      --db-focus: #fbbf24;
      --db-font: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans Ethiopic", sans-serif;
      --db-font-size: 1rem;
      --db-radius: 12px;
      --db-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      font-family: var(--db-font);
      font-size: var(--db-font-size);
      color: var(--db-text);
      box-sizing: border-box;
      line-height: 1.5;
    }

    #digital-bridge-root.db-high-contrast {
      --db-primary: #000000;
      --db-primary-dark: #000000;
      --db-accent: #0000ee;
      --db-bg: #ffffff;
      --db-surface: #ffffff;
      --db-text: #000000;
      --db-text-muted: #000000;
      --db-border: #000000;
      --db-focus: #ffff00;
    }

    #digital-bridge-root.db-text-large {
      --db-font-size: 1.15rem;
    }

    #digital-bridge-root.db-text-xlarge {
      --db-font-size: 1.35rem;
    }

    #digital-bridge-root.db-simple-mode .db-decorative,
    #digital-bridge-root.db-simple-mode .db-badge-extra {
      display: none !important;
    }

    #digital-bridge-root.db-rtl {
      direction: rtl;
      text-align: right;
    }

    #digital-bridge-root.db-rtl .db-launcher {
      right: auto;
      left: 24px;
    }

    #digital-bridge-root.db-rtl .db-panel {
      right: auto;
      left: 24px;
    }

    #digital-bridge-root * {
      box-sizing: border-box;
    }

    /* Floating Launcher Button */
    .db-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 2147483640;
      background: var(--db-primary);
      color: #ffffff;
      border: 2px solid transparent;
      border-radius: 9999px;
      padding: 12px 20px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 10px;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
      transition: transform 0.2s ease, background 0.2s ease;
    }

    .db-launcher:hover {
      background: var(--db-primary-dark);
      transform: translateY(-2px);
    }

    .db-launcher:focus-visible,
    #digital-bridge-root button:focus-visible,
    #digital-bridge-root input:focus-visible,
    #digital-bridge-root select:focus-visible {
      outline: 3px solid var(--db-focus) !important;
      outline-offset: 2px !important;
    }

    /* Modal / Panel */
    .db-panel {
      position: fixed;
      bottom: 84px;
      right: 24px;
      width: min(420px, calc(100vw - 32px));
      height: min(650px, calc(100vh - 120px));
      background: var(--db-bg);
      border: 2px solid var(--db-border);
      border-radius: var(--db-radius);
      box-shadow: var(--db-shadow);
      z-index: 2147483641;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .db-panel.db-hidden {
      display: none !important;
    }

    /* Header */
    .db-header {
      background: var(--db-primary);
      color: #ffffff;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }

    .db-header-title h2 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 700;
    }

    .db-header-title p {
      margin: 2px 0 0 0;
      font-size: 0.8rem;
      opacity: 0.9;
    }

    .db-header-actions {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .db-btn-icon {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.3);
      color: #ffffff;
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 0.85rem;
      cursor: pointer;
    }

    .db-btn-icon:hover {
      background: rgba(255, 255, 255, 0.15);
    }

    /* Quick Toolbar */
    .db-quick-toolbar {
      background: var(--db-surface);
      border-bottom: 1px solid var(--db-border);
      padding: 6px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
    }

    .db-btn-text {
      background: none;
      border: 1px solid var(--db-border);
      border-radius: 4px;
      padding: 4px 8px;
      font-size: 0.8rem;
      color: var(--db-text);
      cursor: pointer;
    }

    .db-btn-human {
      background: #fee2e2;
      border: 1px solid #ef4444;
      color: #b91c1c;
      font-weight: 600;
    }

    /* Messages container */
    .db-messages {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: var(--db-surface);
    }

    .db-message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 0.95rem;
      word-break: break-word;
    }

    .db-message-learner {
      align-self: flex-end;
      background: var(--db-primary);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }

    .db-message-assistant {
      align-self: flex-start;
      background: var(--db-bg);
      color: var(--db-text);
      border: 1px solid var(--db-border);
      border-bottom-left-radius: 2px;
    }

    .db-message-agent {
      align-self: flex-start;
      background: #fef3c7;
      border: 1px solid #f59e0b;
      color: #92400e;
    }

    /* Citations */
    .db-citations {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed var(--db-border);
      font-size: 0.8rem;
    }

    .db-citation-item {
      display: inline-block;
      background: #e0e7ff;
      color: #3730a3;
      padding: 2px 8px;
      border-radius: 4px;
      margin: 2px 4px 2px 0;
      font-weight: 500;
    }

    .db-badge-grounded {
      display: inline-block;
      font-size: 0.7rem;
      background: #dcfce7;
      color: #166534;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 4px;
      font-weight: 600;
    }

    /* Input Area */
    .db-input-area {
      padding: 10px 12px;
      background: var(--db-bg);
      border-top: 1px solid var(--db-border);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .db-input-row {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .db-input {
      flex: 1;
      padding: 10px 12px;
      border: 1px solid var(--db-border);
      border-radius: 6px;
      font-size: 0.95rem;
      color: var(--db-text);
      background: var(--db-bg);
      font-family: inherit;
    }

    .db-btn-send {
      background: var(--db-primary);
      color: #ffffff;
      border: none;
      border-radius: 6px;
      padding: 10px 14px;
      font-weight: 600;
      cursor: pointer;
    }

    .db-btn-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Accessibility Settings View */
    .db-settings-view {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      background: var(--db-bg);
      flex: 1;
      overflow-y: auto;
    }

    .db-setting-item {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--db-border);
    }

    .db-setting-label {
      font-weight: 600;
      font-size: 0.95rem;
    }

    .db-setting-desc {
      font-size: 0.8rem;
      color: var(--db-text-muted);
      margin-top: 2px;
    }

    .db-select {
      padding: 6px 10px;
      border: 1px solid var(--db-border);
      border-radius: 6px;
      background: var(--db-bg);
      color: var(--db-text);
      font-size: 0.9rem;
    }

    /* Screen reader only */
    .db-sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }
  `;

  function handleKeyDown(e) {
    if (e.key === 'Escape' && isOpen) {
      toggleWidget(false);
    }
  }

  function init(options) {
    if (options && typeof options === 'object') {
      if (options.api) apiBase = options.api;
      if (options.course) courseId = options.course;
      if (options.institution) institutionId = options.institution;
      if (options.lang) currentLang = options.lang;
      if (options.token) authToken = options.token;
    }

    if (document.getElementById('digital-bridge-root')) return;

    const hostDiv = document.createElement('div');
    hostDiv.id = 'digital-bridge-root';
    document.body.appendChild(hostDiv);

    let styleEl = document.getElementById('digital-bridge-styles');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'digital-bridge-styles';
      styleEl.textContent = STYLES;
      document.head.appendChild(styleEl);
    }

    if (!keydownListenerAttached) {
      document.addEventListener('keydown', handleKeyDown);
      keydownListenerAttached = true;
    }

    render();
    initSession();
  }

  function destroy() {
    const root = document.getElementById('digital-bridge-root');
    if (root && root.parentNode) {
      root.parentNode.removeChild(root);
    }
    const styleEl = document.getElementById('digital-bridge-styles');
    if (styleEl && styleEl.parentNode) {
      styleEl.parentNode.removeChild(styleEl);
    }
    if (keydownListenerAttached) {
      document.removeEventListener('keydown', handleKeyDown);
      keydownListenerAttached = false;
    }
    isOpen = false;
    sessionId = null;
    messages = [];
  }

  function render() {
    const root = document.getElementById('digital-bridge-root');
    if (!root) return;

    root.className = [
      highContrast ? 'db-high-contrast' : '',
      simpleMode ? 'db-simple-mode' : '',
      textSize === 'large' ? 'db-text-large' : '',
      textSize === 'xlarge' ? 'db-text-xlarge' : '',
      isRtl ? 'db-rtl' : ''
    ].filter(Boolean).join(' ');

    root.dir = isRtl ? 'rtl' : 'ltr';

    root.innerHTML = `
      <div id="db-live-announcer" class="db-sr-only" role="status" aria-live="polite" aria-atomic="true"></div>

      <!-- Floating Launcher Button -->
      <button 
        type="button" 
        class="db-launcher" 
        id="db-launcher-btn" 
        aria-expanded="${isOpen}" 
        aria-controls="db-dialog"
        aria-label="${t('launcherLabel')}"
        title="${t('launcherLabel')}">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>${t('title')}</span>
      </button>

      <!-- Main Assistant Dialog -->
      <section 
        id="db-dialog" 
        class="db-panel ${isOpen ? '' : 'db-hidden'}" 
        role="dialog" 
        aria-modal="true" 
        aria-labelledby="db-panel-title">
        
        <!-- Header -->
        <header class="db-header">
          <div class="db-header-title">
            <h2 id="db-panel-title">${t('title')}</h2>
            <p>${t('subtitle')}</p>
          </div>
          <div class="db-header-actions">
            <!-- Settings button -->
            <button type="button" class="db-btn-icon" id="db-btn-settings" title="${viewMode === 'settings' ? t('backToChat') : t('settingsTitle')}" aria-label="${viewMode === 'settings' ? t('backToChat') : t('settingsTitle')}">
              ${viewMode === 'settings' ? '💬' : '⚙️'}
            </button>
            <!-- Close dialog -->
            <button type="button" class="db-btn-icon" id="db-btn-close" aria-label="${t('closeLabel')}">
              ✕
            </button>
          </div>
        </header>

        <!-- View Body: Either Chat or Settings -->
        ${viewMode === 'settings' ? renderSettingsView() : renderChatView()}
      </section>
    `;

    bindEvents();
  }

  function renderChatView() {
    return `
      <!-- Quick Access Toolbar -->
      <div class="db-quick-toolbar">
        <button type="button" class="db-btn-text db-btn-human" id="db-btn-human">
          🤝 ${t('talkToHuman')}
        </button>
        <button type="button" class="db-btn-text" id="db-btn-quick-lang">
          🌐 ${currentLang === 'en' ? 'አማርኛ' : 'English'}
        </button>
        <button type="button" class="db-btn-text" id="db-btn-simple">
          ${simpleMode ? '✓ ' : ''}${t('simpleMode')}
        </button>
      </div>

      <!-- Messages List -->
      <div class="db-messages" id="db-messages-list" role="log" aria-label="Conversation history">
        ${renderMessages()}
      </div>

      <!-- Loading / Typing Indicator -->
      ${isLoading ? `<div style="padding: 6px 14px; font-size: 0.85rem; color: var(--db-text-muted); font-style: italic;">${t('typing')}</div>` : ''}

      <!-- Message Input Form -->
      <form class="db-input-area" id="db-input-form">
        <div class="db-input-row">
          <input 
            type="text" 
            class="db-input" 
            id="db-msg-input" 
            placeholder="${t('placeholder')}" 
            autocomplete="off" 
            aria-label="${t('placeholder')}" />
          
          ${voiceEnabled ? `
            <button type="button" class="db-btn-text" id="db-btn-mic" title="${t('voiceInput')}" aria-label="${t('voiceInput')}">
              🎤
            </button>
          ` : ''}

          <button type="submit" class="db-btn-send" id="db-btn-send" ${isLoading ? 'disabled' : ''}>
            ${t('sendButton')}
          </button>
        </div>
      </form>
    `;
  }

  function renderSettingsView() {
    return `
      <div class="db-settings-view">
        <h3 style="margin: 0 0 8px 0; font-size: 1.05rem;">${t('settingsTitle')}</h3>
        
        <!-- Language setting -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('language')}</div>
            <div class="db-setting-desc">Switch between English and Amharic</div>
          </div>
          <select id="db-set-lang" class="db-select" aria-label="${t('language')}">
            <option value="en" ${currentLang === 'en' ? 'selected' : ''}>English</option>
            <option value="am" ${currentLang === 'am' ? 'selected' : ''}>አማርኛ (Amharic)</option>
          </select>
        </div>

        <!-- Text Size -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('textSize')}</div>
            <div class="db-setting-desc">Scale text for readability</div>
          </div>
          <select id="db-set-size" class="db-select" aria-label="${t('textSize')}">
            <option value="normal" ${textSize === 'normal' ? 'selected' : ''}>${t('normal')}</option>
            <option value="large" ${textSize === 'large' ? 'selected' : ''}>${t('large')}</option>
            <option value="xlarge" ${textSize === 'xlarge' ? 'selected' : ''}>${t('xlarge')}</option>
          </select>
        </div>

        <!-- Simple Mode -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('simpleMode')}</div>
            <div class="db-setting-desc">${t('simpleModeDesc')}</div>
          </div>
          <input type="checkbox" id="db-set-simple" ${simpleMode ? 'checked' : ''} style="width: 20px; height: 20px;" aria-label="${t('simpleMode')}" />
        </div>

        <!-- High Contrast -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('contrast')}</div>
            <div class="db-setting-desc">${t('contrastDesc')}</div>
          </div>
          <input type="checkbox" id="db-set-contrast" ${highContrast ? 'checked' : ''} style="width: 20px; height: 20px;" aria-label="${t('contrast')}" />
        </div>

        <!-- RTL display -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('direction')}</div>
            <div class="db-setting-desc">${t('directionDesc')}</div>
          </div>
          <input type="checkbox" id="db-set-rtl" ${isRtl ? 'checked' : ''} style="width: 20px; height: 20px;" aria-label="${t('direction')}" />
        </div>

        <!-- Voice features -->
        <div class="db-setting-item">
          <div>
            <div class="db-setting-label">${t('voice')}</div>
            <div class="db-setting-desc">${t('voiceDesc')}</div>
          </div>
          <input type="checkbox" id="db-set-voice" ${voiceEnabled ? 'checked' : ''} style="width: 20px; height: 20px;" aria-label="${t('voice')}" />
        </div>

        <button type="button" class="db-btn-send" id="db-btn-done-settings" style="margin-top: 12px; width: 100%;">
          ${t('backToChat')}
        </button>
      </div>
    `;
  }

  function renderMessages() {
    if (messages.length === 0) {
      return `
        <div style="text-align: center; color: var(--db-text-muted); padding: 24px 12px;">
          <p style="font-weight: 600; margin-bottom: 4px;">${currentLang === 'am' ? 'እንኳን ደህና መጡ!' : 'Welcome to Digital Bridge!'}</p>
          <p style="font-size: 0.85rem;">${currentLang === 'am' ? 'ስለ ኮርሱ ማንኛውንም ጥያቄ ይጠይቁ ወይም የሰው ድጋፍ ሰጪ ያነጋግሩ።' : 'Ask questions grounded in your course materials, or request live support.'}</p>
        </div>
      `;
    }

    return messages.map(msg => {
      const isLearner = msg.sender_type === 'learner';
      const isAgent = msg.sender_type === 'agent';
      const citations = (msg.metadata && msg.metadata.citations) || msg.citations || [];

      let citationsHtml = '';
      if (citations.length > 0) {
        citationsHtml = `
          <div class="db-citations">
            <span class="db-badge-grounded">✓ ${t('groundedBadge')}</span>
            <div style="margin-top: 4px;">
              <strong>${t('citationsTitle')}</strong>
              ${citations.map(c => {
                const title = escapeHtml(c.document_title);
                const section = escapeHtml(c.section);
                const page = escapeHtml(c.page);
                return `
                  <span class="db-citation-item" title="${title} - ${section}">
                    📄 ${title}${c.page ? ` (${t('page')} ${page})` : ''}
                  </span>
                `;
              }).join('')}
            </div>
          </div>
        `;
      }

      return `
        <div class="db-message ${isLearner ? 'db-message-learner' : (isAgent ? 'db-message-agent' : 'db-message-assistant')}">
          ${isAgent ? '<div style="font-size: 0.75rem; font-weight: 700; margin-bottom: 2px;">Support Agent:</div>' : ''}
          <div dir="auto">${escapeHtml(msg.content)}</div>
          ${citationsHtml}
        </div>
      `;
    }).join('');
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function authHeaders(extra) {
    if (!CONTEXT_TOKEN) throw new Error(t('contextMissing'));
    return Object.assign(
      { 'Authorization': `Bearer ${CONTEXT_TOKEN}` },
      extra || {}
    );
  }

  function announce(text) {
    const announcer = document.getElementById('db-live-announcer');
    if (announcer) {
      announcer.textContent = '';
      setTimeout(() => {
        announcer.textContent = text;
      }, 50);
    }
  }

  function toggleWidget(open) {
    isOpen = typeof open === 'boolean' ? open : !isOpen;
    if (isOpen) {
      previousFocusedElement = document.activeElement;
    }
    render();

    if (isOpen) {
      const input = document.getElementById('db-msg-input');
      if (input) input.focus();
      scrollMessagesToBottom();
    } else {
      if (previousFocusedElement && typeof previousFocusedElement.focus === 'function') {
        previousFocusedElement.focus();
      }
    }
  }

  function scrollMessagesToBottom() {
    const list = document.getElementById('db-messages-list');
    if (list) list.scrollTop = list.scrollHeight;
  }

  // Session & Accessibility API Communication
  async function initSession() {
    try {
      if (!CONTEXT_TOKEN) {
        messages.push({ sender_type: 'assistant', content: t('contextMissing') });
        render();
        return false;
      }
      const payload = {
        channel: 'web',
        preferred_language: currentLang
      };

      const res = await fetch(`${apiBase}/api/v1/chat/sessions/`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        sessionId = data.id;
        loadAccessibilityPreferences();
        return true;
      }
      messages.push({ sender_type: 'assistant', content: t('errorNetwork') });
      render();
      return false;
    } catch (err) {
      messages.push({ sender_type: 'assistant', content: err.message || t('errorNetwork') });
      render();
      return false;
    }
  }

  async function loadAccessibilityPreferences() {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/accessibility/preferences/${sessionId}/`, {
        headers: authHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        simpleMode = !!data.simple_mode;
        textSize = data.text_size || 'normal';
        isRtl = !!data.right_to_left || data.text_direction === 'rtl';
        highContrast = !!data.high_contrast;
        voiceEnabled = data.voice_enabled !== false;
        if (data.preferred_language || data.language) {
          currentLang = data.preferred_language || data.language;
        }
        render();
      }
    } catch (e) {
      // Preserves local defaults
    }
  }

  async function updateAccessibilityPreferences(patchData) {
    // Apply locally first for immediate responsiveness
    if ('language' in patchData) currentLang = patchData.language;
    if ('preferred_language' in patchData) currentLang = patchData.preferred_language;
    if ('simple_mode' in patchData) simpleMode = patchData.simple_mode;
    if ('text_size' in patchData) textSize = patchData.text_size;
    if ('voice_enabled' in patchData) voiceEnabled = patchData.voice_enabled;
    if ('right_to_left' in patchData) isRtl = patchData.right_to_left;
    if ('high_contrast' in patchData) highContrast = patchData.high_contrast;

    render();

    // Persist to backend if session exists
    if (!sessionId) return;
    try {
      await fetch(`${apiBase}/api/v1/accessibility/preferences/${sessionId}/`, {
        method: 'PATCH',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(patchData)
      });
    } catch (e) {
      // Local state maintained
    }
  }

  async function sendMessage(content) {
    if (!content || !content.trim()) return;

    const trimmed = content.trim();
    messages.push({
      sender_type: 'learner',
      content: trimmed,
      language: currentLang
    });
    isLoading = true;
    render();
    scrollMessagesToBottom();

    try {
      if (!sessionId && !(await initSession())) return;

      const res = await fetch(`${apiBase}/api/v1/chat/sessions/${sessionId}/messages/`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ content: trimmed, language: currentLang })
      });

      if (res.ok) {
        const data = await res.json();
        messages.push(Object.assign({}, data.assistant_message, {
          metadata: {
            citations: data.citations || [],
            grounded: data.grounded,
            fallback_used: data.fallback_used
          }
        }));
        announce(`${t('liveNewMessagePrefix')} ${t('title')}: ${data.assistant_message.content}`);
      } else {
        messages.push({
          sender_type: 'assistant',
          content: t('errorNetwork')
        });
        announce(t('errorNetwork'));
      }
    } catch (err) {
      messages.push({
        sender_type: 'assistant',
        content: t('errorNetwork')
      });
      announce(t('errorNetwork'));
    } finally {
      isLoading = false;
      render();
      scrollMessagesToBottom();
      const input = document.getElementById('db-msg-input');
      if (input) input.focus();
    }
  }

  async function handleHumanEscalation() {
    const consent = window.confirm(`${t('consentPrompt')}\n\n[OK] = ${t('confirmHuman')}`);
    try {
      if (!sessionId && !(await initSession())) return;
      const response = await fetch(`${API_BASE}/api/v1/support/requests/`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          subject: 'Learner requested human assistance',
          description: 'Please contact the learner through this support request.',
          category: 'course',
          chat_session_id: sessionId,
          learner_consent_chat_history: consent,
          language: currentLang
        })
      });
      if (!response.ok) throw new Error(t('supportUnavailable'));
      const ticket = await response.json();
      const result = `${t('supportSubmitted')} (ID: ${ticket.id})`;
      messages.push({ sender_type: 'assistant', content: result });
      announce(result);
    } catch (err) {
      messages.push({ sender_type: 'assistant', content: err.message || t('supportUnavailable') });
      announce(t('supportUnavailable'));
    }
    render();
    scrollMessagesToBottom();
  }

  function handleVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert(t('voiceUnsupported'));
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = currentLang === 'am' ? 'am-ET' : 'en-US';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      const micBtn = document.getElementById('db-btn-mic');
      if (micBtn) micBtn.textContent = '🔴';

      recognition.onresult = (event) => {
        const speechResult = event.results[0][0].transcript;
        const input = document.getElementById('db-msg-input');
        if (input) {
          input.value = speechResult;
          input.focus();
        }
      };

      recognition.onerror = () => {
        alert(t('voiceUnsupported'));
      };

      recognition.onend = () => {
        if (micBtn) micBtn.textContent = '🎤';
      };

      recognition.start();
    } catch (e) {
      alert(t('voiceUnsupported'));
    }
  }

  function bindEvents() {
    const launcher = document.getElementById('db-launcher-btn');
    if (launcher) launcher.onclick = () => toggleWidget(true);

    const closeBtn = document.getElementById('db-btn-close');
    if (closeBtn) closeBtn.onclick = () => toggleWidget(false);

    const settingsBtn = document.getElementById('db-btn-settings');
    if (settingsBtn) {
      settingsBtn.onclick = () => {
        viewMode = viewMode === 'settings' ? 'chat' : 'settings';
        render();
      };
    }

    const doneSettingsBtn = document.getElementById('db-btn-done-settings');
    if (doneSettingsBtn) {
      doneSettingsBtn.onclick = () => {
        viewMode = 'chat';
        render();
      };
    }

    const quickLangBtn = document.getElementById('db-btn-quick-lang');
    if (quickLangBtn) {
      quickLangBtn.onclick = () => {
        const nextLang = currentLang === 'en' ? 'am' : 'en';
        updateAccessibilityPreferences({ language: nextLang });
      };
    }

    const simpleBtn = document.getElementById('db-btn-simple');
    if (simpleBtn) {
      simpleBtn.onclick = () => {
        updateAccessibilityPreferences({ simple_mode: !simpleMode });
      };
    }

    const humanBtn = document.getElementById('db-btn-human');
    if (humanBtn) humanBtn.onclick = handleHumanEscalation;

    const micBtn = document.getElementById('db-btn-mic');
    if (micBtn) micBtn.onclick = handleVoiceInput;

    const form = document.getElementById('db-input-form');
    if (form) {
      form.onsubmit = (e) => {
        e.preventDefault();
        const input = document.getElementById('db-msg-input');
        if (input) {
          sendMessage(input.value);
          input.value = '';
        }
      };
    }

    // Settings input change handlers
    const setLang = document.getElementById('db-set-lang');
    if (setLang) {
      setLang.onchange = (e) => updateAccessibilityPreferences({ language: e.target.value });
    }

    const setSize = document.getElementById('db-set-size');
    if (setSize) {
      setSize.onchange = (e) => updateAccessibilityPreferences({ text_size: e.target.value });
    }

    const setSimple = document.getElementById('db-set-simple');
    if (setSimple) {
      setSimple.onchange = (e) => updateAccessibilityPreferences({ simple_mode: e.target.checked });
    }

    const setContrast = document.getElementById('db-set-contrast');
    if (setContrast) {
      setContrast.onchange = (e) => updateAccessibilityPreferences({ high_contrast: e.target.checked });
    }

    const setRtl = document.getElementById('db-set-rtl');
    if (setRtl) {
      setRtl.onchange = (e) => updateAccessibilityPreferences({ right_to_left: e.target.checked });
    }

    const setVoice = document.getElementById('db-set-voice');
    if (setVoice) {
      setVoice.onchange = (e) => updateAccessibilityPreferences({ voice_enabled: e.target.checked });
    }

  }

  // Public integration API
  const publicApi = {
    init: init,
    open: () => toggleWidget(true),
    close: () => toggleWidget(false),
    toggle: () => toggleWidget(),
    destroy: destroy,
    setLanguage: (lang) => updateAccessibilityPreferences({ language: lang, preferred_language: lang }),
    setHighContrast: (val) => updateAccessibilityPreferences({ high_contrast: !!val }),
    setSimpleMode: (val) => updateAccessibilityPreferences({ simple_mode: !!val }),
    sendMessage: (text) => sendMessage(text),
    getState: () => ({
      sessionId,
      isOpen,
      currentLang,
      simpleMode,
      highContrast,
      textSize,
      isRtl,
      messageCount: messages.length,
      isLoading
    })
  };

  if (typeof window !== 'undefined') {
    window.DigitalBridgeAssistant = publicApi;
    window.DigitalBridge = publicApi;
  }

  // Auto-boot when DOM ready
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => init());
    } else {
      init();
    }
  }
})();
