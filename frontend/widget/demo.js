'use strict';

const form = document.getElementById('widget-demo-form');
const status = document.getElementById('demo-status');

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const apiUrl = new URL(form.elements.api.value);
  if (!['http:', 'https:'].includes(apiUrl.protocol)) {
    status.textContent = 'Enter an HTTP or HTTPS API origin.';
    return;
  }

  const loader = document.createElement('script');
  loader.src = `${apiUrl.origin}/static/widget/bridge.js`;
  loader.dataset.api = apiUrl.origin;
  loader.dataset.contextToken = form.elements.token.value.trim();
  loader.dataset.lang = form.elements.language.value;
  loader.onload = () => {
    status.textContent = 'Widget loaded. The context token is held only in this page.';
    form.elements.token.value = '';
  };
  loader.onerror = () => {
    status.textContent = 'Unable to load the widget asset from the API origin.';
  };
  form.querySelector('button').disabled = true;
  document.body.appendChild(loader);
});
