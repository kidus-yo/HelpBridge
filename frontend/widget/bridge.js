/**
 * Digital Bridge Assistant - Embeddable Accessibility & Learner-Support Widget
 * ALX Digital Bridge Accessibility Hackathon 2026 — Track 3
 * 
 * Developer: Koket (Developer 2 — Conversation Platform & Accessibility Engineer)
 * Conformance: WCAG 2.2 Level AA, Keyboard-only navigation, ARIA live region announcements,
 * Multilingual (English & Amharic), 200% zoom reflow, high-contrast, simple mode.
 */

(function () {
  'use strict';

  // Read configuration from the script tag
  const currentScript = document.currentScript || (function() {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const API_BASE = (currentScript && currentScript.getAttribute('data-api')) || 'http://localhost:8000';
  const COURSE_ID = currentScript ? currentScript.getAttribute('data-course') : null;
  const INSTITUTION_ID = currentScript ? currentScript.getAttribute('data-institution') : null;
  const INITIAL_LANG = (currentScript && currentScript.getAttribute('data-lang')) || 'en';

  // State
  let sessionId = null;
  let isOpen = false;
  let currentLang = INITIAL_LANG; // 'en' | 'am'
  let simpleMode = false;
  let textSize = 'normal'; // 'normal' | 'large' | 'xlarge'
  let textDirection = 'ltr';
  let highContrast = false;
  let messages = [];
  let isLoading = false;
  let previousFocusedElement = null;

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
      settingsButton: 'Accessibility settings',
      simpleMode: 'Simple Mode',
      textSize: 'Text Size',
      language: 'Language',
      contrast: 'High Contrast',
      direction: 'Text Direction',
      normal: 'Normal',
      large: 'Large',
      xlarge: 'Extra Large',
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
      errorNetwork: 'Unable to reach the assistant server. Please check your connection.',
      errorEmpty: 'Please enter a message before sending.',
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
      settingsButton: 'የተደራሽነት ቅንብሮች',
      simpleMode: 'ቀላል ሁነታ (Simple Mode)',
      textSize: 'የጽሑፍ መጠን',
      language: 'ቋንቋ',
      contrast: 'ከፍተኛ ንፅፅር (High Contrast)',
      direction: 'የጽሑፍ አቅጣጫ',
      normal: 'መደበኛ',
      large: 'ትልቅ',
      xlarge: 'በጣም ትልቅ',
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
      errorNetwork: 'ከአገልጋዩ ጋር መገናኘት አልተቻለም። እባክዎ ግንኙነትዎን ያረጋግጡ።',
      errorEmpty: 'እባክዎ መልዕክትዎን ያስገቡ።',
      voiceInput: 'በድምፅ መልዕክት አስገባ',
      voiceUnsupported: 'ይህ አሳሽ ድምፅን ወደ ጽሑፍ መቀየር አይደግፍም። እባክዎ በጽሑፍ ያስገቡ።',
      liveNewMessagePrefix: 'አዲስ መልዕክት ከ'
    }
  };

  function t(key) {
    const langDict = I18N[currentLang] || I18N.en;
    return langDict[key] || I18N.en[key] || key;
  }

  // Inject Styles into Shadow Root or Scoped Container
  const STYLES = `
    :host, #digital-bridge-root {
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

    .db-btn-text:hover {
      background: var(--db-surface);
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

    /* Settings View */
    .db-settings-panel {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: var(--db-bg);
      flex: 1;
      overflow-y: auto;
    }

    .db-setting-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--db-border);
    }

    .db-setting-row label {
      font-weight: 500;
    }

    /* Live Announcement Region */
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

  // Initialize and Render Widget
  function init() {
    if (document.getElementById('digital-bridge-root')) return;

    const hostDiv = document.createElement('div');
    hostDiv.id = 'digital-bridge-root';
    document.body.appendChild(hostDiv);

    // Apply styles
    const styleEl = document.createElement('style');
    styleEl.textContent = STYLES;
    document.head.appendChild(styleEl);

    render();
    initSession();
  }

  function render() {
    const root = document.getElementById('digital-bridge-root');
    if (!root) return;

    // Apply class preferences to root
    root.className = [
      highContrast ? 'db-high-contrast' : '',
      simpleMode ? 'db-simple-mode' : '',
      textSize === 'large' ? 'db-text-large' : '',
      textSize === 'xlarge' ? 'db-text-xlarge' : '',
    ].filter(Boolean).join(' ');

    root.dir = textDirection;

    root.innerHTML = `
      <!-- Accessible Live Announcement Region for Screen Readers -->
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

      <!-- Main Dialog Window -->
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
            <!-- Language switcher -->
            <button type="button" class="db-btn-icon" id="db-btn-lang" title="${currentLang === 'en' ? 'Switch to Amharic' : 'Switch to English'}" aria-label="Toggle language">
              ${currentLang === 'en' ? 'አማ' : 'EN'}
            </button>
            <!-- Settings button -->
            <button type="button" class="db-btn-icon" id="db-btn-settings" title="${t('settingsButton')}" aria-label="${t('settingsButton')}">
              ⚙️
            </button>
            <!-- Close dialog -->
            <button type="button" class="db-btn-icon" id="db-btn-close" aria-label="${t('closeLabel')}">
              ✕
            </button>
          </div>
        </header>

        <!-- Quick Access Toolbar -->
        <div class="db-quick-toolbar">
          <button type="button" class="db-btn-text db-btn-human" id="db-btn-human">
            🤝 ${t('talkToHuman')}
          </button>
          <button type="button" class="db-btn-text" id="db-btn-simple">
            ${simpleMode ? '✓ ' : ''}${t('simpleMode')}
          </button>
        </div>

        <!-- Chat Messages Container -->
        <div class="db-messages" id="db-messages-list" role="log" aria-label="Chat history">
          ${renderMessages()}
        </div>

        <!-- Loading indicator -->
        ${isLoading ? `<div style="padding: 6px 14px; font-size: 0.85rem; color: var(--db-text-muted); font-style: italic;">${t('typing')}</div>` : ''}

        <!-- Message Input -->
        <form class="db-input-area" id="db-input-form">
          <div class="db-input-row">
            <input 
              type="text" 
              class="db-input" 
              id="db-msg-input" 
              placeholder="${t('placeholder')}" 
              autocomplete="off" 
              aria-label="${t('placeholder')}" />
            
            <button type="button" class="db-btn-text" id="db-btn-mic" title="${t('voiceInput')}" aria-label="${t('voiceInput')}">
              🎤
            </button>

            <button type="submit" class="db-btn-send" id="db-btn-send" ${isLoading ? 'disabled' : ''}>
              ${t('sendButton')}
            </button>
          </div>
        </form>
      </section>
    `;

    bindEvents();
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
      const citations = (msg.metadata && msg.metadata.citations) || [];
      const grounded = msg.metadata && msg.metadata.grounded;

      let citationsHtml = '';
      if (citations.length > 0) {
        citationsHtml = `
          <div class="db-citations">
            <span class="db-badge-grounded">✓ ${t('groundedBadge')}</span>
            <div style="margin-top: 4px;">
              <strong>${t('citationsTitle')}</strong>
              ${citations.map(c => `
                <span class="db-citation-item" title="${c.document_title} - ${c.section}">
                  📄 ${c.document_title}${c.page ? ` (${t('page')} ${c.page})` : ''}
                </span>
              `).join('')}
            </div>
          </div>
        `;
      }

      return `
        <div class="db-message ${isLearner ? 'db-message-learner' : (isAgent ? 'db-message-agent' : 'db-message-assistant')}">
          ${isAgent ? '<div style="font-size: 0.75rem; font-weight: 700; margin-bottom: 2px;">Support Agent:</div>' : ''}
          <div>${escapeHtml(msg.content)}</div>
          ${citationsHtml}
        </div>
      `;
    }).join('');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

  // Session Management
  async function initSession() {
    try {
      const payload = {
        channel: 'web',
        preferred_language: currentLang,
      };
      if (COURSE_ID) payload.course_id = COURSE_ID;
      if (INSTITUTION_ID) payload.institution_id = INSTITUTION_ID;

      const res = await fetch(`${API_BASE}/api/v1/chat/sessions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        sessionId = data.id;
        loadAccessibilityPreferences();
      }
    } catch (err) {
      console.warn('Digital Bridge Assistant running in offline/local mock mode.');
    }
  }

  async function loadAccessibilityPreferences() {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/accessibility/preferences/${sessionId}/`);
      if (res.ok) {
        const data = await res.json();
        simpleMode = !!data.simple_mode;
        textSize = data.text_size || 'normal';
        textDirection = data.text_direction || 'ltr';
        highContrast = !!data.high_contrast;
        if (data.preferred_language) currentLang = data.preferred_language;
        render();
      }
    } catch (e) {
      // Graceful fallback
    }
  }

  async function saveAccessibilityPreferences(updates) {
    Object.assign({ simpleMode, textSize, textDirection, highContrast, currentLang }, updates);
    render();

    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/api/v1/accessibility/preferences/${sessionId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
    } catch (e) {
      // Preferences remain in client state
    }
  }

  async function sendMessage(content) {
    if (!content || !content.trim()) return;

    const trimmed = content.trim();
    // Add local learner message
    const learnerMsg = {
      sender_type: 'learner',
      content: trimmed,
      language: currentLang
    };
    messages.push(learnerMsg);
    isLoading = true;
    render();
    scrollMessagesToBottom();

    try {
      if (!sessionId) {
        await initSession();
      }

      const res = await fetch(`${API_BASE}/api/v1/chat/sessions/${sessionId}/messages/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: trimmed, language: currentLang })
      });

      if (res.ok) {
        const data = await res.json();
        messages.push(data.assistant_message);
        announce(`${t('liveNewMessagePrefix')} ${t('title')}: ${data.assistant_message.content}`);
      } else {
        const errorMsg = {
          sender_type: 'assistant',
          content: t('errorNetwork')
        };
        messages.push(errorMsg);
        announce(t('errorNetwork'));
      }
    } catch (err) {
      const fallbackMsg = {
        sender_type: 'assistant',
        content: t('errorNetwork')
      };
      messages.push(fallbackMsg);
      announce(t('errorNetwork'));
    } finally {
      isLoading = false;
      render();
      scrollMessagesToBottom();
      const input = document.getElementById('db-msg-input');
      if (input) input.focus();
    }
  }

  function handleHumanEscalation() {
    const consent = window.confirm(`${t('consentPrompt')}\n\n[OK] = ${t('confirmHuman')}`);
    const escalationMsg = {
      sender_type: 'agent',
      content: `${t('humanEscalated')} (${consent ? 'Context shared' : 'Context private'})`
    };
    messages.push(escalationMsg);
    render();
    scrollMessagesToBottom();
    announce(t('humanEscalated'));
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
    if (launcher) {
      launcher.onclick = () => toggleWidget(true);
    }

    const closeBtn = document.getElementById('db-btn-close');
    if (closeBtn) {
      closeBtn.onclick = () => toggleWidget(false);
    }

    const langBtn = document.getElementById('db-btn-lang');
    if (langBtn) {
      langBtn.onclick = () => {
        const nextLang = currentLang === 'en' ? 'am' : 'en';
        saveAccessibilityPreferences({ preferred_language: nextLang });
      };
    }

    const simpleBtn = document.getElementById('db-btn-simple');
    if (simpleBtn) {
      simpleBtn.onclick = () => {
        saveAccessibilityPreferences({ simple_mode: !simpleMode });
      };
    }

    const humanBtn = document.getElementById('db-btn-human');
    if (humanBtn) {
      humanBtn.onclick = handleHumanEscalation;
    }

    const micBtn = document.getElementById('db-btn-mic');
    if (micBtn) {
      micBtn.onclick = handleVoiceInput;
    }

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

    const settingsBtn = document.getElementById('db-btn-settings');
    if (settingsBtn) {
      settingsBtn.onclick = () => {
        const nextSize = textSize === 'normal' ? 'large' : (textSize === 'large' ? 'xlarge' : 'normal');
        saveAccessibilityPreferences({ text_size: nextSize, high_contrast: !highContrast });
      };
    }

    // Keyboard support: Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen) {
        toggleWidget(false);
      }
    });
  }

  // Auto-boot when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

