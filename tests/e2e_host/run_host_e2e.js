/**
 * Comprehensive Browser-Environment E2E Host Integration Test
 * Simulates a third-party LMS host loading bridge.js and tests all Phase 2 requirements.
 */

const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

async function runE2ETests() {
  console.log('================================================================');
  console.log('   RUNNING E2E HOST PLUGIN INTEGRATION TEST SUITE (JSDOM)      ');
  console.log('================================================================\n');

  const htmlPath = path.join(__dirname, 'index.html');
  const bridgeJsPath = path.join(__dirname, '../../frontend/widget/bridge.js');
  const bridgeJsSource = fs.readFileSync(bridgeJsPath, 'utf8');

  let passed = 0;
  let failed = 0;

  function assert(condition, testName, details = '') {
    if (condition) {
      console.log(`  ✓ [PASS] ${testName}`);
      passed++;
    } else {
      console.error(`  ✗ [FAIL] ${testName} ${details ? '(' + details + ')' : ''}`);
      failed++;
    }
  }

  // 1. Initialize host DOM environment
  const dom = new JSDOM(fs.readFileSync(htmlPath, 'utf8'), {
    runScripts: 'dangerously',
    url: 'http://localhost:3000/courses/va-101',
    resources: 'usable'
  });

  const { window } = dom;
  const { document } = window;

  // Mock speech recognition & alert
  window.SpeechRecognition = class {
    constructor() { this.lang = 'en-US'; }
    start() {}
    stop() {}
  };
  window.alert = (msg) => { window.__lastAlert = msg; };
  window.confirm = (msg) => true;

  // Mock backend fetch API with realistic responses
  const fetchCalls = [];
  window.fetch = async (url, options = {}) => {
    fetchCalls.push({ url, options });
    const method = options.method || 'GET';

    if (url.includes('/api/v1/chat/sessions/') && method === 'POST') {
      if (url.endsWith('/messages/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            assistant_message: {
              id: 'msg-ast-101',
              sender_type: 'assistant',
              content: 'Virtual Assistant responsibilities include calendar management and email triage.',
              language: 'en',
              citations: [
                { document_title: 'VA Handbook.pdf', section: 'Chapter 1', page: 4 }
              ]
            }
          })
        };
      }
      return {
        ok: true,
        status: 201,
        json: async () => ({
          id: 'sess-test-uuid-999',
          course_id: 'course-va-101',
          institution_id: 'inst-default',
          preferred_language: 'en',
          status: 'active'
        })
      };
    }

    if (url.includes('/api/v1/accessibility/preferences/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          simple_mode: false,
          text_size: 'normal',
          high_contrast: false,
          right_to_left: false,
          voice_enabled: true,
          preferred_language: 'en'
        })
      };
    }

    return { ok: true, status: 200, json: async () => ({}) };
  };

  // Inject bridge.js script into the host window
  const scriptEl = document.createElement('script');
  scriptEl.textContent = bridgeJsSource;
  scriptEl.setAttribute('data-api', 'http://localhost:8000');
  scriptEl.setAttribute('data-course', 'course-va-101');
  scriptEl.setAttribute('data-institution', 'inst-default');
  scriptEl.setAttribute('data-lang', 'en');
  scriptEl.setAttribute('data-token', 'test-platform-context-token');
  document.body.appendChild(scriptEl);

  // Wait for DOM events & async init
  await new Promise(r => setTimeout(r, 100));

  console.log('--- Test Suite 1: Installation & Isolation ---');
  const root = document.getElementById('digital-bridge-root');
  assert(root !== null, 'Plugin root #digital-bridge-root mounted to host DOM');
  assert(root.parentNode === document.body, 'Root appended directly to body as overlay container');

  const styleEl = document.getElementById('digital-bridge-styles');
  assert(styleEl !== null, 'Scoped styles injected with id #digital-bridge-styles');
  assert(styleEl.textContent.includes('#digital-bridge-root'), 'Styles properly scoped to root element');

  // Verify host isolation
  const counterBtn = document.getElementById('host-counter-btn');
  const initialClicks = parseInt(document.getElementById('host-click-counter').textContent, 10);
  counterBtn.click();
  const postClicks = parseInt(document.getElementById('host-click-counter').textContent, 10);
  assert(postClicks === initialClicks + 1, 'Host interactive buttons and listeners work unhindered');

  const notesInput = document.getElementById('host-notes-input');
  notesInput.value = 'My notes on lesson 1';
  document.getElementById('host-save-notes-btn').click();
  assert(notesInput.value === 'My notes on lesson 1', 'Host form inputs and text areas unhindered');

  console.log('\n--- Test Suite 2: Public JavaScript API ---');
  const api = window.DigitalBridgeAssistant;
  assert(typeof api === 'object' && api !== null, 'Public window.DigitalBridgeAssistant is exposed');
  assert(typeof api.open === 'function', 'API supports open()');
  assert(typeof api.close === 'function', 'API supports close()');
  assert(typeof api.setLanguage === 'function', 'API supports setLanguage()');
  assert(typeof api.setHighContrast === 'function', 'API supports setHighContrast()');
  assert(typeof api.setSimpleMode === 'function', 'API supports setSimpleMode()');
  assert(typeof api.destroy === 'function', 'API supports destroy()');
  assert(typeof api.getState === 'function', 'API supports getState()');

  console.log('\n--- Test Suite 3: Dialog Lifecycle & Accessibility ---');
  let launcher = document.getElementById('db-launcher-btn');
  let dialog = document.getElementById('db-dialog');
  assert(dialog.classList.contains('db-hidden'), 'Dialog starts hidden before interaction');
  assert(launcher.getAttribute('aria-expanded') === 'false', 'Launcher reflects aria-expanded="false"');

  // Open dialog
  api.open();
  dialog = document.getElementById('db-dialog');
  launcher = document.getElementById('db-launcher-btn');
  assert(!dialog.classList.contains('db-hidden'), 'api.open() removes db-hidden');
  assert(launcher.getAttribute('aria-expanded') === 'true', 'Launcher reflects aria-expanded="true"');
  assert(dialog.getAttribute('role') === 'dialog', 'Dialog has role="dialog"');
  assert(dialog.getAttribute('aria-modal') === 'true', 'Dialog has aria-modal="true"');

  // Close via Escape key
  const escapeEvent = new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
  document.dispatchEvent(escapeEvent);
  dialog = document.getElementById('db-dialog');
  assert(dialog.classList.contains('db-hidden'), 'Pressing Escape key closes the dialog');

  console.log('\n--- Test Suite 4: Multilingual Support (Ethiopic & English) ---');
  api.setLanguage('am');
  launcher = document.getElementById('db-launcher-btn');
  assert(launcher.textContent.includes('ዲጂታል ብሪጅ'), 'Launcher updates label to Amharic (ዲጂታል ብሪጅ)');
  const amharicPlaceholder = document.getElementById('db-msg-input')?.placeholder || '';
  assert(amharicPlaceholder.includes('ማንኛውንም ጥያቄ'), 'Input placeholder updates to Amharic');

  api.setLanguage('en');
  launcher = document.getElementById('db-launcher-btn');
  assert(launcher.textContent.includes('Digital Bridge'), 'Launcher returns to English');

  console.log('\n--- Test Suite 5: Accessibility Modes ---');
  api.setHighContrast(true);
  assert(root.classList.contains('db-high-contrast'), 'High contrast mode adds .db-high-contrast class');
  api.setSimpleMode(true);
  assert(root.classList.contains('db-simple-mode'), 'Simple mode adds .db-simple-mode class');

  api.setHighContrast(false);
  api.setSimpleMode(false);
  assert(!root.classList.contains('db-high-contrast'), 'High contrast cleanly toggled off');
  assert(!root.classList.contains('db-simple-mode'), 'Simple mode cleanly toggled off');

  console.log('\n--- Test Suite 6: Backend API & Token Authentication ---');
  // Check that fetch was called with token
  const sessionPost = fetchCalls.find(c => c.url.includes('/api/v1/chat/sessions/') && c.options.method === 'POST');
  assert(sessionPost !== undefined, 'POST /api/v1/chat/sessions/ triggered on initialization');
  const headers = sessionPost ? sessionPost.options.headers : {};
  assert(headers['Authorization'] === 'Bearer test-platform-context-token', 'Platform context token attached in Authorization header');
  assert(headers['X-HelpBridge-Context'] === 'test-platform-context-token', 'Platform context token attached in X-HelpBridge-Context header');

  // Test sending learner message
  api.open();
  await api.sendMessage('What are the main responsibilities of a VA?');
  await new Promise(r => setTimeout(r, 100));

  const msgPost = fetchCalls.find(c => c.url.includes('/messages/') && c.options.method === 'POST');
  assert(msgPost !== undefined, 'POST /api/v1/chat/sessions/{id}/messages/ triggered when learner asks question');
  const messagesList = document.getElementById('db-messages-list');
  assert(messagesList.innerHTML.includes('VA Handbook.pdf'), 'Assistant answer rendered with evidence-grounded source citation');

  const announcer = document.getElementById('db-live-announcer');
  assert(announcer !== null, 'Polite ARIA live region (#db-live-announcer) exists for screen readers');

  console.log('\n--- Test Suite 7: Idempotency & Clean Destruction ---');
  // Multiple init calls shouldn't duplicate root
  api.init();
  const roots = document.querySelectorAll('#digital-bridge-root');
  assert(roots.length === 1, 'Calling init() repeatedly is idempotent; does not duplicate DOM');

  // Destroy widget
  api.destroy();
  assert(document.getElementById('digital-bridge-root') === null, 'api.destroy() completely removes #digital-bridge-root from DOM');
  assert(document.getElementById('digital-bridge-styles') === null, 'api.destroy() completely removes #digital-bridge-styles from DOM');

  // Re-initialize cleanly
  api.init({
    api: 'http://localhost:8000',
    course: 'course-reinit-101',
    institution: 'inst-reinit',
    lang: 'en'
  });
  assert(document.getElementById('digital-bridge-root') !== null, 'Widget can be safely re-initialized after destruction');

  console.log('\n================================================================');
  console.log(`TOTAL TESTS: ${passed + failed} | PASSED: ${passed} | FAILED: ${failed}`);
  console.log('================================================================\n');

  if (failed > 0) {
    process.exit(1);
  } else {
    process.exit(0);
  }
}

runE2ETests().catch(err => {
  console.error('Unhandled test failure:', err);
  process.exit(1);
});
