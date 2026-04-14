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
    var playInputMode = (function () {
        try {
            var stored = window.localStorage ? window.localStorage.getItem(INPUT_MODE_STORAGE_KEY) : "";
            return stored === INPUT_MODE_COMMAND ? INPUT_MODE_COMMAND : INPUT_MODE_CHAT;
        } catch (error) {
            return INPUT_MODE_CHAT;
        }
    })();
    var inputContext = INPUT_CONTEXT_COMMAND;
    var isLoggedIn = false;
    var lastMobileInputOpenAt = 0;
    var isMobileViewport = function () {
        return !!(window.matchMedia && window.matchMedia("(max-width: 900px)").matches);
    };

    var getEffectiveInputMode = function () {
        return inputContext === INPUT_CONTEXT_COMMAND ? INPUT_MODE_COMMAND : playInputMode;
    };

    var syncInputModeBodyState = function () {
        if (!document.body) {
            return;
        }
        document.body.setAttribute("data-brave-input-mode", getEffectiveInputMode());
        document.body.setAttribute("data-brave-input-context", inputContext);
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

    var setReadyState = function (activeOverride) {
        var focused = $(".inputfield:focus, #inputfield:focus").length > 0;
        var active = activeOverride;
        if (active === undefined || active === null) {
            active = focused;
        }

        var inputfield = getCommandInput();
        var hasText = !!(inputfield.length && String(inputfield.val() || "").length);

        $("body").toggleClass("brave-command-ready", !!active);
        $("body").toggleClass("brave-command-armed", !!active && isMobileViewport() && !focused);
        $("body").toggleClass("brave-command-has-text", hasText);
        $(".inputfield, #inputfield").toggleClass("focused", !!active);
        syncInputModeBodyState();
    };

    var buildInputModeBarMarkup = function () {
        var effectiveMode = getEffectiveInputMode();
        var chatActive = effectiveMode === INPUT_MODE_CHAT ? " brave-input-modebar__button--active" : "";
        var commandActive = effectiveMode === INPUT_MODE_COMMAND ? " brave-input-modebar__button--active" : "";
        var chatDisabled = inputContext === INPUT_CONTEXT_COMMAND ? " disabled" : "";
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
        var chatActive = effectiveMode === INPUT_MODE_CHAT;
        var commandActive = effectiveMode === INPUT_MODE_COMMAND;
        var chatDisabled = inputContext === INPUT_CONTEXT_COMMAND;
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
        $(".inputfield, #inputfield").attr("placeholder", placeholderByMode[getEffectiveInputMode()] || placeholderByMode.command);
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
                window.localStorage.setItem(INPUT_MODE_STORAGE_KEY, playInputMode);
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
        if (mode !== INPUT_MODE_CHAT && mode !== INPUT_MODE_COMMAND) {
            return getEffectiveInputMode();
        }
        if (inputContext === INPUT_CONTEXT_COMMAND && mode !== INPUT_MODE_COMMAND) {
            return getEffectiveInputMode();
        }
        if (playInputMode !== mode) {
            playInputMode = mode;
            persistPlayInputMode();
        }
        refreshInputChrome();
        return getEffectiveInputMode();
    };

    var setInputContext = function (context) {
        var nextContext = context === INPUT_CONTEXT_PLAY ? INPUT_CONTEXT_PLAY : INPUT_CONTEXT_COMMAND;
        if (inputContext === nextContext) {
            if (nextContext === INPUT_CONTEXT_PLAY) {
                isLoggedIn = true;
                playInputMode = INPUT_MODE_CHAT;
                persistPlayInputMode();
                if (isMobileViewport()) {
                    setMobileInputOpen(true, { focus: false, moveCaret: false });
                }
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
            window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: false } }));
        }
        inputContext = nextContext;
        refreshInputChrome();
        if (nextContext === INPUT_CONTEXT_PLAY && isMobileViewport()) {
            setMobileInputOpen(true, { focus: false, moveCaret: false });
        }
        return inputContext;
    };

    var focusInput = function (options) {
        if (inputContext === INPUT_CONTEXT_COMMAND) {
            return $();
        }
        options = options || {};
        if (!focusOnKeydown && !options.force) {
            return $();
        }

        if (isMobileViewport()) {
            decorateInputLayoutShells();
            if (document.body) {
                var wasOpen = document.body.classList.contains(MOBILE_INPUT_OPEN_CLASS);
                document.body.classList.add(MOBILE_INPUT_OPEN_CLASS);
                lastMobileInputOpenAt = Date.now();
                if (!wasOpen) {
                    window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: true } }));
                }
            }
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

        if (!document.body) {
            return getCommandInput();
        }

        if (!isMobileViewport()) {
            document.body.classList.remove(MOBILE_INPUT_OPEN_CLASS);
            if (options.focus) {
                return focusInput({ force: true, moveCaret: options.moveCaret !== false });
            }
            setReadyState();
            return getCommandInput();
        }

        document.body.classList.toggle(MOBILE_INPUT_OPEN_CLASS, !!open);
        if (open) {
            lastMobileInputOpenAt = Date.now();
        }
        window.dispatchEvent(new CustomEvent("brave:mobile-input-state", { detail: { open: !!open } }));
        if (open) {
            decorateInputs();
            decorateSendButton();
            setReadyState(true);
            if (options.focus) {
                window.setTimeout(function () {
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
        if (inputContext === INPUT_CONTEXT_COMMAND) {
            return $();
        }
        if (isMobileViewport()) {
            decorateInputs();
            decorateInputLayoutShells();
            setReadyState(isMobileInputOpen());
            return getCommandInput();
        }
        return focusInput({ force: true });
    };

    var setInputValue = function (value, options) {
        options = options || {};
        if (options.mode) {
            setInputMode(options.mode);
        } else {
            setInputMode(INPUT_MODE_COMMAND);
        }
        var inputfield = focusInput({ force: true });
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
        if (isMobileViewport()) {
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
                if (inputfield.length < 1) {
                    inputfield = focusInput({ force: true });
                }
                if (!event.shiftKey) {
                    sendCurrentInput(inputfield, event);
                }
                return true;

            case 27:
                if (inputfield.length > 0) {
                    inputfield.blur();
                    setReadyState();
                    event.preventDefault();
                }
                return true;

            case 8:
            case 46:
                if (inputfield.length < 1 && focusOnKeydown) {
                    inputfield = focusInput({ force: true });
                    if (inputfield.length > 0) {
                        handleUnfocusedDelete(inputfield, event.which === 8);
                        event.preventDefault();
                    }
                }
                return true;

            default:
                if (focusOnKeydown && inputfield.length < 1) {
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
        $(window).on("focus.default_in", function () {
            setTimeout(function () {
                primeInput();
            }, 25);
        });

        document.addEventListener("visibilitychange", function () {
            if (!document.hidden) {
                setTimeout(function () {
                    primeInput();
                }, 25);
            }
        });

        $(document)
            .on("click.default_in", "[data-brave-input-mode]", function (event) {
                event.preventDefault();
                setInputMode($(this).attr("data-brave-input-mode"));
                if (!isMobileViewport()) {
                    focusInput({ force: true, moveCaret: true });
                }
            })
            .on("focusin.default_in", ".inputfield, #inputfield", setReadyState)
            .on("focusout.default_in", ".inputfield, #inputfield", function () {
                setTimeout(function () {
                    if (isMobileViewport()) {
                        if ($(".inputfield:focus, #inputfield:focus").length < 1) {
                            setMobileInputOpen(false, { preserveFocus: true });
                            return;
                        }
                        setReadyState(isMobileInputOpen());
                        return;
                    }
                    setReadyState();
                }, 0);
            })
            .on("input.default_in keyup.default_in", ".inputfield, #inputfield", function () {
                if (isMobileViewport() && $(".inputfield:focus, #inputfield:focus").length < 1) {
                    setReadyState(true);
                    return;
                }
                setReadyState();
            })
            .on("click.default_in touchend.default_in", "#messagewindow, .content, .lm_content, #brave-chrome", function (event) {
                if (isInteractiveTarget(event.target) || hasSelection()) {
                    return;
                }
                setTimeout(function () {
                    primeInput();
                }, 0);
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

        setTimeout(function () {
            primeInput();
        }, 60);
    };

    var onLoggedIn = function () {
        isLoggedIn = true;
        setInputContext(INPUT_CONTEXT_PLAY);
        setInputMode(INPUT_MODE_CHAT);
        decorateInputLayoutShells();
        primeInput();
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
    };
})();
window.plugin_handler.add("default_in", defaultInPlugin);
