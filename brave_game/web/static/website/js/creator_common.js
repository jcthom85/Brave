(function () {
  const CREATOR_LINKS = [
    { key: 'studio', label: 'Studio', href: '/creator/' },
    { key: 'world', label: 'World', href: '/creator/world/' },
    { key: 'encounters', label: 'Encounters', href: '/creator/encounters/' },
    { key: 'systems', label: 'Systems', href: '/creator/systems/' },
    { key: 'items', label: 'Items', href: '/creator/items/' },
    { key: 'quests', label: 'Quests', href: '/creator/quests/' },
    { key: 'dialogue', label: 'Dialogue', href: '/creator/dialogue/' },
    { key: 'characters', label: 'Characters', href: '/creator/characters/' },
  ];
  const FLOW_ORDER = ['world', 'encounters', 'systems', 'items', 'quests', 'dialogue'];

  function activeCreatorKey() {
    const path = window.location.pathname;
    if (path.includes('/creator/composers/boss/')) return 'boss';
    const match = CREATOR_LINKS.find((entry) => entry.href !== '/creator/' && path.startsWith(entry.href));
    return match ? match.key : 'studio';
  }

  function injectCreatorStyles() {
    if (document.getElementById('brave-creator-shell-styles')) return;
    const style = document.createElement('style');
    style.id = 'brave-creator-shell-styles';
    style.textContent = `
      .creator-shell-nav { width:min(1680px,calc(100vw - 32px)); margin:16px auto 0; display:grid; gap:10px; }
      .creator-shell-nav__bar { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:10px; border:1px solid var(--line,#d9c8ac); border-radius:18px; background:rgba(255,249,240,.92); box-shadow:0 14px 38px rgba(29,36,48,.10); }
      .creator-shell-nav__brand { font-weight:800; letter-spacing:.04em; margin-right:8px; color:var(--ink,#1d2430); }
      .creator-shell-nav a { color:var(--ink,#1d2430); text-decoration:none; border:1px solid transparent; border-radius:999px; padding:8px 12px; }
      .creator-shell-nav a:hover,.creator-shell-nav a[aria-current="page"] { border-color:var(--accent,#8b4a29); background:#fff8f2; color:var(--accent,#8b4a29); }
      .creator-shell-nav__flow { display:flex; flex-wrap:wrap; gap:8px; align-items:center; color:var(--muted,#6b6157); font-size:.94rem; padding:0 4px; }
      .creator-shell-nav__flow a { border-color:var(--line,#d9c8ac); background:#fffdfa; }
      .creator-related-links { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
      .creator-related-links a { border:1px solid var(--line,#d9c8ac); border-radius:999px; padding:7px 10px; background:#fffdfa; color:var(--accent,#8b4a29); text-decoration:none; font-size:.92rem; }
    `;
    document.head.appendChild(style);
  }

  function attachCreatorShell() {
    if (document.querySelector('[data-creator-shell-nav]')) return null;
    injectCreatorStyles();
    const active = activeCreatorKey();
    const nav = document.createElement('nav');
    nav.className = 'creator-shell-nav';
    nav.setAttribute('data-creator-shell-nav', active);
    const linkHtml = CREATOR_LINKS.map((entry) => `<a href="${entry.href}"${entry.key === active ? ' aria-current="page"' : ''}>${entry.label}</a>`).join('');
    const activeIndex = FLOW_ORDER.indexOf(active);
    const previous = activeIndex > 0 ? CREATOR_LINKS.find((entry) => entry.key === FLOW_ORDER[activeIndex - 1]) : null;
    const next = activeIndex >= 0 && activeIndex < FLOW_ORDER.length - 1 ? CREATOR_LINKS.find((entry) => entry.key === FLOW_ORDER[activeIndex + 1]) : null;
    nav.innerHTML = [
      `<div class="creator-shell-nav__bar"><span class="creator-shell-nav__brand">Brave Creator</span>${linkHtml}<a href="/creator/composers/boss/"${active === 'boss' ? ' aria-current="page"' : ''}>Boss Composer</a></div>`,
      `<div class="creator-shell-nav__flow">${previous ? `<a href="${previous.href}">&larr; ${previous.label}</a>` : ''}<span>Authoring flow: World &rarr; Encounters &rarr; Systems &rarr; Items &rarr; Quests &rarr; Dialogue</span>${next ? `<a href="${next.href}">${next.label} &rarr;</a>` : ''}</div>`,
    ].join('');
    document.body.insertBefore(nav, document.body.firstChild);
    return nav;
  }

  function getCookie(name) {
    const prefix = `${name}=`;
    for (const part of String(document.cookie || '').split(';')) {
      const trimmed = part.trim();
      if (trimmed.startsWith(prefix)) return decodeURIComponent(trimmed.slice(prefix.length));
    }
    return '';
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function braveCreatorFetch(input, options) {
    const requestOptions = options || {};
    const method = String(requestOptions.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
      requestOptions.headers = {
        'X-CSRFToken': getCookie('csrftoken'),
        ...(requestOptions.headers || {}),
      };
    }
    return nativeFetch(input, requestOptions);
  };

  function apiFetch(apiRoot, path, options) {
    const requestOptions = options || {};
    return fetch(`${apiRoot}${path}`, {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(requestOptions.headers || {}) },
      ...requestOptions,
    }).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || `Request failed with ${response.status}`);
      }
      return payload;
    });
  }

  function attachWorkflow(apiRoot, statusNode, outputNode, validationNode) {
    if (!apiRoot || document.querySelector('[data-creator-workflow]')) return null;
    const panel = document.createElement('section');
    panel.className = 'panel creator-workflow';
    panel.setAttribute('data-creator-workflow', 'draft-first');
    panel.innerHTML = [
      '<div class="panel-head"><h2>Draft Workflow</h2><p>Browser edits save to draft packs. Validate, publish, inspect history, and revert from here.</p></div>',
      '<div class="panel-body stack">',
      '<div class="toolbar">',
      '<button id="creator-validate-draft" class="secondary" type="button">Validate Drafts</button>',
      '<button id="creator-publish-draft" type="button">Publish Drafts</button>',
      '<button id="creator-history" class="secondary" type="button">History</button>',
      '<button id="creator-revert" class="secondary" type="button">Revert Entry</button>',
      '</div>',
      '<div class="field"><label for="creator-publish-domain">Publish Domain</label><select id="creator-publish-domain"><option value="all">all</option><option value="world">world</option><option value="items">items</option><option value="quests">quests</option><option value="encounters">encounters</option><option value="dialogue">dialogue</option><option value="characters">characters</option><option value="systems">systems</option></select></div>',
      '<div class="field"><label for="creator-revert-entry">History Entry Id</label><input id="creator-revert-entry" type="text" placeholder="entry id from history"></div>',
      '</div>',
    ].join('');
    const shell = document.querySelector('[data-creator-workflow-host]') || document.querySelector('.workspace') || document.querySelector('.stack') || document.body;
    shell.appendChild(panel);

    function renderResult(payload, message, tone) {
      if (outputNode) outputNode.textContent = JSON.stringify(payload, null, 2);
      if (statusNode) setStatus(statusNode, message, tone);
      if (validationNode && payload.validation_errors) renderValidation(validationNode, payload.validation_errors);
      if (validationNode && payload.errors) renderValidation(validationNode, payload.errors);
    }

    panel.querySelector('#creator-validate-draft').addEventListener('click', async () => {
      try {
        const payload = await apiFetch(apiRoot, '/validate', { method: 'POST', body: JSON.stringify({ stage: 'draft' }) });
        renderResult(payload, payload.ok ? 'Draft validation passed.' : 'Draft validation found issues.', payload.ok ? 'good' : 'bad');
      } catch (error) {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      }
    });
    panel.querySelector('#creator-publish-draft').addEventListener('click', async () => {
      try {
        const domain = panel.querySelector('#creator-publish-domain').value;
        const payload = await apiFetch(apiRoot, '/publish', { method: 'POST', body: JSON.stringify({ domain }) });
        renderResult(payload, `Published ${payload.published.length} draft domain(s).`, 'good');
      } catch (error) {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      }
    });
    panel.querySelector('#creator-history').addEventListener('click', async () => {
      try {
        const payload = await apiFetch(apiRoot, '/history?limit=20');
        renderResult(payload, 'Loaded Creator history.', 'good');
      } catch (error) {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      }
    });
    panel.querySelector('#creator-revert').addEventListener('click', async () => {
      try {
        const entryId = panel.querySelector('#creator-revert-entry').value.trim();
        if (!entryId) throw new Error('History entry id is required.');
        const payload = await apiFetch(apiRoot, '/revert', { method: 'POST', body: JSON.stringify({ entry_id: entryId, write: true, stage: 'draft' }) });
        renderResult(payload, `Reverted ${entryId} into draft content.`, 'good');
      } catch (error) {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      }
    });
    return panel;
  }

  function setStatus(node, message, tone) {
    if (!node) return;
    node.className = 'status' + (tone ? ` ${tone}` : '');
    node.textContent = message;
  }

  function renderValidation(node, messages) {
    if (!node) return [];
    const errors = Array.isArray(messages) ? messages.filter(Boolean) : [];
    node.innerHTML = '';
    if (!errors.length) {
      node.className = 'validation-notes';
      node.hidden = true;
      return [];
    }
    node.hidden = false;
    node.className = 'validation-notes bad';
    const title = document.createElement('strong');
    title.textContent = 'Validation Notes';
    node.appendChild(title);
    const list = document.createElement('ul');
    for (const message of errors) {
      const item = document.createElement('li');
      item.textContent = message;
      list.appendChild(item);
    }
    node.appendChild(list);
    return errors;
  }

  function fillSelect(select, entries, options) {
    const config = options || {};
    const placeholder = config.placeholder || 'None';
    const includeBlank = config.includeBlank !== false;
    const selectedValue = config.selectedValue || select.value || '';
    const labelBuilder = config.labelBuilder || ((entry) => entry.label || entry.id);
    select.innerHTML = '';
    if (includeBlank) {
      const blank = document.createElement('option');
      blank.value = '';
      blank.textContent = placeholder;
      select.appendChild(blank);
    }
    for (const entry of entries || []) {
      const option = document.createElement('option');
      option.value = entry.id;
      option.textContent = labelBuilder(entry);
      if (entry.id === selectedValue) option.selected = true;
      select.appendChild(option);
    }
  }

  function fetchReferences(apiRoot, domain, options) {
    const config = options || {};
    const limit = Number(config.limit || 500);
    const query = config.query ? `&q=${encodeURIComponent(config.query)}` : '';
    return apiFetch(apiRoot, `/references/${domain}?limit=${limit}${query}`).then((payload) => payload.results || []);
  }

  function requireFields(specs) {
    return (specs || []).filter((spec) => !String(spec.value || '').trim()).map((spec) => `${spec.label} is required.`);
  }

  function parseJsonField(source, fallback, options) {
    const config = options || {};
    const label = config.label || (source && source.id) || 'field';
    const raw = typeof source === 'string' ? source.trim() : String((source && source.value) || '').trim();
    if (!raw) return fallback;
    try {
      const value = JSON.parse(raw);
      if (config.expect === 'array') {
        if (!Array.isArray(value)) throw new Error('must be a JSON array');
        return value;
      }
      if (config.expect === 'object') {
        if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('must be a JSON object');
        return value;
      }
      return value;
    } catch (error) {
      throw new Error(`${label} JSON parse error: ${error.message}`);
    }
  }

  function bind(apiRoot, statusNode, validationNode) {
    attachCreatorShell();
    const outputNode = document.getElementById('output');
    attachWorkflow(apiRoot, statusNode, outputNode, validationNode);
    return {
      apiFetch: (path, options) => apiFetch(apiRoot, path, options),
      fetchReferences: (domain, options) => fetchReferences(apiRoot, domain, options),
      fillSelect,
      requireFields,
      parseJsonField,
      setStatus: (message, tone) => setStatus(statusNode, message, tone),
      showValidation: (messages) => renderValidation(validationNode, messages).length === 0,
      clearValidation: () => renderValidation(validationNode, []),
      attachWorkflow: () => attachWorkflow(apiRoot, statusNode, outputNode, validationNode),
      attachCreatorShell,
    };
  }

  window.BraveCreator = { apiFetch, setStatus, renderValidation, fillSelect, fetchReferences, requireFields, parseJsonField, attachWorkflow, attachCreatorShell, bind };
}());
