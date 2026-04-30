/*
 *
 * Brave override of Evennia's default input plugin.
 *
 * Main behavior changes:
 * - Keep the command input focused after sending.
 * - Preserve the first typed character if the input was not focused.
 * - Refocus the command line on window return and output clicks.
 *
 */
let defaultInPlugin = (function () {
    "use strict";

    var MOBILE_INPUT_OPEN_CLASS = "brave-mobile-input-open";
    var INPUT_MODE_STORAGE_KEY = "brave.webclient.playInputMode";
    var INPUT_MODE_CHAT = "chat";
    var INPUT_MODE_COMMAND = "command";
    var INPUT_CONTEXT_PLAY = "play";
    var INPUT_CONTEXT_COMMAND = "command";
    var focusOnKeydown = true;
    var placeholderByMode = {
        chat: "Say something nearby. Prefix with / to send a command.",
        command: "Type a command. Try: map, n, e, sheet, talk mira, fight",
    };
    var playInputMode = INPUT_MODE_CHAT;
    var inputContext = INPUT_CONTEXT_COMMAND;
    var isLoggedIn = false;
    var lastMobileInputOpenAt = 0;
    var pendingOverlayFocusTimeout = null;
    var pendingChatPrefix = "";
    var pendingChatPrompt = "";
    var isMobileViewport = function () {
        return !!(window.matchMedia && window.matchMedia("(max-width: 900px)").matches);
    };

    var getDefaultOutPlugin = function () {
        if (!window.plugins || !window.plugins.defaultout) {
            return null;
        }
        return window.plugins.defaultout;
    };

    var getResolvedInputContext = function () {
        return inputContext;
    };

    var syncOverlayBackdrop = function (open) {
        var backdrop = document.getElementById("brave-chat-overlay-backdrop");
        if (!backdrop) {
            return;
        }
        backdrop.setAttribute("aria-hidden", open ? "false" : "true");
    };

    var clearPendingOverlayFocus = function () {
        if (pendingOverlayFocusTimeout !== null) {
            window.clearTimeout(pendingOverlayFocusTimeout);
            pendingOverlayFocusTimeout = null;
        }
    };

    var clearChatDraft = function () {
        pendingChatPrefix = "";
        pendingChatPrompt = "";
    };

    var getChatPlaceholder = function () {
        if (pendingChatPrompt) {
            return pendingChatPrompt;
        }
        return placeholderByMode.chat;
    };

    var getEffectiveInputMode = function () {
        return getResolvedInputContext() === INPUT_CONTEXT_COMMAND ? INPUT_MODE_COMMAND : INPUT_MODE_CHAT;
    };

    var syncInputModeBodyState = function () {
        if (!document.body) {
            return;
        }
        var resolvedContext = getResolvedInputContext();
        document.body.setAttribute("data-brave-input-mode", getEffectiveInputMode());
        document.body.setAttribute("data-brave-input-context", resolvedContext);
    };

    var dispatchInputModeChange = function () {
        syncInputModeBodyState();
        window.dispatchEvent(new CustomEvent("brave:input-mode-change", {
            detail: {
                mode: getEffectiveInputMode(),
                context: inputContext,
            },
        }));
    };

    var getGoldenLayoutInstance = function () {
        if (!window.plugins || !window.plugins.goldenlayout || typeof window.plugins.goldenlayout.getGL !== "function") {
            return null;
        }
        return window.plugins.goldenlayout.getGL();
    };

    var getLayoutItemElement = function (item) {
        if (!item || !item.element) {
            return null;
        }
        return item.element[0] || item.element;
    };

    var collapseInputLayoutReservation = function (layout, inputComponent, sibling, inputElement, siblingElement) {
        var needsUpdate = false;
        if (inputComponent && inputComponent.config) {
            if (inputComponent.config.height !== 0) {
                inputComponent.config.height = 0;
                needsUpdate = true;
            }
            if (inputComponent.config.minHeight !== 0) {
                inputComponent.config.minHeight = 0;
                needsUpdate = true;
            }
        }
        if (sibling && sibling.config && sibling.config.height !== 100) {
            sibling.config.height = 100;
            needsUpdate = true;
        }
        if (inputElement) {
            inputElement.style.height = "0px";
            inputElement.style.minHeight = "0px";
            inputElement.style.maxHeight = "0px";
            inputElement.style.flexBasis = "0px";
        }
        if (siblingElement) {
            siblingElement.style.height = "100%";
            siblingElement.style.minHeight = "0px";
            siblingElement.style.flexBasis = "auto";
            siblingElement.style.flexGrow = "1";
        }
        if (needsUpdate && layout && typeof layout.updateSize === "function") {
            window.requestAnimationFrame(function () {
                layout.updateSize();
            });
        }
    };

    var decorateInputLayoutShells = function () {
        var layout = getGoldenLayoutInstance();
        if (!layout || !layout.root || typeof layout.root.getItemsByType !== "function") {
            return;
        }

        var components = layout.root.getItemsByType("component") || [];
        var inputComponent = null;
        for (var i = 0; i < components.length; i += 1) {
            if (components[i] && typeof components[i].hasId === "function" && components[i].hasId("inputComponent")) {
                inputComponent = components[i];
                break;
            }
        }
        if (!inputComponent) {
            return;
        }

        var inputElement = getLayoutItemElement(inputComponent);
        var parentElement = getLayoutItemElement(inputComponent.parent);
        var sibling = null;
        if (inputComponent.parent && Array.isArray(inputComponent.parent.contentItems)) {
            for (var j = 0; j < inputComponent.parent.contentItems.length; j += 1) {
                var candidate = inputComponent.parent.contentItems[j];
                if (candidate !== inputComponent) {
                    sibling = candidate;
                    break;
                }
            }
        }
        var siblingElement = getLayoutItemElement(sibling);

        if (parentElement) {
            parentElement.classList.add("brave-gl-input-column");
        }
        if (inputElement) {
            inputElement.classList.add("brave-gl-input-item");
            if (inputElement.previousElementSibling && inputElement.previousElementSibling.classList.contains("lm_splitter")) {
                inputElement.previousElementSibling.classList.add("brave-gl-input-splitter");
            }
            if (inputElement.nextElementSibling && inputElement.nextElementSibling.classList.contains("lm_splitter")) {
                inputElement.nextElementSibling.classList.add("brave-gl-input-splitter");
            }
        }
        if (siblingElement) {
            siblingElement.classList.add("brave-gl-main-item");
        }
        collapseInputLayoutReservation(layout, inputComponent, sibling, inputElement, siblingElement);
    };

    var getCommandInput = function () {
        var inputfield = $(".inputfield:focus");
        if (inputfield.length < 1) {
            inputfield = $("#inputfield:focus");
        }
        if (inputfield.length < 1) {
            inputfield = $(".inputfield.focused");
        }
        if (inputfield.length < 1) {
            inputfield = $(".inputfield:last");
        }
        if (inputfield.length < 1) {
            inputfield = $("#inputfield");
        }
        return inputfield.first();
    };

    var isMobileInputOpen = function () {
        return !!(document.body && document.body.classList.contains(MOBILE_INPUT_OPEN_CLASS));
    };

    var isCommandInput = function (target) {
        return $(target).closest(".inputfieldwrapper, #inputcontrol, .inputwrap").length > 0
            || $(target).is(".inputfield, #inputfield");
    };

    var isInteractiveTarget = function (target) {
        return $(target).closest(
            "input, textarea, select, button, a, label, [contenteditable='true'], .dialog, .goldenlayout-options-ui, .lm_header"
        ).length > 0;
    };

    var hasSelection = function () {
        if (!window.getSelection) {
            return false;
        }
        return window.getSelection().toString().length > 0;
    };

    var playUiSound = function (kind) {
        if (window.BraveAudio && typeof window.BraveAudio.handleUiAction === "function") {
            window.BraveAudio.handleUiAction(kind || "click");
        }
    };

    var setReadyState = function (activeOverride) {
        var inputAvailable = getResolvedInputContext() === INPUT_CONTEXT_PLAY;
        var focused = inputAvailable && $(".inputfield:focus, #inputfield:focus").length > 0;
        var active = activeOverride;
        if (!inputAvailable) {
            active = false;
        } else if (active === undefined || active === null) {
            active = focused;
        }

        var inputfield = inputAvailable ? getCommandInput() : $();
        var hasText = !!(inputAvailable && inputfield.length && String(inputfield.val() || "").length);

        $("body").toggleClass("brave-command-ready", !!active);
        $("body").toggleClass("brave-command-armed", !!active && isMobileViewport() && !focused);
        $("body").toggleClass("brave-command-has-text", hasText);
        $(".inputfield, #inputfield").toggleClass("focused", !!active && inputAvailable);
        syncInputModeBodyState();
    };

    var buildInputModeBarMarkup = function () {
        var effectiveMode = getEffectiveInputMode();
        var resolvedContext = getResolvedInputContext();
        var chatActive = effectiveMode === INPUT_MODE_CHAT ? " brave-input-modebar__button--active" : "";
        var commandActive = effectiveMode === INPUT_MODE_COMMAND ? " brave-input-modebar__button--active" : "";
        var chatDisabled = resolvedContext === INPUT_CONTEXT_COMMAND ? " disabled" : "";
        return (
            "<div class='brave-input-modebar' role='tablist' aria-label='Input mode'>"
            + "<button type='button' class='brave-input-modebar__button" + chatActive + "' data-brave-input-mode='" + INPUT_MODE_CHAT + "' aria-pressed='" + (effectiveMode === INPUT_MODE_CHAT ? "true" : "false") + "'" + chatDisabled + ">"
            + "<span>Chat</span>"
            + "</button>"
            + "<button type='button' class='brave-input-modebar__button" + commandActive + "' data-brave-input-mode='" + INPUT_MODE_COMMAND + "' aria-pressed='" + (effectiveMode === INPUT_MODE_COMMAND ? "true" : "false") + "'>"
            + "<span>Command</span>"
            + "</button>"
            + "</div>"
        );
    };

    var ensureInputModeBar = function () {
        var effectiveMode = getEffectiveInputMode();
        var resolvedContext = getResolvedInputContext();
        var chatActive = effectiveMode === INPUT_MODE_CHAT;
        var commandActive = effectiveMode === INPUT_MODE_COMMAND;
        var chatDisabled = resolvedContext === INPUT_CONTEXT_COMMAND;
        $(".inputwrap").each(function () {
            var wrap = $(this);
            var wrapper = wrap.find(".inputfieldwrapper").first();
            if (!wrapper.length) {
                return;
            }
            var modebar = wrap.children(".brave-input-modebar");
            if (!modebar.length) {
                wrapper.before(buildInputModeBarMarkup());
                return;
            }
            var buttons = modebar.children(".brave-input-modebar__button");
            if (buttons.length !== 2) {
                modebar.remove();
                wrapper.before(buildInputModeBarMarkup());
                return;
            }

            var chatButton = buttons.eq(0);
            var commandButton = buttons.eq(1);

            chatButton.toggleClass("brave-input-modebar__button--active", chatActive);
            chatButton.prop("disabled", chatDisabled);
            chatButton.attr("aria-pressed", chatActive ? "true" : "false");

            commandButton.toggleClass("brave-input-modebar__button--active", commandActive);
            commandButton.attr("aria-pressed", commandActive ? "true" : "false");
        });
    };

    var decorateInputs = function () {
        var effectiveMode = getEffectiveInputMode();
        $(".inputfield, #inputfield").attr("placeholder", effectiveMode === INPUT_MODE_CHAT ? getChatPlaceholder() : placeholderByMode.command);
        ensureInputModeBar();
    };

    var decorateSendButton = function () {
        var button = $("#inputsend");
        if (button.length < 1) {
            return;
        }

        button.attr("aria-label", getEffectiveInputMode() === INPUT_MODE_CHAT ? "Send chat" : "Send command");

        if (button.is("input")) {
            button.val("send");
        } else {
            button.empty().append("<i class='ra ra-forward' aria-hidden='true'></i>");
        }
    };

    var moveCaretToEnd = function (inputfield) {
        var element = inputfield && inputfield.get(0);
        if (!element || typeof element.setSelectionRange !== "function") {
            return;
        }

        var length = inputfield.val().length;
        element.setSelectionRange(length, length);
    };

    var persistPlayInputMode = function () {
        try {
            if (window.localStorage) {
                window.localStorage.setItem(INPUT_MODE_STORAGE_KEY, INPUT_MODE_CHAT);
            }
        } catch (error) {
            // Ignore storage failures.
        }
    };

    var refreshInputChrome = function () {
        decorateInputs();
        decorateSendButton();
        setReadyState();
        dispatchInputModeChange();
    };

    var setInputMode = function (mode) {
        var resolvedContext = getResolvedInputContext();
        if (mode !== INPUT_MODE_CHAT && mode !== INPUT_MODE_COMMAND) {
            return getEffectiveInputMode();
        }
        if (resolvedContext === INPUT_CONTEXT_COMMAND && mode !== INPUT_MODE_COMMAND) {
            return getEffectiveInputMode();
        }
        if (resolvedContext === INPUT_CONTEXT_PLAY && mode === INPUT_MODE_COMMAND) {
            return getEffectiveInputMode();
        }
        if (playInputMode !== mode) {
            playInputMode = mode;
            persistPlayInputMode();
        }
        refreshInputChrome();
        return getEffectiveInputMode();
    };

    var openChatDraft = function (commandPrefix, options) {
        options = options || {};
        if (getResolvedInputContext() !== INPUT_CONTEXT_PLAY) {
            setInputContext(INPUT_CONTEXT_PLAY);
        }
        pendingChatPrefix = String(commandPrefix || "");
        pendingChatPrompt = String(options.prompt || "");
        setInputMode(INPUT_MODE_CHAT);
        var inputfield = focusInput({ force: true, openOverlay: true, chatMode: true });
        if (inputfield.length > 0) {
            inputfield.val("");
            moveCaretToEnd(inputfield);
        }
        refreshInputChrome();
        return inputfield;
    };

    var setInputContext = function (context) {
        var nextContext = context === INPUT_CONTEXT_PLAY ? INPUT_CONTEXT_PLAY : INPUT_CONTEXT_COMMAND;
        if (inputContext === nextContext) {
            if (nextContext === INPUT_CONTEXT_PLAY) {
                isLoggedIn = true;
                playInputMode = INPUT_MODE_CHAT;
                persistPlayInputMode();
            }
            refreshInputChrome();
            return inputContext;
        }
        if (inputContext === INPUT_CONTEXT_COMMAND && nextContext === INPUT_CONTEXT_PLAY) {
            isLoggedIn = true;
            playInputMode = INPUT_MODE_CHAT;
            persistPlayInputMode();
        }
        if (nextContext === INPUT_CONTEXT_COMMAND) {
            if (document.body) {
                document.body.classList.remove(MOBILE_INPUT_OPEN_CLASS);
            }
            syncOverlayBackdrop(false);
            window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: false } }));
        }
        inputContext = nextContext;
        refreshInputChrome();
        return inputContext;
    };

    var focusInput = function (options) {
        if (getResolvedInputContext() === INPUT_CONTEXT_COMMAND) {
            return $();
        }
        options = options || {};
        if (options.chatMode && getResolvedInputContext() === INPUT_CONTEXT_PLAY) {
            setInputMode(INPUT_MODE_CHAT);
        }
        if (!focusOnKeydown && !options.force) {
            return $();
        }

        decorateInputLayoutShells();
        if (!isMobileInputOpen()) {
            if (!options.openOverlay) {
                return $();
            }
            setMobileInputOpen(true, { focus: false, moveCaret: options.moveCaret !== false });
        }

        var inputfield = getCommandInput();
        if (inputfield.length < 1) {
            return inputfield;
        }

        inputfield.focus();
        if (options.moveCaret !== false) {
            moveCaretToEnd(inputfield);
        }
        decorateInputs();
        setReadyState();
        return inputfield;
    };

    var setMobileInputOpen = function (open, options) {
        options = options || {};
        decorateInputLayoutShells();
        clearPendingOverlayFocus();

        if (getResolvedInputContext() === INPUT_CONTEXT_COMMAND) {
            if (document.body) {
                document.body.classList.remove(MOBILE_INPUT_OPEN_CLASS);
            }
            syncOverlayBackdrop(false);
            window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: false } }));
            setReadyState(false);
            return $();
        }

        if (!document.body) {
            return getCommandInput();
        }

        document.body.classList.toggle(MOBILE_INPUT_OPEN_CLASS, !!open);
        syncOverlayBackdrop(!!open);
        if (open) {
            lastMobileInputOpenAt = Date.now();
        }
        window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: !!open } }));
        if (open) {
            decorateInputs();
            decorateSendButton();
            setReadyState(true);
            if (options.focus) {
                pendingOverlayFocusTimeout = window.setTimeout(function () {
                    pendingOverlayFocusTimeout = null;
                    focusInput({ force: true, moveCaret: options.moveCaret !== false });
                }, typeof options.delay === "number" ? options.delay : 0);
            }
            return getCommandInput();
        }

        if (!options.preserveFocus) {
            var inputfield = getCommandInput();
            if (inputfield.length > 0) {
                inputfield.blur();
            }
        }
        setReadyState(false);
        return getCommandInput();
    };

    var primeInput = function () {
        if (getResolvedInputContext() === INPUT_CONTEXT_COMMAND || !isMobileInputOpen()) {
            return $();
        }
        decorateInputs();
        decorateInputLayoutShells();
        setReadyState(isMobileInputOpen());
        return focusInput({ force: true });
    };

    var setInputValue = function (value, options) {
        options = options || {};
        clearChatDraft();
        if (options.mode) {
            setInputMode(options.mode);
        } else {
            setInputMode(INPUT_MODE_CHAT);
        }
        var inputfield = focusInput({ force: true, openOverlay: true });
        if (inputfield.length < 1) {
            return;
        }

        inputfield.val(value || "");
        moveCaretToEnd(inputfield);
        setReadyState();
    };

    var insertTextAtCursor = function (inputfield, text) {
        var element = inputfield.get(0);
        if (!element) {
            return;
        }

        if (typeof element.setRangeText === "function") {
            var start = element.selectionStart || 0;
            var end = element.selectionEnd || 0;
            element.setRangeText(text, start, end, "end");
        } else {
            inputfield.val((inputfield.val() || "") + text);
            moveCaretToEnd(inputfield);
        }
    };

    var handleUnfocusedDelete = function (inputfield, isBackspace) {
        var element = inputfield.get(0);
        if (!element) {
            return;
        }

        var value = inputfield.val() || "";
        var start = element.selectionStart || value.length;
        var end = element.selectionEnd || start;

        if (start !== end) {
            if (typeof element.setRangeText === "function") {
                element.setRangeText("", start, end, "start");
            } else {
                inputfield.val(value.slice(0, start) + value.slice(end));
            }
            return;
        }

        if (isBackspace && start > 0) {
            if (typeof element.setRangeText === "function") {
                element.setRangeText("", start - 1, start, "start");
            } else {
                inputfield.val(value.slice(0, start - 1) + value.slice(start));
            }
        } else if (!isBackspace && start < value.length) {
            if (typeof element.setRangeText === "function") {
                element.setRangeText("", start, start + 1, "start");
            } else {
                inputfield.val(value.slice(0, start) + value.slice(start + 1));
            }
        }
    };

    var sendCurrentInput = function (inputfield, event) {
        var outtext = inputfield.val() || "";
        var lines = outtext.replace(/[\r]+/, "\n").replace(/[\n]+/, "\n").split("\n");
        var effectiveMode = getEffectiveInputMode();
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            var trimmed = String(line || "").trim();
            if (!trimmed) {
                continue;
            }
            if (effectiveMode === INPUT_MODE_CHAT) {
                if (pendingChatPrefix) {
                    if (trimmed.charAt(0) === "/") {
                        clearChatDraft();
                        plugin_handler.onSend(trimmed.slice(1));
                        continue;
                    }
                    plugin_handler.onSend(pendingChatPrefix + trimmed);
                    continue;
                }
                if (trimmed.charAt(0) === "/") {
                    plugin_handler.onSend(trimmed.slice(1));
                } else {
                    plugin_handler.onSend("say " + trimmed);
                }
                continue;
            }
            plugin_handler.onSend(line);
        }
        inputfield.val("");
        clearChatDraft();
        refreshInputChrome();
        if (isMobileInputOpen()) {
            setMobileInputOpen(false);
            event.preventDefault();
            return;
        }
        focusInput({ force: true });
        event.preventDefault();
    };

    var shouldCapturePrintable = function (event) {
        return !event.ctrlKey
            && !event.metaKey
            && !event.altKey
            && event.key
            && event.key.length === 1;
    };

    var onKeydown = function (event) {
        var inputfield = $(".inputfield:focus");
        var overlayOpen = isMobileInputOpen();
        if (inputfield.length < 1) {
            inputfield = $("#inputfield:focus");
        }

        if ((event.ctrlKey || event.metaKey) && event.keyCode === 67) {
            return true;
        }

        if (isInteractiveTarget(event.target) && !isCommandInput(event.target)) {
            return true;
        }

        switch (event.which) {
            case 9:
            case 16:
            case 17:
            case 18:
            case 20:
            case 144:
                return true;

            case 13:
                if (overlayOpen && inputfield.length < 1) {
                    inputfield = focusInput({ force: true });
                }
                if (overlayOpen && !event.shiftKey && inputfield.length > 0) {
                    sendCurrentInput(inputfield, event);
                }
                return true;

            case 27:
                var outputPlugin = getDefaultOutPlugin();
                if (outputPlugin && typeof outputPlugin.handleEscapeKey === "function" && outputPlugin.handleEscapeKey()) {
                    event.preventDefault();
                    return true;
                }
                if (inputfield.length > 0) {
                    inputfield.blur();
                    setReadyState();
                    event.preventDefault();
                }
                return true;

            case 192:
                if (!event.ctrlKey && !event.metaKey && !event.altKey) {
                    if (getResolvedInputContext() === INPUT_CONTEXT_PLAY) {
                        setInputMode(INPUT_MODE_CHAT);
                        if (overlayOpen) {
                            setMobileInputOpen(false);
                        } else {
                            focusInput({ force: true, moveCaret: true, chatMode: true, openOverlay: true });
                        }
                        event.preventDefault();
                    }
                }
                return true;

            case 8:
            case 46:
                if (overlayOpen && inputfield.length < 1 && focusOnKeydown) {
                    inputfield = focusInput({ force: true });
                    if (inputfield.length > 0) {
                        handleUnfocusedDelete(inputfield, event.which === 8);
                        event.preventDefault();
                    }
                }
                return true;

            default:
                if (overlayOpen && focusOnKeydown && inputfield.length < 1) {
                    inputfield = focusInput({ force: true });

                    if (inputfield.length > 0 && shouldCapturePrintable(event)) {
                        insertTextAtCursor(inputfield, event.key);
                        event.preventDefault();
                    }
                }
                return true;
        }
    };

    var installFocusBindings = function () {
        $(document)
            .on("click.default_in", "[data-brave-input-mode]", function (event) {
                event.preventDefault();
                playUiSound("select");
                setInputMode($(this).attr("data-brave-input-mode"));
                focusInput({ force: true, moveCaret: true });
            })
            .on("focusin.default_in", ".inputfield, #inputfield", setReadyState)
            .on("focusout.default_in", ".inputfield, #inputfield", function () {
                setTimeout(function () {
                    setReadyState(isMobileInputOpen());
                }, 0);
            })
            .on("input.default_in keyup.default_in", ".inputfield, #inputfield", function () {
                if (isMobileViewport() && $(".inputfield:focus, #inputfield:focus").length < 1) {
                    setReadyState(true);
                    return;
                }
                setReadyState();
            })
            .on("click.default_in touchend.default_in", "#brave-chat-overlay-backdrop", function (event) {
                event.preventDefault();
                playUiSound("close");
                setMobileInputOpen(false);
            });
    };

    var installObserver = function () {
        if (!window.MutationObserver) {
            return;
        }

        var clientwrapper = document.getElementById("clientwrapper");
        if (!clientwrapper) {
            return;
        }

        var observer = new MutationObserver(function () {
            decorateInputs();
            decorateSendButton();
            decorateInputLayoutShells();
            setReadyState();
        });
        observer.observe(clientwrapper, { childList: true, subtree: true });
    };

    var init = function () {
        $("#inputsend")
            .bind("click", function () {
                playUiSound("select");
                var e = $.Event("keydown");
                e.which = 13;
                focusInput({ force: true }).trigger(e);
            });

        decorateInputs();
        decorateSendButton();
        decorateInputLayoutShells();
        installFocusBindings();
        installObserver();
        syncInputModeBodyState();
        dispatchInputModeChange();
    };

    var onLoggedIn = function () {
        isLoggedIn = true;
        setInputContext(INPUT_CONTEXT_PLAY);
        setInputMode(INPUT_MODE_CHAT);
        decorateInputLayoutShells();
    };

    var onConnectionClose = function () {
        isLoggedIn = false;
        setInputContext(INPUT_CONTEXT_COMMAND);
        setReadyState(false);
    };

    return {
        init: init,
        onKeydown: onKeydown,
        onLoggedIn: onLoggedIn,
        setKeydownFocus: function (bool) {
            focusOnKeydown = bool;
        },
        focusInput: focusInput,
        getInputField: getCommandInput,
        setInputValue: setInputValue,
        setInputMode: setInputMode,
        getInputMode: getEffectiveInputMode,
        setInputContext: setInputContext,
        getInputContext: function () {
            return inputContext;
        },
        onConnectionClose: onConnectionClose,
        openMobileInput: function () {
            return setMobileInputOpen(true, { focus: true });
        },
        closeMobileInput: function () {
            return setMobileInputOpen(false);
        },
        isMobileInputOpen: isMobileInputOpen,
        openChatDraft: openChatDraft,
        clearChatDraft: clearChatDraft,
    };
})();
window.plugin_handler.add("default_in", defaultInPlugin);
