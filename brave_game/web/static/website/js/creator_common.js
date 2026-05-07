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
      .creator-shell-nav { width:min(1680px,calc(100vw - 32px)); margin:16px auto 0; display:grid; gap:10px; }
      .creator-shell-nav__bar { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:10px; border:1px solid var(--line,#d9c8ac); border-radius:18px; background:rgba(255,249,240,.92); box-shadow:0 14px 38px rgba(29,36,48,.10); }
      .creator-shell-nav__brand { font-weight:800; letter-spacing:.04em; margin-right:8px; color:var(--ink,#1d2430); }
      .creator-shell-nav a { color:var(--ink,#1d2430); text-decoration:none; border:1px solid transparent; border-radius:999px; padding:8px 12px; }
      .creator-shell-nav a:hover,.creator-shell-nav a[aria-current="page"] { border-color:var(--accent,#8b4a29); background:#fff8f2; color:var(--accent,#8b4a29); }
      .creator-shell-nav__flow { display:flex; flex-wrap:wrap; gap:8px; align-items:center; color:var(--muted,#6b6157); font-size:.94rem; padding:0 4px; }
      .creator-shell-nav__flow a { border-color:var(--line,#d9c8ac); background:#fffdfa; }
      .creator-related-links { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
      .creator-related-links a { border:1px solid var(--line,#d9c8ac); border-radius:999px; padding:7px 10px; background:#fffdfa; color:var(--accent,#8b4a29); text-decoration:none; font-size:.92rem; }
      .creator-health-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
      .creator-health-card,.creator-incoming-card { border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:12px; display:grid; gap:6px; }
      .creator-health-card strong,.creator-incoming-card strong { display:block; }
      .creator-health-card span,.creator-incoming-card span { color:var(--muted,#6b6157); font-size:.9rem; line-height:1.35; }
      .creator-health-card.good { border-color:rgba(47,109,76,.28); background:#eef8f1; }
      .creator-health-card.bad { border-color:rgba(141,49,34,.28); background:#fff0ed; }
      .creator-incoming-card pre { display:block; min-height:90px; max-height:220px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
      .creator-agent-runs { display:grid; gap:10px; }
      .creator-agent-run-list { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
      .creator-agent-run-section { display:grid; gap:8px; grid-column:1/-1; }
      .creator-agent-run-section details { display:grid; gap:8px; }
      .creator-agent-run-section summary { cursor:pointer; font-weight:800; color:var(--ink,#1d2430); }
      .creator-agent-run-section__head { display:flex; align-items:baseline; justify-content:space-between; gap:10px; border-bottom:1px solid var(--line,#d9c8ac); padding-bottom:6px; }
      .creator-agent-run-section__head strong { color:var(--ink,#1d2430); }
      .creator-agent-run-section__grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
      .creator-agent-run-card { text-align:left; border:1px solid var(--line,#d9c8ac); border-radius:12px; background:#fffdfa; padding:12px; display:grid; gap:6px; color:var(--ink,#1d2430); cursor:pointer; font:inherit; }
      .creator-agent-run-card.is-ready { border-color:rgba(47,109,76,.36); background:#f2fbf4; }
      .creator-agent-run-card.is-blocked { border-color:rgba(141,49,34,.36); background:#fff0ed; }
      .creator-agent-run-card.is-published { opacity:.78; }
      .creator-agent-run-card.is-noop { opacity:.68; }
      .creator-agent-run-card:hover,.creator-agent-run-card[aria-current="true"] { border-color:var(--accent,#8b4a29); background:#fff8f2; }
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
    const linkHtml = CREATOR_LINKS.map((entry) => `<a href="${entry.href}"${entry.key === active ? ' aria-current="page"' : ''}>${entry.label}</a>`).join('');
    const activeIndex = FLOW_ORDER.indexOf(active);
    const previous = activeIndex > 0 ? CREATOR_LINKS.find((entry) => entry.key === FLOW_ORDER[activeIndex - 1]) : null;
    const next = activeIndex >= 0 && activeIndex < FLOW_ORDER.length - 1 ? CREATOR_LINKS.find((entry) => entry.key === FLOW_ORDER[activeIndex + 1]) : null;
    nav.innerHTML = [
      `<div class="creator-shell-nav__bar"><span class="creator-shell-nav__brand">Brave Creator</span>${linkHtml}<a href="/creator/composers/boss/"${active === 'boss' ? ' aria-current="page"' : ''}>Boss Composer</a><a href="/creator/composers/recipe/"${active === 'recipe' ? ' aria-current="page"' : ''}>Recipe Composer</a><a href="/creator/composers/fishing/"${active === 'fishing' ? ' aria-current="page"' : ''}>Fishing Composer</a></div>`,
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
      panel.innerHTML = '<div class="panel-head"><h2>Creator Health</h2><p>Draft status, validation, readiness checks, and recommended next actions.</p></div><div class="panel-body stack"><div class="creator-health-grid" data-creator-health-grid></div></div>';
      host.appendChild(panel);
    }
    const grid = panel.querySelector('[data-creator-health-grid]');
    const errors = payload.validation_errors || [];
    const draftDomains = payload.draft_domains || [];
    const issueCount = (payload.readiness || []).reduce((total, section) => total + (section.issues || []).length, 0);
    const cards = [
      { title: payload.ok ? 'Validation Clear' : 'Validation Issues', meta: errors.length ? `${errors.length} issue(s) need fixing.` : 'Draft registry validates cleanly.', tone: payload.ok ? 'good' : 'bad' },
      { title: draftDomains.length ? 'Drafts Present' : 'No Drafts', meta: draftDomains.length ? draftDomains.join(', ') : 'No draft pack files detected.', tone: draftDomains.length ? '' : 'good' },
      { title: issueCount ? 'Readiness Gaps' : 'Ready', meta: issueCount ? `${issueCount} cross-builder readiness issue(s).` : 'No readiness gaps found.', tone: issueCount ? 'bad' : 'good' },
    ];
    for (const action of payload.recommended_next_actions || []) {
      cards.push({ title: 'Next Action', meta: action.label, href: action.href, tone: '' });
    }
    grid.innerHTML = cards.map((card) => `<article class="creator-health-card ${card.tone || ''}"><strong>${card.href ? `<a href="${card.href}">${card.title}</a>` : card.title}</strong><span>${card.meta}</span></article>`).join('');
    return panel;
  }

  function summarizeRun(run) {
    const domains = (run.touched_domains || []).length ? run.touched_domains.join(', ') : 'No domains yet';
    const count = Number(run.mutation_count || 0);
    return `${run.status || 'planned'} · ${count} mutation${count === 1 ? '' : 's'} · ${domains}`;
  }

  function agentRunClass(run) {
    if (Number(run.mutation_count || 0) === 0) return 'is-noop';
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
    const ready = runs.filter((run) => run.status === 'reviewed' && Number(run.mutation_count || 0) > 0);
    const blocked = runs.filter((run) => run.status === 'publish_blocked' || run.status === 'failed');
    const active = runs.filter((run) => !['reviewed', 'publish_blocked', 'failed', 'published'].includes(run.status) && Number(run.mutation_count || 0) > 0);
    const history = runs.filter((run) => run.status === 'published' && Number(run.mutation_count || 0) > 0);
    const noops = runs.filter((run) => Number(run.mutation_count || 0) === 0);
    list.innerHTML = [
      agentRunSection('Ready To Publish', ready, { subtitle: 'Reviewed draft runs waiting for publish' }),
      agentRunSection('Needs Attention', blocked, { subtitle: 'Failed or blocked runs' }),
      agentRunSection('In Progress', active, { subtitle: 'Draft runs not reviewed yet' }),
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
      '<div class="panel-head"><h2>Agent Runs</h2><p>Review Codex-authored draft runs before using the normal Creator publish workflow.</p></div>',
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
    attachWorkflow(apiRoot, statusNode, outputNode, validationNode);
    attachAgentRunsPanel(apiRoot, statusNode);
    fetchHealth(apiRoot, 'draft')
      .then((payload) => renderHealthPanel(host, payload))
      .catch(() => {});
    return {
      apiFetch: (path, options) => apiFetch(apiRoot, path, options),
      fetchHealth: (stage) => fetchHealth(apiRoot, stage),
      renderHealthPanel: (hostNode, payload) => renderHealthPanel(hostNode || host, payload),
      fetchReferences: (domain, options) => fetchReferences(apiRoot, domain, options),
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
      attachWorkflow: () => attachWorkflow(apiRoot, statusNode, outputNode, validationNode),
      attachAgentRunsPanel: () => attachAgentRunsPanel(apiRoot, statusNode),
      attachCreatorShell,
    };
  }

  window.BraveCreator = { apiFetch, setStatus, renderValidation, fillSelect, fetchReferences, fetchHealth, renderHealthPanel, requireFields, parseJsonField, sendToBuilder, normalizeIncomingPayload, registerApplyHandler, applyIncomingPayload, consumeIncomingPayload, renderIncomingPayload, attachWorkflow, attachAgentRunsPanel, attachCreatorShell, bind };
}());
