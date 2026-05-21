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
    if (path.includes('/creator/composers/recipe/')) return 'recipe';
    if (path.includes('/creator/composers/fishing/')) return 'fishing';
    const match = CREATOR_LINKS.find((entry) => entry.href !== '/creator/' && path.startsWith(entry.href));
    return match ? match.key : 'studio';
  }

  function injectCreatorStyles() {
    if (document.getElementById('brave-creator-shell-styles')) return;
    const style = document.createElement('style');
    style.id = 'brave-creator-shell-styles';
    style.textContent = `
      :root {
        --creator-shell-height: 64px;
        --creator-shell-ink: #1e293b;
        --creator-shell-muted: #64748b;
        --creator-shell-line: #e2e8f0;
        --creator-shell-accent: #f97316;
        --creator-shell-accent-soft: #fff7ed;
      }
      body.creator-shell-has-nav {
        --ink: #1e293b;
        --accent: #f97316;
        --panel: #ffffff;
        --line: #e2e8f0;
        --muted: #64748b;
        --good: #10b981;
        --bad: #ef4444;
        --shadow: rgba(15, 23, 42, 0.08);
        font-family: "Outfit", "Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink, #1e293b);
        background:
          radial-gradient(circle at 8% 0%, rgba(249, 115, 22, 0.12), transparent 26%),
          linear-gradient(180deg, #f8fafc 0%, #fff7ed 46%, #f1f5f9 100%);
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) {
        padding-top: var(--creator-shell-height);
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .shell {
        margin-top: 24px;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .panel,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .hero,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .card,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .rail,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .section,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .section-card,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .subsection,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) details {
        border-color: var(--line, #e2e8f0);
        border-radius: 8px;
        background: var(--panel, #ffffff);
        box-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .panel-head,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .section-head,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .subsection-head {
        border-color: var(--line, #e2e8f0);
        background:
          linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 247, 237, 0.92));
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) h1,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) h2,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) h3,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) h4 {
        letter-spacing: 0;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) p,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .meta,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .field label {
        color: var(--muted, #64748b);
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) input,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) select,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) textarea,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) pre {
        border-color: var(--line, #e2e8f0);
        border-radius: 8px;
        background: #fff;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) button,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .button-link {
        border-radius: 999px;
        background: var(--accent, #f97316);
        box-shadow: 0 10px 24px rgba(249, 115, 22, 0.22);
        transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease, border-color 140ms ease;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) button:hover:not(:disabled),
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .button-link:hover {
        transform: translateY(-1px);
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) button.secondary,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .button-link.secondary,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .guide-button,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .preset-button,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .creator-agent-run-card,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .item-row,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .quest-row,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .entity-row,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .selector-row,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .room-row,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .row {
        border-color: var(--line, #e2e8f0);
        background: #fff;
        color: var(--ink, #1e293b);
        box-shadow: none;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .guide-button.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .preset-button.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .tab.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .inspector-tab.active {
        background: var(--ink, #1e293b);
        border-color: var(--ink, #1e293b);
        color: #fff;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .item-row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .item-row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .quest-row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .quest-row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .entity-row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .entity-row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .selector-row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .selector-row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .room-row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .room-row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .row:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .row.active,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .guide-button:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .preset-button:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .creator-agent-run-card:hover,
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .creator-agent-run-card[aria-current="true"] {
        border-color: rgba(249, 115, 22, 0.38);
        background: #fff7ed;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .status {
        border-color: var(--line, #e2e8f0);
        border-radius: 8px;
        background: #fff7ed;
      }
      body.creator-shell-has-nav:not(.creator-shell-fixed-workspace) .validation-notes {
        border-radius: 8px;
      }
      body.creator-shell-fixed-workspace .shell {
        top: var(--creator-shell-height) !important;
        height: calc(100vh - var(--creator-shell-height)) !important;
        grid-template-rows: calc(100vh - var(--creator-shell-height)) !important;
      }
      body.creator-shell-fixed-workspace .sidebar,
      body.creator-shell-fixed-workspace .inspector,
      body.creator-shell-fixed-workspace .main-viewport {
        height: calc(100vh - var(--creator-shell-height)) !important;
      }
      .creator-shell-nav {
        position: fixed;
        inset: 0 0 auto 0;
        z-index: 10000;
        min-height: var(--creator-shell-height);
        display: grid;
        align-items: center;
        border-bottom: 1px solid rgba(226, 232, 240, 0.92);
        background: rgba(255, 255, 255, 0.88);
        color: var(--creator-shell-ink);
        box-shadow: 0 14px 42px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(18px) saturate(160%);
      }
      .creator-shell-nav__bar {
        width: min(1760px, calc(100vw - 28px));
        min-width: 0;
        margin: 0 auto;
        display: grid;
        grid-template-columns: minmax(170px, auto) minmax(0, 1fr) auto;
        gap: 12px;
        align-items: center;
        padding: 8px 0;
      }
      .creator-shell-nav__brand {
        display: inline-grid;
        gap: 2px;
        line-height: 1.05;
        color: var(--creator-shell-ink);
        text-decoration: none;
        white-space: nowrap;
      }
      .creator-shell-nav__brand strong {
        font-size: 0.96rem;
        font-weight: 800;
        letter-spacing: 0;
      }
      .creator-shell-nav__brand span,
      .creator-shell-nav__group-label {
        color: var(--creator-shell-muted);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .creator-shell-nav__links {
        min-width: 0;
        display: flex;
        gap: 4px;
        align-items: center;
        overflow-x: auto;
        scrollbar-width: thin;
      }
      .creator-shell-nav a {
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        min-height: 34px;
        border: 1px solid transparent;
        border-radius: 999px;
        padding: 7px 10px;
        color: var(--creator-shell-ink);
        text-decoration: none;
        font-size: 0.88rem;
        font-weight: 700;
        letter-spacing: 0;
        transition: background 140ms ease, border-color 140ms ease, color 140ms ease, transform 140ms ease;
      }
      .creator-shell-nav a:hover {
        transform: translateY(-1px);
        border-color: rgba(249, 115, 22, 0.28);
        background: var(--creator-shell-accent-soft);
        color: #c2410c;
      }
      .creator-shell-nav a[aria-current="page"] {
        border-color: rgba(249, 115, 22, 0.42);
        background: var(--creator-shell-accent);
        color: #fff;
        box-shadow: 0 10px 22px rgba(249, 115, 22, 0.22);
      }
      .creator-shell-nav__menu {
        position: relative;
        justify-self: end;
      }
      .creator-shell-nav__menu summary {
        list-style: none;
        min-height: 36px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid rgba(226, 232, 240, 0.96);
        border-radius: 999px;
        padding: 7px 12px;
        background: #fff;
        color: var(--creator-shell-ink);
        cursor: pointer;
        font-size: 0.88rem;
        font-weight: 800;
        white-space: nowrap;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
      }
      .creator-shell-nav__menu summary::-webkit-details-marker {
        display: none;
      }
      .creator-shell-nav__menu summary::after {
        content: "";
        width: 7px;
        height: 7px;
        border-right: 2px solid currentColor;
        border-bottom: 2px solid currentColor;
        transform: translateY(-2px) rotate(45deg);
      }
      .creator-shell-nav__menu[open] summary {
        border-color: rgba(249, 115, 22, 0.34);
        background: var(--creator-shell-accent-soft);
        color: #c2410c;
      }
      .creator-shell-nav__menu-panel {
        position: absolute;
        top: calc(100% + 10px);
        right: 0;
        width: 220px;
        display: grid;
        gap: 6px;
        padding: 8px;
        border: 1px solid rgba(226, 232, 240, 0.96);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.98);
        box-shadow: 0 18px 42px rgba(15, 23, 42, 0.14);
      }
      .creator-shell-nav__menu-panel a {
        width: 100%;
        justify-content: flex-start;
        border-radius: 8px;
        padding: 9px 10px;
      }
      @media (max-width: 1100px) {
        :root { --creator-shell-height: 104px; }
        .creator-shell-nav__bar {
          grid-template-columns: minmax(160px, auto) auto;
          gap: 6px;
        }
        .creator-shell-nav__links {
          grid-column: 1 / -1;
          order: 3;
        }
        .creator-shell-nav__menu {
          justify-self: end;
        }
      }
      .creator-related-links { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
      .creator-related-links a { border:1px solid var(--line,#d9c8ac); border-radius:999px; padding:7px 10px; background:#fffdfa; color:var(--accent,#8b4a29); text-decoration:none; font-size:.92rem; }
      .creator-health-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
      .creator-health-card,.creator-incoming-card { border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:12px; display:grid; gap:6px; }
      .creator-health-card strong,.creator-incoming-card strong { display:block; }
      .creator-health-card span,.creator-incoming-card span { color:var(--muted,#6b6157); font-size:.9rem; line-height:1.35; }
      .creator-health-card.good { border-color:rgba(47,109,76,.28); background:#eef8f1; }
      .creator-health-card.bad { border-color:rgba(141,49,34,.28); background:#fff0ed; }
      .creator-health-actions span { display:block; margin-top:4px; }
      .creator-readiness-detail { grid-column:1/-1; border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:12px; display:grid; gap:8px; }
      .creator-readiness-detail h3 { margin:0; font-size:1rem; }
      .creator-readiness-detail ul { margin:0; padding-left:20px; display:grid; gap:5px; color:var(--muted,#6b6157); }
      .creator-readiness-detail a { color:var(--accent,#8b4a29); font-weight:700; }
      .creator-incoming-card pre { display:block; min-height:90px; max-height:220px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
      .creator-workflow details { border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:10px 12px; }
      .creator-workflow summary { cursor:pointer; font-weight:800; color:var(--ink,#1d2430); }
      .creator-workflow .field { margin-top:10px; }
      .creator-agent-runs { display:grid; gap:10px; }
      .creator-agent-run-list { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
      .creator-agent-run-section { display:grid; gap:8px; grid-column:1/-1; }
      .creator-agent-run-section details { display:grid; gap:8px; }
      .creator-agent-run-section summary { cursor:pointer; font-weight:800; color:var(--ink,#1d2430); }
      .creator-agent-run-section__head { display:flex; align-items:baseline; justify-content:space-between; gap:10px; border-bottom:1px solid var(--line,#d9c8ac); padding-bottom:6px; }
      .creator-agent-run-section__head strong { color:var(--ink,#1d2430); }
      .creator-agent-run-section__grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
      .creator-agent-run-card { text-align:left; border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fff; padding:12px; display:grid; gap:6px; color:var(--ink,#1d2430); cursor:pointer; font:inherit; }
      .creator-agent-run-card.is-ready { border-color:rgba(47,109,76,.36); box-shadow:inset 3px 0 0 rgba(47,109,76,.9); }
      .creator-agent-run-card.is-blocked { border-color:rgba(141,49,34,.36); box-shadow:inset 3px 0 0 rgba(141,49,34,.9); }
      .creator-agent-run-card.is-scratch { border-color:rgba(100,116,139,.24); box-shadow:inset 3px 0 0 rgba(100,116,139,.8); }
      .creator-agent-run-card.is-published { opacity:.78; }
      .creator-agent-run-card.is-noop { opacity:.68; }
      .creator-agent-run-card:hover,.creator-agent-run-card[aria-current="true"] { border-color:rgba(249,115,22,.38); background:#fffaf3; }
      .creator-agent-run-card strong { overflow-wrap:anywhere; }
      .creator-agent-run-card span,.creator-agent-run-meta { color:var(--muted,#6b6157); font-size:.9rem; line-height:1.35; }
      .creator-agent-run-detail { border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:12px; display:grid; gap:10px; }
      .creator-agent-run-detail pre { display:block; max-height:360px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
      .creator-agent-run-detail textarea { width:100%; min-height:74px; }
      .creator-agent-run-status { display:inline-flex; width:max-content; border:1px solid var(--line,#d9c8ac); border-radius:999px; padding:4px 8px; background:#fff; font-size:.86rem; }
      @media (max-width:980px) { .creator-health-grid { grid-template-columns:1fr; } }
      @media (max-width:980px) { .creator-agent-run-list,.creator-agent-run-section__grid { grid-template-columns:1fr; } }
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
    nav.setAttribute('aria-label', 'Creator tools');
    const linkHtml = CREATOR_LINKS.map((entry) => `<a href="${entry.href}"${entry.key === active ? ' aria-current="page"' : ''}>${entry.label}</a>`).join('');
    const composerLinks = [
      { key: 'boss', label: 'Boss Composer', href: '/creator/composers/boss/' },
      { key: 'recipe', label: 'Recipe Composer', href: '/creator/composers/recipe/' },
      { key: 'fishing', label: 'Fishing Composer', href: '/creator/composers/fishing/' },
    ].map((entry) => `<a href="${entry.href}"${entry.key === active ? ' aria-current="page"' : ''}>${entry.label}</a>`).join('');
    nav.innerHTML = `
      <div class="creator-shell-nav__bar">
        <a class="creator-shell-nav__brand" href="/creator/">
          <strong>Brave Creator Studio</strong>
        </a>
        <div class="creator-shell-nav__links">${linkHtml}</div>
        <details class="creator-shell-nav__menu">
          <summary>Composers</summary>
          <div class="creator-shell-nav__menu-panel">${composerLinks}</div>
        </details>
      </div>
    `;
    document.body.insertBefore(nav, document.body.firstChild);
    document.body.classList.add('creator-shell-has-nav');
    const shell = document.querySelector('.shell');
    if (shell && window.getComputedStyle(shell).position === 'fixed') {
      document.body.classList.add('creator-shell-fixed-workspace');
    }
    const syncShellHeight = () => {
      document.documentElement.style.setProperty('--creator-shell-height', `${Math.ceil(nav.getBoundingClientRect().height)}px`);
    };
    window.requestAnimationFrame(syncShellHeight);
    window.addEventListener('resize', syncShellHeight);
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
        const error = new Error(payload.error || `Request failed with ${response.status}`);
        error.payload = payload;
        throw error;
      }
      return payload;
    });
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[char]));
  }

  function attachWorkflow(apiRoot, statusNode, outputNode, validationNode, hostNode) {
    if (!apiRoot || document.querySelector('[data-creator-workflow]')) return null;
    const shell = hostNode || document.querySelector('[data-creator-actions-host]');
    if (!shell) return null;
    const panel = document.createElement('section');
    panel.className = 'panel creator-workflow';
    panel.setAttribute('data-creator-workflow', 'draft-first');
    panel.innerHTML = [
      '<div class="panel-head"><h2>Draft Actions</h2><p>Validate first. Use Publish Drafts only when the draft domains listed below are the exact content you want live.</p></div>',
      '<div class="panel-body stack">',
      '<div class="toolbar">',
      '<button id="creator-validate-draft" class="secondary" type="button">Validate Drafts</button>',
      '<button id="creator-publish-draft" type="button">Publish Drafts</button>',
      '</div>',
      '<div class="field"><label for="creator-publish-domain">Publish Domain</label><select id="creator-publish-domain"><option value="all">all reviewed draft domains</option><option value="world">world</option><option value="items">items</option><option value="quests">quests</option><option value="encounters">encounters</option><option value="dialogue">dialogue</option><option value="characters">characters</option><option value="systems">systems</option></select></div>',
      '<details>',
      '<summary>History and Revert Tools</summary>',
      '<div class="toolbar">',
      '<button id="creator-history" class="secondary" type="button">History</button>',
      '<button id="creator-revert" class="secondary" type="button">Revert Entry</button>',
      '</div>',
      '<div class="field"><label for="creator-revert-entry">History Entry Id</label><input id="creator-revert-entry" type="text" placeholder="entry id from history"></div>',
      '</details>',
      '</div>',
    ].join('');
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

  function fetchHealth(apiRoot, stage) {
    return apiFetch(apiRoot, `/health?stage=${encodeURIComponent(stage || 'draft')}`);
  }

  function renderHealthPanel(host, payload) {
    if (!host) return null;
    let panel = host.querySelector('[data-creator-health-panel]');
    if (!panel) {
      panel = document.createElement('section');
      panel.className = 'panel creator-health';
      panel.setAttribute('data-creator-health-panel', 'true');
      panel.innerHTML = '<div class="panel-head"><h2>Draft Health</h2><p>Shows whether draft content validates and what still needs cleanup before the game is fully tidy.</p></div><div class="panel-body stack"><div class="creator-health-grid" data-creator-health-grid></div></div>';
      host.appendChild(panel);
    }
    const grid = panel.querySelector('[data-creator-health-grid]');
    const errors = payload.validation_errors || [];
    const draftDomains = payload.draft_domains || [];
    const issueCount = (payload.readiness || []).reduce((total, section) => total + (section.issues || []).length, 0);
    const cards = [
      { title: payload.ok ? 'Validation Clear' : 'Validation Issues', meta: errors.length ? `${errors.length} issue(s) need fixing.` : 'Draft registry validates cleanly.', tone: payload.ok ? 'good' : 'bad' },
      { title: draftDomains.length ? 'Draft Domains' : 'No Drafts', meta: draftDomains.length ? draftDomains.join(', ') : 'No draft pack files detected.', tone: draftDomains.length ? '' : 'good' },
      { title: issueCount ? 'Readiness Gaps' : 'Ready', meta: issueCount ? `${issueCount} cross-builder readiness issue(s).` : 'No readiness gaps found.', tone: issueCount ? 'bad' : 'good' },
    ];
    const actions = payload.recommended_next_actions || [];
    if (actions.length) {
      cards.push({
        title: 'Recommended Cleanup',
        meta: actions.slice(0, 4).map((action) => action.label).join('\n'),
        href: actions[0].href,
        tone: '',
      });
    }
    const readinessDetails = (payload.readiness || [])
      .map((section) => {
        const issues = section.issues || [];
        if (!issues.length) return '';
        const title = section.label || section.key || 'Readiness';
        const href = section.href || '#';
        const items = issues.map((issue) => `<li>${escapeHtml(issue.message || issue)}</li>`).join('');
        return `<section><h3><a href="${escapeHtml(href)}">${escapeHtml(title)}</a></h3><ul>${items}</ul></section>`;
      })
      .filter(Boolean)
      .join('');
    const detailHtml = readinessDetails
      ? `<article class="creator-readiness-detail"><h3>Readiness Issues</h3>${readinessDetails}</article>`
      : '';
    grid.innerHTML = cards.map((card) => `<article class="creator-health-card ${card.tone || ''} ${card.title === 'Recommended Cleanup' ? 'creator-health-actions' : ''}"><strong>${card.href ? `<a href="${card.href}">${card.title}</a>` : card.title}</strong>${escapeHtml(card.meta).split('\n').map((line) => `<span>${line}</span>`).join('')}</article>`).join('') + detailHtml;
    return panel;
  }

  function summarizeRun(run) {
    const domains = (run.touched_domains || []).length ? run.touched_domains.join(', ') : 'No domains yet';
    const count = Number(run.mutation_count || 0);
    return `${run.status || 'planned'} · ${count} mutation${count === 1 ? '' : 's'} · ${domains}`;
  }

  function isScratchRun(run) {
    const text = `${run.run_id || ''} ${run.instructions || ''}`.toLowerCase();
    return text.includes('test') || text.includes('do not publish') || text.includes('disposable') || text.includes('smoke test');
  }

  function agentRunClass(run) {
    if (Number(run.mutation_count || 0) === 0) return 'is-noop';
    if (isScratchRun(run)) return 'is-scratch';
    if (run.status === 'reviewed') return 'is-ready';
    if (run.status === 'publish_blocked' || run.status === 'failed') return 'is-blocked';
    if (run.status === 'published') return 'is-published';
    return '';
  }

  function agentRunCard(run) {
    const classes = ['creator-agent-run-card', agentRunClass(run)].filter(Boolean).join(' ');
    return [
      `<button type="button" class="${classes}" data-agent-run-id="${escapeHtml(run.run_id)}">`,
      `<strong>${escapeHtml(run.instructions || run.run_id)}</strong>`,
      `<span>${escapeHtml(summarizeRun(run))}</span>`,
      `<span>Updated ${escapeHtml(run.updated_at || '-')}</span>`,
      '</button>',
    ].join('');
  }

  function agentRunSection(title, runs, options) {
    const config = options || {};
    if (!runs.length) return '';
    const subtitle = config.subtitle ? `<span class="creator-agent-run-meta">${escapeHtml(config.subtitle)}</span>` : '';
    const grid = `<div class="creator-agent-run-section__grid">${runs.map(agentRunCard).join('')}</div>`;
    const heading = `<div class="creator-agent-run-section__head"><strong>${escapeHtml(title)}</strong>${subtitle}</div>`;
    if (config.collapsed) {
      return `<section class="creator-agent-run-section"><details><summary>${escapeHtml(title)} (${runs.length})</summary>${grid}</details></section>`;
    }
    return `<section class="creator-agent-run-section">${heading}${grid}</section>`;
  }

  function runBuilderLinks(run) {
    const domains = run.touched_domains || [];
    const links = {
      world: '/creator/world/',
      encounters: '/creator/encounters/',
      systems: '/creator/systems/',
      items: '/creator/items/',
      quests: '/creator/quests/',
      dialogue: '/creator/dialogue/',
      characters: '/creator/characters/',
    };
    return domains.filter((domain) => links[domain]).map((domain) => `<a href="${links[domain]}">${escapeHtml(domain)}</a>`).join('');
  }

  function renderAgentRunDetail(panel, apiRoot, run, statusNode) {
    const detail = panel.querySelector('[data-agent-run-detail]');
    const summary = {
      run_id: run.run_id,
      status: run.status,
      instructions: run.instructions,
      plan: run.plan,
      validation: run.validation,
      dry_run: run.dry_run,
      apply: run.apply,
      verify: run.verify,
      publish: run.publish,
      review_notes: run.review_notes || [],
    };
    const publishMessage = run.status === 'reviewed'
      ? '<div class="creator-agent-run-meta">Reviewed means approved for draft publishing. Use Publish Run Drafts to promote this run&apos;s touched draft domains.</div>'
      : '';
    detail.innerHTML = [
      `<article class="creator-agent-run-detail"><div><strong>${escapeHtml(run.instructions || run.run_id)}</strong><div class="creator-agent-run-meta">${escapeHtml(run.run_id)} · updated ${escapeHtml(run.updated_at || '-')}</div></div>`,
      `<span class="creator-agent-run-status">${escapeHtml(run.status || 'planned')}</span>`,
      publishMessage,
      `<div class="creator-related-links">${runBuilderLinks(run) || '<span class="creator-agent-run-meta">No builder links yet.</span>'}</div>`,
      `<pre>${escapeHtml(JSON.stringify(summary, null, 2))}</pre>`,
      '<label for="creator-agent-run-review-note">Review Note</label>',
      '<textarea id="creator-agent-run-review-note" data-agent-run-review-note placeholder="What did you verify?"></textarea>',
      '<div class="toolbar"><button type="button" data-agent-run-review>Mark Reviewed</button><button type="button" data-agent-run-publish>Publish Run Drafts</button></div>',
      '</article>',
    ].join('');
    detail.querySelector('[data-agent-run-review]').addEventListener('click', async () => {
      try {
        const note = detail.querySelector('[data-agent-run-review-note]').value.trim();
        if (!note) throw new Error('Review note is required.');
        const payload = await apiFetch(apiRoot, `/codex/runs/${encodeURIComponent(run.run_id)}/review`, { method: 'POST', body: JSON.stringify({ note }) });
        renderAgentRunDetail(panel, apiRoot, payload.run, statusNode);
        if (statusNode) setStatus(statusNode, 'Agent run marked reviewed.', 'good');
      } catch (error) {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      }
    });
    detail.querySelector('[data-agent-run-publish]').addEventListener('click', async () => {
      try {
        const payload = await apiFetch(apiRoot, `/codex/runs/${encodeURIComponent(run.run_id)}/publish`, { method: 'POST', body: JSON.stringify({}) });
        renderAgentRunDetail(panel, apiRoot, payload.run, statusNode);
        await loadAgentRuns(panel, apiRoot, statusNode);
        if (statusNode) setStatus(statusNode, `Published ${payload.published.length} draft domain(s) for this agent run.`, 'good');
      } catch (error) {
        if (error.payload && error.payload.run) renderAgentRunDetail(panel, apiRoot, error.payload.run, statusNode);
        const details = error.payload && (error.payload.validation_errors || []).length ? ` ${error.payload.validation_errors.join(' ')}` : '';
        if (statusNode) setStatus(statusNode, `${error.message}${details}`, 'bad');
      }
    });
  }

  async function loadAgentRuns(panel, apiRoot, statusNode) {
    const list = panel.querySelector('[data-agent-run-list]');
    const payload = await apiFetch(apiRoot, '/codex/runs?limit=20');
    const runs = payload.runs || [];
    if (!runs.length) {
      list.innerHTML = '<div class="creator-agent-run-meta">No agent runs yet.</div>';
      panel.querySelector('[data-agent-run-detail]').innerHTML = '';
      return;
    }
    const scratch = runs.filter((run) => isScratchRun(run) && run.status !== 'published' && Number(run.mutation_count || 0) > 0);
    const ready = runs.filter((run) => !isScratchRun(run) && run.status === 'reviewed' && Number(run.mutation_count || 0) > 0);
    const blocked = runs.filter((run) => run.status === 'publish_blocked' || run.status === 'failed');
    const active = runs.filter((run) => !isScratchRun(run) && !['reviewed', 'publish_blocked', 'failed', 'published'].includes(run.status) && Number(run.mutation_count || 0) > 0);
    const history = runs.filter((run) => run.status === 'published' && Number(run.mutation_count || 0) > 0);
    const noops = runs.filter((run) => Number(run.mutation_count || 0) === 0);
    list.innerHTML = [
      agentRunSection('Ready To Publish', ready, { subtitle: 'Reviewed draft runs waiting for publish' }),
      agentRunSection('Needs Attention', blocked, { subtitle: 'Failed or blocked runs' }),
      agentRunSection('In Progress', active, { subtitle: 'Draft runs not reviewed yet' }),
      agentRunSection('Scratch / Test Runs', scratch, { subtitle: 'Smoke-test or disposable runs; usually leave these unpublished', collapsed: true }),
      agentRunSection('Published History', history, { collapsed: true }),
      agentRunSection('No-Op / Scratch Runs', noops, { collapsed: true }),
    ].join('') || '<div class="creator-agent-run-meta">No matching agent runs.</div>';
    list.querySelectorAll('[data-agent-run-id]').forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          list.querySelectorAll('[aria-current="true"]').forEach((entry) => entry.removeAttribute('aria-current'));
          button.setAttribute('aria-current', 'true');
          const detailPayload = await apiFetch(apiRoot, `/codex/runs/${encodeURIComponent(button.getAttribute('data-agent-run-id'))}`);
          renderAgentRunDetail(panel, apiRoot, detailPayload.run, statusNode);
        } catch (error) {
          if (statusNode) setStatus(statusNode, error.message, 'bad');
        }
      });
    });
  }

  function attachAgentRunsPanel(apiRoot, statusNode) {
    if (!apiRoot || document.querySelector('[data-creator-agent-runs-panel]')) return null;
    const host = document.querySelector('[data-creator-agent-runs-host]');
    if (!host) return null;
    const panel = document.createElement('section');
    panel.className = 'rail creator-agent-runs';
    panel.setAttribute('data-creator-agent-runs-panel', 'true');
    panel.innerHTML = [
      '<div class="panel-head"><h2>Agent Runs</h2><p>This is an audit queue for Codex-authored draft batches. Open a run, check what it changed, add a review note if it is intentional, then publish only reviewed runs. Scratch and TEST runs stay collapsed.</p></div>',
      '<div class="toolbar"><button type="button" data-agent-runs-refresh>Refresh</button></div>',
      '<div class="creator-agent-run-list" data-agent-run-list></div>',
      '<div data-agent-run-detail></div>',
    ].join('');
    host.appendChild(panel);
    panel.querySelector('[data-agent-runs-refresh]').addEventListener('click', () => {
      loadAgentRuns(panel, apiRoot, statusNode).catch((error) => {
        if (statusNode) setStatus(statusNode, error.message, 'bad');
      });
    });
    loadAgentRuns(panel, apiRoot, statusNode).catch(() => {});
    return panel;
  }

  function builderKeyFromPath(path) {
    const value = String(path || '');
    if (value.includes('/creator/world/')) return 'world';
    if (value.includes('/creator/encounters/')) return 'encounters';
    if (value.includes('/creator/systems/')) return 'systems';
    if (value.includes('/creator/items/')) return 'items';
    if (value.includes('/creator/quests/')) return 'quests';
    if (value.includes('/creator/dialogue/')) return 'dialogue';
    if (value.includes('/creator/characters/')) return 'characters';
    return 'studio';
  }

  function normalizeIncomingPayload(path, payload, label, options) {
    const config = options || {};
    return {
      source_builder: config.source_builder || activeCreatorKey(),
      target_builder: config.target_builder || builderKeyFromPath(path),
      kind: config.kind || 'generic',
      label: label || config.label || 'Incoming Payload',
      payload: payload || {},
      created_at: new Date().toISOString(),
    };
  }

  function sendToBuilder(path, payload, label, options) {
    const entry = normalizeIncomingPayload(path, payload, label, options);
    window.sessionStorage.setItem('braveCreatorIncomingPayload', JSON.stringify(entry));
    window.location.href = path;
  }

  function consumeIncomingPayload() {
    const raw = window.sessionStorage.getItem('braveCreatorIncomingPayload');
    if (!raw) return null;
    window.sessionStorage.removeItem('braveCreatorIncomingPayload');
    try { return JSON.parse(raw); }
    catch (_error) { return null; }
  }

  function renderIncomingPayload(host, incoming, statusNode) {
    if (!host || !incoming) return null;
    const panel = document.createElement('section');
    panel.className = 'panel creator-incoming';
    panel.setAttribute('data-creator-incoming-payload-panel', 'true');
    const meta = `${incoming.source_builder || 'builder'} -> ${incoming.target_builder || 'builder'}${incoming.kind ? ` · ${incoming.kind}` : ''}`;
    panel.innerHTML = [
      '<div class="panel-head"><h2>Incoming Payload</h2><p>A linked builder sent this here. Applying it updates this form only; Preview or Save remains explicit.</p></div>',
      '<div class="panel-body stack">',
      `<article class="creator-incoming-card"><strong>${incoming.label || 'Incoming Payload'}</strong><span>${meta}. Payload is staged only; nothing was written.</span><pre>${JSON.stringify(incoming.payload || {}, null, 2)}</pre><div class="toolbar"><button type="button" data-apply-incoming-payload>Apply To Builder</button><button class="secondary" type="button" data-copy-incoming-payload>Copy Payload</button></div></article>`,
      '</div>',
    ].join('');
    panel.querySelector('[data-apply-incoming-payload]').addEventListener('click', () => {
      const applied = applyIncomingPayload(incoming);
      if (!applied && statusNode) setStatus(statusNode, `No apply handler for ${incoming.kind || 'this payload'} on this builder.`, 'bad');
    });
    panel.querySelector('[data-copy-incoming-payload]').addEventListener('click', () => {
      const text = JSON.stringify(incoming.payload || {}, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text);
      if (statusNode) setStatus(statusNode, 'Incoming payload copied.', 'good');
    });
    host.insertBefore(panel, host.firstChild);
    return panel;
  }

  function registerApplyHandler(kind, handler) {
    window.BraveCreatorApplyHandlers = window.BraveCreatorApplyHandlers || {};
    window.BraveCreatorApplyHandlers[kind] = handler;
  }

  function applyIncomingPayload(incoming) {
    if (!incoming) return false;
    const direct = window.BraveCreatorApplyIncomingPayload;
    if (typeof direct === 'function') return direct(incoming) !== false;
    const handlers = window.BraveCreatorApplyHandlers || {};
    const handler = handlers[incoming.kind];
    if (typeof handler !== 'function') return false;
    handler(incoming);
    return true;
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

  function fetchInspiration(apiRoot, kind, context) {
    return apiFetch(apiRoot, '/codex/inspire', { method: 'POST', body: JSON.stringify({ kind, context }) }).then((payload) => payload.inspiration);
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
    const host = document.querySelector('[data-creator-workflow-host]') || document.querySelector('.workspace') || document.querySelector('.stack') || document.body;
    const incoming = consumeIncomingPayload();
    renderIncomingPayload(host, incoming, statusNode);
    const actionsHost = document.querySelector('[data-creator-actions-host]');
    if (actionsHost) attachWorkflow(apiRoot, statusNode, outputNode, validationNode, actionsHost);
    attachAgentRunsPanel(apiRoot, statusNode);
    fetchHealth(apiRoot, 'draft')
      .then((payload) => renderHealthPanel(host, payload))
      .catch(() => {});
    return {
      apiFetch: (path, options) => apiFetch(apiRoot, path, options),
      fetchHealth: (stage) => fetchHealth(apiRoot, stage),
      renderHealthPanel: (hostNode, payload) => renderHealthPanel(hostNode || host, payload),
      fetchReferences: (domain, options) => fetchReferences(apiRoot, domain, options),
      fetchInspiration: (kind, context) => fetchInspiration(apiRoot, kind, context),
      fillSelect,
      requireFields,
      parseJsonField,
      sendToBuilder,
      registerApplyHandler,
      applyIncomingPayload,
      consumeIncomingPayload,
      renderIncomingPayload: (hostNode, payload) => renderIncomingPayload(hostNode || host, payload, statusNode),
      setStatus: (message, tone) => setStatus(statusNode, message, tone),
      showValidation: (messages) => renderValidation(validationNode, messages).length === 0,
      clearValidation: () => renderValidation(validationNode, []),
      attachWorkflow: (hostNode) => attachWorkflow(apiRoot, statusNode, outputNode, validationNode, hostNode),
      attachAgentRunsPanel: () => attachAgentRunsPanel(apiRoot, statusNode),
      attachCreatorShell,
    };
  }

  window.BraveCreator = { apiFetch, setStatus, renderValidation, fillSelect, fetchReferences, fetchHealth, renderHealthPanel, fetchInspiration, requireFields, parseJsonField, sendToBuilder, normalizeIncomingPayload, registerApplyHandler, applyIncomingPayload, consumeIncomingPayload, renderIncomingPayload, attachWorkflow, attachAgentRunsPanel, attachCreatorShell, bind };
}());
