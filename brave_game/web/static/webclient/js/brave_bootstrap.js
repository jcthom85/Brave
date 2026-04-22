(function () {
    "use strict";

    var LAYOUT_KEY = "evenniaGoldenLayoutSavedState";
    var LAYOUT_NAME_KEY = "evenniaGoldenLayoutSavedStateName";
    var BLOCKED_COMPONENTS = {
        iframe: true,
        options: true,
    };

    function cloneConfig(config) {
        return JSON.parse(JSON.stringify(config));
    }

    function sanitizeNode(node) {
        if (!node || typeof node !== "object") {
            return null;
        }

        if (node.type === "component" && BLOCKED_COMPONENTS[node.componentName]) {
            return null;
        }

        var sanitized = Array.isArray(node) ? [] : {};

        Object.keys(node).forEach(function (key) {
            if (key === "content" && Array.isArray(node.content)) {
                sanitized.content = node.content
                    .map(sanitizeNode)
                    .filter(function (entry) {
                        return !!entry;
                    });
            } else {
                sanitized[key] = node[key];
            }
        });

        if (
            (sanitized.type === "row" || sanitized.type === "column" || sanitized.type === "stack") &&
            (!sanitized.content || sanitized.content.length === 0)
        ) {
            return null;
        }

        return sanitized;
    }

    function collectComponentNames(node, names) {
        if (!node || typeof node !== "object") {
            return;
        }

        if (node.type === "component" && node.componentName) {
            names[node.componentName] = true;
        }

        if (Array.isArray(node.content)) {
            node.content.forEach(function (child) {
                collectComponentNames(child, names);
            });
        }
    }

    function hasRequiredLayout(config) {
        var names = {};
        collectComponentNames(config, names);
        return !!(names.Main && names.input);
    }

    function isMobileViewport() {
        return !!(window.matchMedia && window.matchMedia("(max-width: 900px)").matches);
    }

    function rewriteCanonicalInputLayout(node) {
        if (!node || typeof node !== "object") {
            return;
        }

        if (node.type === "component" && node.id === "inputComponent") {
            node.height = 0;
            node.minHeight = 0;
        } else if (node.type === "component" && node.componentName === "Main") {
            node.height = 100;
        }

        if (Array.isArray(node.content)) {
            node.content.forEach(rewriteCanonicalInputLayout);
        }
    }

    function normalizeLayoutForViewport() {
        if (!window.goldenlayout_config) {
            return;
        }
        rewriteCanonicalInputLayout(window.goldenlayout_config);
    }

    function resetToDefaultLayout() {
        if (!window.localStorage || !window.goldenlayout_config) {
            return;
        }

        window.localStorage.setItem(LAYOUT_KEY, JSON.stringify(cloneConfig(window.goldenlayout_config)));
        window.localStorage.setItem(LAYOUT_NAME_KEY, "default");
    }

    function sanitizeSavedLayout() {
        if (!window.localStorage || !window.goldenlayout_config) {
            return;
        }

        normalizeLayoutForViewport();

        // Brave uses a fixed browser-first shell. Persisted GoldenLayout state
        // is more likely to strand users in a broken or invisible layout than
        // to provide useful customization, so always restore the canonical
        // layout on boot.
        resetToDefaultLayout();
    }

    function lockRootScrolling() {
        var html = document.documentElement;
        var body = document.body;
        var scroller = document.scrollingElement || html;
        var viewportHeight = window.innerHeight + "px";
        var viewportWidth = window.innerWidth + "px";
        if (!html || !body) {
            return;
        }

        [html, body, scroller].forEach(function (el) {
            if (!el) {
                return;
            }
            el.style.setProperty("overflow", "hidden", "important");
            el.style.setProperty("overflow-x", "hidden", "important");
            el.style.setProperty("overflow-y", "hidden", "important");
            el.style.setProperty("scrollbar-width", "none", "important");
            el.style.setProperty("width", viewportWidth, "important");
            el.style.setProperty("min-width", viewportWidth, "important");
            el.style.setProperty("max-width", viewportWidth, "important");
            el.style.setProperty("height", viewportHeight, "important");
            el.style.setProperty("min-height", viewportHeight, "important");
            el.style.setProperty("max-height", viewportHeight, "important");
        });

        window.scrollTo(0, 0);
        if (scroller) {
            scroller.scrollTop = 0;
            scroller.scrollLeft = 0;
        }
    }

    if (window.history && "scrollRestoration" in window.history) {
        window.history.scrollRestoration = "manual";
    }

    sanitizeSavedLayout();
    lockRootScrolling();
    window.addEventListener("resize", lockRootScrolling);
    window.addEventListener("load", lockRootScrolling);
    document.addEventListener("DOMContentLoaded", lockRootScrolling);
})();
