(function () {
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
    return {
      apiFetch: (path, options) => apiFetch(apiRoot, path, options),
      fetchReferences: (domain, options) => fetchReferences(apiRoot, domain, options),
      fillSelect,
      requireFields,
      parseJsonField,
      setStatus: (message, tone) => setStatus(statusNode, message, tone),
      showValidation: (messages) => renderValidation(validationNode, messages).length === 0,
      clearValidation: () => renderValidation(validationNode, []),
    };
  }

  window.BraveCreator = { apiFetch, setStatus, renderValidation, fillSelect, fetchReferences, requireFields, parseJsonField, bind };
}());
