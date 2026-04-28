/*
 *
 * Brave override of Evennia's default outputs plugin.
 *
 * This keeps the stock text/prompt behavior but intercepts Brave-specific
 * OOB events before they fall through as "Unhandled event" noise.
 *
 */
let defaultout_plugin = (function () {
    "use strict";

    var THEME_STORAGE_KEY = "brave.webclient.theme";
    var VIDEO_SETTINGS_STORAGE_KEY = "brave.webclient.video";
    var LEGACY_FONT_STORAGE_KEY = "brave.webclient.font";
    var LEGACY_SIZE_STORAGE_KEY = "evenniaFontSize";
    var DEFAULT_VIDEO_SETTINGS = {
        ui_scale: 1,
        reduced_motion: false,
    };
    var THEME_PRESETS = {
        hearth: { font: "redhat", size: "1.0" },
        signalglass: { font: "sharetech", size: "1.0" },
        terminal: { font: "dejavu", size: "1.0" },
        campfire: { font: "vt323", size: "1.1" },
        journal: { font: "anonymous", size: "1.0" },
        atlas: { font: "space", size: "1.0" },
    };
    var THEME_ALIASES = {
        lantern: "hearth",
        green: "signalglass",
        amber: "campfire",
        paper: "journal",
        slate: "atlas",
        sharp: "signalglass",
        soft: "campfire",
        mud: "terminal",
        bare: "terminal",
        ghost: "terminal",
    };
    var suppressNextLookText = false;
    var browserInteractionHandlersBound = false;
    var connectionBoilerplateObserver = null;
    var roomActivityObserver = null;
    var combatLogObserver = null;
    var reactiveTimers = {};
    var currentViewData = null;
    var currentRoomViewData = null;
    var currentSceneData = null;
    var currentRoomSceneData = null;
    var currentRoomFeedEntries = [];
    var currentRoomVoiceBubbles = [];
    var currentWelcomePages = [];
    var currentWelcomePageIndex = 0;
    var currentRoomVoiceBubbleTimers = {};
    var currentRoomVoiceBubbleRemovalTimers = {};
    var currentRoomVoiceBubbleMarkup = {
        desktop: "",
        self: "",
        mobile: "",
    };
    var currentRoomVoiceBubbleActive = {
        desktop: false,
        self: false,
        mobile: false,
    };
    var nextRoomVoiceBubbleId = 1;
    var roomActivityRailPinnedToBottom = true;
    var roomActivityRailScrollTop = 0;
    var roomActivityRailMissedCount = 0;
    var combatLogPinnedToBottom = true;
    var combatLogScrollTop = 0;
    var currentMapText = "";
    var currentMapGrid = null;
    var currentArcadeState = null;
    var pendingArcadeRoomRestore = false;
    var pendingMainScrollRestore = null;
    var currentMobileUtilityTab = null;
    var mobileRoomActivityUnreadCount = 0;
    var currentCombatActionTab = "abilities";
    var currentMobileSwipe = null;
    var currentPickerData = null;
    var currentPickerAnchorRect = null;
    var currentPickerSourceId = "";
    var currentNoticeTimer = null;
    var currentFishingGame = null;
    var currentFishingAnimationFrame = null;
    var currentConnectionScreen = "menu";
    var braveGameLoaded = false;
    var suppressBrowserClickUntil = 0;
    var allowNextRoomRefreshNavigationUntil = 0;
    var ENABLE_ROOM_SWIPE_NAV = false;
    var pendingCombatFxEvents = [];
    var pendingCombatFxFlushTimeout = null;
    var combatFxProcessing = false;
    var pendingCombatViewRenderTimeout = null;
    var pendingCombatViewData = null;
    var pendingCombatResultViewData = null;
    var pendingCombatResultFallbackTimeout = null;
    var pendingCombatPanelData = null;
    var currentAtbAnimationFrame = null;
    var pendingCombatSwapTimeout = null;
    var pendingCombatTransitionViewData = null;
    var pendingCombatTransitionTimeout = null;
    var pendingCombatTransitionCleanupTimeout = null;
    var pendingCombatTransitionMode = "";
    var pendingCombatResultReturnTransition = false;
    var suppressMobileNonInputFocusUntil = 0;
    var suppressMobileRoomNavScrollUntil = 0;
    var pendingRegionTransitionViewData = null;
    var pendingRegionTransitionTimeout = null;
    var pendingRegionTransitionCleanupTimeout = null;
    var roomSceneCardTransitionTimeout = null;
    var pendingRegionTransitionMeta = null;
    var lastRenderedRoomSceneMeta = null;
    var suppressedCombatEntryRefs = {};
    var combatViewTransitionActive = false;
    var ROOM_VOICE_SPEECH_LIMIT = 2;
    var ROOM_VOICE_EMOTE_LIMIT = 1;
    var ROOM_VOICE_THREAT_LIMIT = 1;
    var ROOM_VOICE_SELF_DURATION_MS = 5000;
    var ROOM_VOICE_DISMISS_ANIMATION_MS = 220;
    var ROOM_VOICE_SPEECH_DURATION_MS = 60000;
    var ROOM_VOICE_EMOTE_DURATION_MS = 30000;
    var ROOM_VOICE_THREAT_DURATION_MS = 60000;
    var currentVideoSettings = null;
    var COMBAT_IMPACT_RGB = {
        damage: "199, 55, 44",
        heal: "65, 160, 100",
        guard: "70, 134, 181",
        break: "201, 145, 38",
        fire: "224, 121, 45",
        frost: "104, 196, 224",
        lightning: "231, 197, 84",
        holy: "232, 204, 124",
        nature: "106, 177, 88",
        poison: "154, 188, 62",
        shadow: "135, 124, 176",
        bleed: "199, 55, 44",
        physical: "199, 55, 44",
    };

    var isMobileViewport = function () {
        return !!(window.matchMedia && window.matchMedia("(max-width: 900px)").matches);
    };

    var getBraveAudio = function () {
        if (!window.BraveAudio || typeof window.BraveAudio.getState !== "function") {
            return null;
        }
        return window.BraveAudio;
    };

    var normalizeVideoUiScale = function (value) {
        var numeric = parseFloat(value);
        if (!Number.isFinite(numeric)) {
            numeric = DEFAULT_VIDEO_SETTINGS.ui_scale;
        }
        numeric = Math.max(0.85, Math.min(1.35, numeric));
        return Math.round(numeric * 100) / 100;
    };

    var normalizeVideoSettings = function (settings) {
        settings = settings && typeof settings === "object" ? settings : {};
        return {
            ui_scale: normalizeVideoUiScale(settings.ui_scale),
            reduced_motion: !!settings.reduced_motion,
        };
    };

    var getVideoSettings = function () {
        if (currentVideoSettings) {
            return currentVideoSettings;
        }
        var parsed = {};
        if (window.localStorage) {
            try {
                parsed = JSON.parse(window.localStorage.getItem(VIDEO_SETTINGS_STORAGE_KEY) || "{}") || {};
            } catch (error) {
                parsed = {};
            }
        }
        currentVideoSettings = normalizeVideoSettings(parsed);
        return currentVideoSettings;
    };

    var applyVideoSettings = function (settings, options) {
        var normalized = normalizeVideoSettings(settings);
        var opts = options || {};
        currentVideoSettings = normalized;
        setBodyState("motion", normalized.reduced_motion ? "reduced" : "full");
        if (window.localStorage && opts.persist !== false) {
            window.localStorage.setItem(VIDEO_SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
        }
        if (opts.refreshTheme !== false) {
            applyTheme(document.body.getAttribute("data-brave-theme") || "hearth", {
                skipPulse: true,
                skipPersistTheme: true,
            });
        }
    };

    var setVideoSetting = function (key, value) {
        var next = normalizeVideoSettings(getVideoSettings());
        if (key === "ui_scale") {
            next.ui_scale = normalizeVideoUiScale(value);
        } else if (key === "reduced_motion") {
            next.reduced_motion = !!value;
        } else {
            return next;
        }
        applyVideoSettings(next);
        return next;
    };

    var toggleVideoSetting = function (key) {
        var next = normalizeVideoSettings(getVideoSettings());
        if (key === "reduced_motion") {
            next.reduced_motion = !next.reduced_motion;
            applyVideoSettings(next);
        }
        return next;
    };

    var formatScalePercent = function (value) {
        return Math.round(normalizeVideoUiScale(value) * 100) + "%";
    };

    var prefersReducedMotion = function () {
        return !!(
            getVideoSettings().reduced_motion
            || (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches)
        );
    };

    var getCombatTransitionRevealDelay = function (mode) {
        if (mode === "return") {
            return 1180;
        }
        return 980;
    };

    var getCombatTransitionCleanupDelay = function (mode) {
        if (mode === "return") {
            return 360;
        }
        return 320;
    };

    var getDefaultInPlugin = function () {
        if (!window.plugins || !window.plugins.default_in) {
            return null;
        }
        return window.plugins.default_in;
    };

    var getInputMode = function () {
        var inputPlugin = getDefaultInPlugin();
        if (inputPlugin && typeof inputPlugin.getInputMode === "function") {
            return inputPlugin.getInputMode();
        }
        return "chat";
    };

    var handleAudioPickerInteraction = function (target) {
        if (!target) {
            return false;
        }
        var audioActionTarget = target.closest("[data-brave-audio-action]");
        if (audioActionTarget) {
            var braveAudio = getBraveAudio();
            if (braveAudio && audioActionTarget.getAttribute("data-brave-audio-action") === "unlock") {
                braveAudio.unlock().then(function () {
                    renderPickerSheet();
                });
            }
            return true;
        }
        var audioPreviewTarget = target.closest("[data-brave-audio-preview]");
        if (audioPreviewTarget) {
            var braveAudioPreview = getBraveAudio();
            if (braveAudioPreview && typeof braveAudioPreview.previewCue === "function") {
                braveAudioPreview.previewCue(audioPreviewTarget.getAttribute("data-brave-audio-preview"));
            }
            return true;
        }
        var audioToggleTarget = target.closest("[data-brave-audio-toggle]");
        if (audioToggleTarget) {
            var braveAudioToggle = getBraveAudio();
            if (braveAudioToggle && typeof braveAudioToggle.toggleSetting === "function") {
                braveAudioToggle.toggleSetting(audioToggleTarget.getAttribute("data-brave-audio-toggle"));
                renderPickerSheet();
            }
            return true;
        }
        return false;
    };

    var handleVideoPickerInteraction = function (target) {
        var actionTarget;
        var toggleTarget;
        if (!target) {
            return false;
        }
        actionTarget = target.closest("[data-brave-video-action]");
        if (actionTarget) {
            if (actionTarget.getAttribute("data-brave-video-action") === "fullscreen") {
                toggleFullscreenMode().finally(function () {
                    renderPickerSheet();
                });
            } else if (actionTarget.getAttribute("data-brave-video-action") === "reset") {
                applyVideoSettings(DEFAULT_VIDEO_SETTINGS);
                renderPickerSheet();
            }
            return true;
        }
        toggleTarget = target.closest("[data-brave-video-toggle]");
        if (toggleTarget) {
            toggleVideoSetting(toggleTarget.getAttribute("data-brave-video-toggle"));
            renderPickerSheet();
            return true;
        }
        return false;
    };

    var viewSupportsBottomInput = function (viewData) {
        return !!(
            viewData
            && (viewData.layout === "explore" || (viewData.reactive && viewData.reactive.scene === "explore"))
        );
    };

    var isBottomInputSceneActive = function () {
        return !!(document.body && document.body.getAttribute("data-brave-scene") === "explore");
    };

    var syncInputContextForView = function (viewData) {
        var inputPlugin = getDefaultInPlugin();
        if (!inputPlugin || typeof inputPlugin.setInputContext !== "function") {
            return;
        }
        inputPlugin.setInputContext(viewSupportsBottomInput(viewData) ? "play" : "command");
    };

    var isMobileCommandTrayOpen = function () {
        var inputPlugin = getDefaultInPlugin();
        if (inputPlugin && typeof inputPlugin.isMobileInputOpen === "function") {
            return !!inputPlugin.isMobileInputOpen();
        }
        return !!(document.body && document.body.classList.contains("brave-mobile-input-open"));
    };

    var openMobileCommandTray = function () {
        var inputPlugin = getDefaultInPlugin();
        if (!inputPlugin) {
            return false;
        }
        if (typeof inputPlugin.setInputMode === "function") {
            inputPlugin.setInputMode("chat");
        }
        if (typeof inputPlugin.openMobileInput === "function") {
            inputPlugin.openMobileInput();
            if (typeof inputPlugin.isMobileInputOpen === "function") {
                return !!inputPlugin.isMobileInputOpen();
            }
            return true;
        }
        return false;
    };

    var closeMobileCommandTray = function () {
        var inputPlugin = getDefaultInPlugin();
        if (inputPlugin && typeof inputPlugin.closeMobileInput === "function") {
            inputPlugin.closeMobileInput();
            return true;
        }
        if (document.body) {
            document.body.classList.remove("brave-mobile-input-open");
        }
        return false;
    };

    var isRoomLikeView = function (viewData) {
        return !!(viewData && typeof viewData === "object" && (viewData.layout === "explore" || viewData.variant === "room"));
    };

    var isCombatUiActive = function () {
        if (combatViewTransitionActive || (currentViewData && currentViewData.variant === "combat")) {
            return true;
        }
        if (document.body && document.body.getAttribute("data-brave-scene") === "combat") {
            return true;
        }
        return !!document.querySelector("#messagewindow .brave-view--combat");
    };

    var hasCombatFxWork = function () {
        return !!(combatFxProcessing || pendingCombatFxEvents.length);
    };

    var shouldDeferCombatViewRender = function (viewData) {
        if (!viewData || !currentViewData || currentViewData.variant !== "combat") {
            return false;
        }
        if (viewData.variant !== "combat") {
            return false;
        }
        return hasCombatFxWork();
    };

    var shouldQueueCombatResultView = function (viewData) {
        return !!(
            viewData
            && viewData.variant === "combat-result"
            && isCombatUiActive()
            && hasCombatFxWork()
        );
    };

    var flushQueuedCombatResultView = function () {
        if (!pendingCombatResultViewData || hasCombatFxWork()) {
            return;
        }
        if (pendingCombatResultFallbackTimeout) {
            window.clearTimeout(pendingCombatResultFallbackTimeout);
            pendingCombatResultFallbackTimeout = null;
        }
        var viewData = pendingCombatResultViewData;
        pendingCombatResultViewData = null;
        clearDeferredCombatViewRender();
        pendingCombatPanelData = null;
        renderMainView(viewData);
    };

    var forceFlushQueuedCombatResultView = function () {
        if (!pendingCombatResultViewData) {
            return;
        }
        clearDeferredCombatViewRender();
        pendingCombatFxEvents = [];
        combatFxProcessing = false;
        combatViewTransitionActive = false;
        flushQueuedCombatResultView();
    };

    var scheduleCombatResultFallback = function () {
        if (pendingCombatResultFallbackTimeout) {
            return;
        }
        pendingCombatResultFallbackTimeout = window.setTimeout(function () {
            pendingCombatResultFallbackTimeout = null;
            forceFlushQueuedCombatResultView();
        }, 1800);
    };

    var shouldIgnoreRoomViewDuringCombat = function (viewData) {
        return !!(isCombatUiActive() && isRoomLikeView(viewData));
    };

    var isCombatPanelData = function (panelData) {
        return !!(
            panelData
            && typeof panelData === "object"
            && String(panelData.title || "").toUpperCase() === "COMBAT"
        );
    };

    var compactOobKwargs = function (kwargs) {
        var compact = {};
        Object.keys(kwargs || {}).forEach(function (entryKey) {
            if (entryKey === "options" || entryKey === "cmdid") {
                return;
            }
            compact[entryKey] = kwargs[entryKey];
        });
        return compact;
    };

    var getOobPayload = function (args, kwargs, key, fallback) {
        if (kwargs && Object.prototype.hasOwnProperty.call(kwargs, key)) {
            return kwargs[key];
        }
        if (kwargs && Object.keys(kwargs).length) {
            var compact = compactOobKwargs(kwargs);
            if (Object.keys(compact).length) {
                return compact;
            }
        }
        if (Array.isArray(args) && args.length) {
            return args[0];
        }
        return fallback;
    };

    var clearDeferredCombatViewRender = function () {
        if (pendingCombatViewRenderTimeout) {
            window.clearTimeout(pendingCombatViewRenderTimeout);
            pendingCombatViewRenderTimeout = null;
        }
        pendingCombatViewData = null;
    };

    var flushDeferredCombatViewRender = function (force) {
        if (!pendingCombatViewData) {
            return;
        }
        if (!force && (hasCombatFxWork() || combatViewTransitionActive || pendingCombatResultViewData || pendingCombatSwapTimeout)) {
            deferCombatViewRender(pendingCombatViewData);
            return;
        }
        var viewData = pendingCombatViewData;
        clearDeferredCombatViewRender();
        renderMainView(viewData);
    };

    var deferCombatViewRender = function (viewData) {
        pendingCombatViewData = viewData;
        if (pendingCombatViewRenderTimeout) {
            return;
        }
        pendingCombatViewRenderTimeout = window.setTimeout(function () {
            pendingCombatViewRenderTimeout = null;
            flushDeferredCombatViewRender(false);
        }, 80);
    };

    var getCurrentRoomView = function () {
        if (isRoomLikeView(currentViewData)) {
            return currentViewData;
        }
        if (isRoomLikeView(currentRoomViewData)) {
            return currentRoomViewData;
        }
        return null;
    };

    var currentRoomActivityTab = "activity";

    var normalizeRoomActivityTab = function (tab) {
        return tab === "nearby" ? "nearby" : "activity";
    };

    var getRoomSocialPresence = function (roomView) {
        var data = roomView && roomView.social_presence && typeof roomView.social_presence === "object"
            ? roomView.social_presence
            : {};
        var nearbyTotal = parseInt(data.nearby_total, 10);
        var engagedTotal = parseInt(data.engaged_total, 10);
        var partyTotal = parseInt(data.party_total, 10);
        var groupCount = parseInt(data.group_count, 10);
        return {
            nearby_total: isNaN(nearbyTotal) ? 0 : Math.max(0, nearbyTotal),
            engaged_total: isNaN(engagedTotal) ? 0 : Math.max(0, engagedTotal),
            party_total: isNaN(partyTotal) ? 0 : Math.max(0, partyTotal),
            group_count: isNaN(groupCount) ? 0 : Math.max(0, groupCount),
            people: Array.isArray(data.people) ? data.people : [],
        };
    };

    var extractRoomVoicePreview = function (text, category) {
        var clean = String(text || "").replace(/\s+/g, " ").trim();
        if (!clean) {
            return null;
        }
        var speechMatch = clean.match(/^(.*?)\s+(says?|asks?|exclaims?|whispers?|shouts?|yells?)(?:,)?\s+"(.+)"$/i);
        if (speechMatch) {
            return {
                speaker: speechMatch[1].trim(),
                line: "\"" + speechMatch[3].trim() + "\"",
                category: "speech",
            };
        }
        var emoteMatch = clean.match(/^(.*?)\s+(smiles?|nods?|waves?|shrugs?|laughs?|frowns?|bows?)\b(.*)$/i);
        if (emoteMatch) {
            return {
                speaker: emoteMatch[1].trim(),
                line: clean,
                category: "emote",
            };
        }
        return {
            speaker: category === "emote" ? "Nearby" : "Voice",
            line: clean,
            category: category || "speech",
        };
    };

    var getRoomActiveVoices = function (limit) {
        var seen = {};
        var voices = [];
        var max = typeof limit === "number" && limit > 0 ? limit : 3;
        for (var i = currentRoomFeedEntries.length - 1; i >= 0; i -= 1) {
            var entry = currentRoomFeedEntries[i];
            var category = entry && entry.category ? entry.category : classifyRoomActivity(entry && entry.text ? entry.text : "", entry && entry.cls ? entry.cls : "out", entry);
            if (category !== "speech" && category !== "emote") {
                continue;
            }
            var preview = extractRoomVoicePreview(entry && entry.text ? entry.text : "", category);
            if (!preview || !preview.line) {
                continue;
            }
            var key = String(preview.speaker || preview.line).toLowerCase();
            if (seen[key]) {
                continue;
            }
            seen[key] = true;
            voices.push(preview);
            if (voices.length >= max) {
                break;
            }
        }
        return voices;
    };

    var getRoomVoiceBubbleSpeakerKey = function (speaker) {
        return String(speaker || "").trim().toLowerCase();
    };

    var isSelfRoomVoiceBubble = function (bubble) {
        if (!bubble) {
            return false;
        }
        var speakerKey = getRoomVoiceBubbleSpeakerKey(bubble.speaker);
        var line = String(bubble.line || "").trim().toLowerCase();
        return speakerKey === "you" || line.indexOf("you ") === 0;
    };

    var getRoomVoiceBubbleDurationMs = function (bubble) {
        if (!bubble) {
            return ROOM_VOICE_SPEECH_DURATION_MS;
        }
        if (isSelfRoomVoiceBubble(bubble)) {
            return ROOM_VOICE_SELF_DURATION_MS;
        }
        if (bubble.category === "emote") {
            return ROOM_VOICE_EMOTE_DURATION_MS;
        }
        if (bubble.category === "threat") {
            return ROOM_VOICE_THREAT_DURATION_MS;
        }
        return ROOM_VOICE_SPEECH_DURATION_MS;
    };

    var clearRoomVoiceBubbleTimer = function (bubbleId) {
        if (!currentRoomVoiceBubbleTimers[bubbleId]) {
            return;
        }
        window.clearTimeout(currentRoomVoiceBubbleTimers[bubbleId]);
        delete currentRoomVoiceBubbleTimers[bubbleId];
    };

    var clearRoomVoiceBubbleRemovalTimer = function (bubbleId) {
        if (!currentRoomVoiceBubbleRemovalTimers[bubbleId]) {
            return;
        }
        window.clearTimeout(currentRoomVoiceBubbleRemovalTimers[bubbleId]);
        delete currentRoomVoiceBubbleRemovalTimers[bubbleId];
    };

    var buildRoomVoiceBubbleLayerMarkup = function (options) {
        var opts = options || {};
        var active = currentRoomVoiceBubbles
            .slice()
            .filter(function (bubble) {
                if (opts.selfOnly) {
                    return isSelfRoomVoiceBubble(bubble);
                }
                if (opts.excludeSelf) {
                    return !isSelfRoomVoiceBubble(bubble);
                }
                return true;
            })
            .sort(function (left, right) {
                return (right.updated_at || 0) - (left.updated_at || 0);
            });
        var speech = active.filter(function (bubble) {
            return bubble && bubble.category === "speech";
        });
        var emotes = active.filter(function (bubble) {
            return bubble && bubble.category === "emote";
        });
        var threats = active.filter(function (bubble) {
            return bubble && bubble.category === "threat";
        });
        var visibleThreats = threats.slice(0, ROOM_VOICE_THREAT_LIMIT);
        var visibleSpeech = visibleThreats.length ? [] : speech.slice(0, ROOM_VOICE_SPEECH_LIMIT);
        var visibleEmotes = (visibleThreats.length || visibleSpeech.length) ? [] : emotes.slice(0, ROOM_VOICE_EMOTE_LIMIT);
        var visible = visibleThreats.concat(visibleSpeech, visibleEmotes);
        var overflow = Math.max(0, active.length - visible.length);
        if (!visible.length) {
            return "";
        }
        return (
            "<div class='brave-room-voice-layer"
            + (opts.mobile ? " brave-room-voice-layer--mobile" : "")
            + (opts.selfOnly ? " brave-room-voice-layer--self" : "")
            + "' aria-hidden='true'>"
            + visible.map(function (bubble, index) {
                var bubbleClass = "brave-room-voice-bubble brave-room-voice-bubble--" + escapeHtml(bubble.category || "speech");
                if (isSelfRoomVoiceBubble(bubble)) {
                    bubbleClass += " brave-room-voice-bubble--self";
                }
                if (bubble && bubble.dismissing) {
                    bubbleClass += " brave-room-voice-bubble--dismissing";
                }
                if (index === 0 && (bubble.category === "speech" || bubble.category === "threat")) {
                    bubbleClass += " brave-room-voice-bubble--lead";
                }
                return (
                    "<div class='" + bubbleClass + "' data-brave-room-voice-id='" + escapeHtml(String(bubble.id)) + "'>"
                    + (bubble.category === "emote"
                        ? ""
                        : "<div class='brave-room-voice-bubble__speaker'>" + escapeHtml(bubble.speaker || "Nearby") + "</div>")
                    + "<div class='brave-room-voice-bubble__line'>" + escapeHtml(bubble.line || "") + "</div>"
                    + "</div>"
                );
            }).join("")
            + (overflow
                ? "<div class='brave-room-voice-overflow'>+" + escapeHtml(String(overflow)) + " more</div>"
                : "")
            + "</div>"
        );
    };

    var syncRoomVoiceBubblePositions = function () {
        var overlay = document.getElementById("brave-room-voice-overlay-desktop");
        if (!overlay || !currentRoomVoiceBubbles.length) return;
        
        currentRoomVoiceBubbles.forEach(function (bubble) {
            if (isSelfRoomVoiceBubble(bubble)) {
                return;
            }
            var speakerName = escapeHtml(bubble.speaker || "");
            var target = null;
            if (speakerName) {
                try {
                    var safeSelector = speakerName.replace(/"/g, '\\"');
                    // Prefer the main view's vicinity section first, then fallback to the rail panel
                    target = document.querySelector(".brave-view--room .brave-view__section--vicinity [data-brave-speaker=\"" + safeSelector + "\"]");
                    if (!target || target.offsetWidth === 0) {
                        target = document.querySelector("#scene-vicinity-panel [data-brave-speaker=\"" + safeSelector + "\"]");
                    }
                } catch (e) {}
            }
            
            var bubbleEl = overlay.querySelector("[data-brave-room-voice-id='" + bubble.id + "']");
            if (target && bubbleEl && target.offsetWidth > 0) {
                var targetRect = target.getBoundingClientRect();
                var scrollContainer = target.closest(".brave-view__list") || target.closest(".scene-card__list") || target.closest(".scene-rail__panel");
                var isHidden = false;
                
                if (scrollContainer) {
                    var containerRect = scrollContainer.getBoundingClientRect();
                    // Check if the card has scrolled completely out of view
                    if (targetRect.bottom < containerRect.top || targetRect.top > containerRect.bottom) {
                        isHidden = true;
                    }
                }
                
                bubbleEl.style.position = "fixed";
                bubbleEl.style.top = (targetRect.top - bubbleEl.offsetHeight - 12) + "px";
                bubbleEl.style.left = targetRect.left + "px";
                bubbleEl.style.width = targetRect.width + "px";
                bubbleEl.style.bottom = "auto";
                bubbleEl.style.right = "auto";
                bubbleEl.style.zIndex = "100";
                
                if (isHidden) {
                    bubbleEl.style.opacity = "0";
                    bubbleEl.style.pointerEvents = "none";
                    bubbleEl.style.transition = "opacity 0.15s ease-out";
                } else {
                    bubbleEl.style.opacity = "1";
                    bubbleEl.style.pointerEvents = "auto";
                    bubbleEl.style.transition = "opacity 0.15s ease-in";
                }
            } else if (bubbleEl) {
                 bubbleEl.style.position = "";
                 bubbleEl.style.top = "";
                 bubbleEl.style.bottom = "";
                 bubbleEl.style.right = "";
                 bubbleEl.style.left = "";
                 bubbleEl.style.width = "";
                 bubbleEl.style.zIndex = "";
                 bubbleEl.style.opacity = "";
                 bubbleEl.style.pointerEvents = "";
                 bubbleEl.style.transition = "";
            }
        });
    };

    var syncRoomVoiceBubbleHosts = function () {
        var railHost = document.getElementById("brave-room-voice-overlay-desktop");
        if (railHost) {
            var desktopMarkup = buildRoomVoiceBubbleLayerMarkup({ mobile: false, excludeSelf: true });
            var desktopActive = currentRoomVoiceBubbles.some(function (bubble) {
                return !isSelfRoomVoiceBubble(bubble);
            });
            if (currentRoomVoiceBubbleMarkup.desktop !== desktopMarkup) {
                railHost.innerHTML = desktopMarkup;
                currentRoomVoiceBubbleMarkup.desktop = desktopMarkup;
            }
            if (currentRoomVoiceBubbleActive.desktop !== desktopActive) {
                railHost.setAttribute("aria-hidden", desktopActive ? "false" : "true");
                railHost.classList.toggle("brave-room-voice-overlay--active", desktopActive);
                currentRoomVoiceBubbleActive.desktop = desktopActive;
            }
        }
        var selfHost = document.getElementById("brave-room-voice-overlay-self");
        if (selfHost) {
            var selfMarkup = buildRoomVoiceBubbleLayerMarkup({ mobile: false, selfOnly: true });
            var selfActive = currentRoomVoiceBubbles.some(function (bubble) {
                return isSelfRoomVoiceBubble(bubble);
            });
            if (currentRoomVoiceBubbleMarkup.self !== selfMarkup) {
                selfHost.innerHTML = selfMarkup;
                currentRoomVoiceBubbleMarkup.self = selfMarkup;
            }
            if (currentRoomVoiceBubbleActive.self !== selfActive) {
                selfHost.setAttribute("aria-hidden", selfActive ? "false" : "true");
                selfHost.classList.toggle("brave-room-voice-overlay--active", selfActive);
                currentRoomVoiceBubbleActive.self = selfActive;
            }
        }
        var mobileHost = document.getElementById("brave-room-voice-overlay-mobile");
        if (mobileHost) {
            var mobileMarkup = buildRoomVoiceBubbleLayerMarkup({ mobile: true });
            var mobileActive = !!currentRoomVoiceBubbles.length;
            if (currentRoomVoiceBubbleMarkup.mobile !== mobileMarkup) {
                mobileHost.innerHTML = mobileMarkup;
                currentRoomVoiceBubbleMarkup.mobile = mobileMarkup;
            }
            if (currentRoomVoiceBubbleActive.mobile !== mobileActive) {
                mobileHost.setAttribute("aria-hidden", mobileActive ? "false" : "true");
                mobileHost.classList.toggle("brave-room-voice-overlay--active", mobileActive);
                currentRoomVoiceBubbleActive.mobile = mobileActive;
            }
        }
        
        syncRoomVoiceBubblePositions();
    };

    window.addEventListener("scroll", syncRoomVoiceBubblePositions, true);
    window.addEventListener("resize", syncRoomVoiceBubblePositions);

    var removeRoomVoiceBubble = function (bubbleId) {
        clearRoomVoiceBubbleTimer(bubbleId);
        var bubble = null;
        for (var i = 0; i < currentRoomVoiceBubbles.length; i += 1) {
            if (currentRoomVoiceBubbles[i] && currentRoomVoiceBubbles[i].id === bubbleId) {
                bubble = currentRoomVoiceBubbles[i];
                break;
            }
        }
        if (!bubble) {
            clearRoomVoiceBubbleRemovalTimer(bubbleId);
            return;
        }
        if (bubble.dismissing) {
            return;
        }
        bubble.dismissing = true;
        bubble.dismiss_started_at = Date.now();
        clearRoomVoiceBubbleRemovalTimer(bubbleId);
        syncRoomVoiceBubbleHosts();
        currentRoomVoiceBubbleRemovalTimers[bubbleId] = window.setTimeout(function () {
            currentRoomVoiceBubbles = currentRoomVoiceBubbles.filter(function (entry) {
                return entry && entry.id !== bubbleId;
            });
            clearRoomVoiceBubbleRemovalTimer(bubbleId);
            syncRoomVoiceBubbleHosts();
        }, ROOM_VOICE_DISMISS_ANIMATION_MS);
    };

    var startRoomVoiceBubbleDismiss = function (bubbleId) {
        var bubble = null;
        for (var i = 0; i < currentRoomVoiceBubbles.length; i += 1) {
            if (currentRoomVoiceBubbles[i] && currentRoomVoiceBubbles[i].id === bubbleId) {
                bubble = currentRoomVoiceBubbles[i];
                break;
            }
        }
        if (!bubble) {
            return;
        }
        removeRoomVoiceBubble(bubbleId);
    };

    var dismissRoomVoiceBubble = function (bubbleId) {
        clearRoomVoiceBubbleTimer(bubbleId);
        clearRoomVoiceBubbleRemovalTimer(bubbleId);
        startRoomVoiceBubbleDismiss(bubbleId);
    };

    var dismissRoomVoiceBubblesForSpeaker = function (speaker) {
        var speakerKey = getRoomVoiceBubbleSpeakerKey(speaker);
        if (!speakerKey) {
            return;
        }
        currentRoomVoiceBubbles.slice().forEach(function (bubble) {
            if (bubble && getRoomVoiceBubbleSpeakerKey(bubble.speaker) === speakerKey) {
                dismissRoomVoiceBubble(bubble.id);
            }
        });
    };

    var purgeRoomVoiceBubble = function (bubbleId) {
        clearRoomVoiceBubbleTimer(bubbleId);
        clearRoomVoiceBubbleRemovalTimer(bubbleId);
        currentRoomVoiceBubbles = currentRoomVoiceBubbles.filter(function (bubble) {
            return bubble && bubble.id !== bubbleId;
        });
        syncRoomVoiceBubbleHosts();
    };

    var scheduleRoomVoiceBubbleExpiry = function (bubbleId) {
        clearRoomVoiceBubbleTimer(bubbleId);
        var duration = ROOM_VOICE_SPEECH_DURATION_MS;
        for (var i = 0; i < currentRoomVoiceBubbles.length; i += 1) {
            if (currentRoomVoiceBubbles[i] && currentRoomVoiceBubbles[i].id === bubbleId) {
                duration = getRoomVoiceBubbleDurationMs(currentRoomVoiceBubbles[i]);
                break;
            }
        }
        currentRoomVoiceBubbleTimers[bubbleId] = window.setTimeout(function () {
            startRoomVoiceBubbleDismiss(bubbleId);
        }, duration);
    };

    var clearRoomVoiceBubbles = function () {
        Object.keys(currentRoomVoiceBubbleTimers).forEach(function (bubbleId) {
            clearRoomVoiceBubbleTimer(bubbleId);
        });
        Object.keys(currentRoomVoiceBubbleRemovalTimers).forEach(function (bubbleId) {
            clearRoomVoiceBubbleRemovalTimer(bubbleId);
        });
        currentRoomVoiceBubbles = [];
        currentRoomVoiceBubbleMarkup.desktop = "";
        currentRoomVoiceBubbleMarkup.self = "";
        currentRoomVoiceBubbleMarkup.mobile = "";
        currentRoomVoiceBubbleActive.desktop = null;
        currentRoomVoiceBubbleActive.self = null;
        currentRoomVoiceBubbleActive.mobile = null;
        syncRoomVoiceBubbleHosts();
    };

    var recordRoomVoiceBubble = function (text, category) {
        if ((category !== "speech" && category !== "emote" && category !== "threat") || isCombatUiActive() || !isRoomLikeView(getCurrentRoomView())) {
            return;
        }
        var preview = category === "threat"
            ? { speaker: "Danger", line: String(text || "").replace(/\s+/g, " ").trim(), category: "threat" }
            : extractRoomVoicePreview(text, category);
        if (!preview || (preview.category !== "speech" && preview.category !== "emote" && preview.category !== "threat") || !preview.line) {
            return;
        }
        var now = Date.now();
        var speaker = preview.speaker || "Nearby";
        var speakerKey = getRoomVoiceBubbleSpeakerKey(speaker);
        var existing = null;
        for (var i = 0; i < currentRoomVoiceBubbles.length; i += 1) {
            if (
                getRoomVoiceBubbleSpeakerKey(currentRoomVoiceBubbles[i].speaker) === speakerKey
                && String(currentRoomVoiceBubbles[i].category || "speech") === String(preview.category || category)
            ) {
                existing = currentRoomVoiceBubbles[i];
                break;
            }
        }
        if (existing) {
            existing.speaker = speaker;
            existing.line = preview.line;
            existing.category = preview.category || category;
            existing.updated_at = now;
            scheduleRoomVoiceBubbleExpiry(existing.id);
            syncRoomVoiceBubbleHosts();
            return;
        }
        var bubble = {
            id: nextRoomVoiceBubbleId,
            speaker: speaker,
            line: preview.line,
            category: preview.category || category,
            updated_at: now,
        };
        nextRoomVoiceBubbleId += 1;
        currentRoomVoiceBubbles.push(bubble);
        scheduleRoomVoiceBubbleExpiry(bubble.id);
        syncRoomVoiceBubbleHosts();
    };

    var buildRoomActivityTabsMarkup = function (roomView) {
        var presence = getRoomSocialPresence(roomView);
        return (
            "<div class='brave-room-activity-tabs' data-brave-room-tabs='1'>"
            + "<button type='button' class='brave-room-activity-tabs__button brave-click"
                + (currentRoomActivityTab === "activity" ? " brave-room-activity-tabs__button--active" : "")
                + "' data-brave-activity-tab='activity' aria-pressed='" + (currentRoomActivityTab === "activity" ? "true" : "false") + "'>"
                + "<span>Activity</span>"
                + "</button>"
            + "<button type='button' class='brave-room-activity-tabs__button brave-click"
                + (currentRoomActivityTab === "nearby" ? " brave-room-activity-tabs__button--active" : "")
                + "' data-brave-activity-tab='nearby' aria-pressed='" + (currentRoomActivityTab === "nearby" ? "true" : "false") + "'>"
                + "<span>Nearby</span>"
                + (presence.nearby_total ? "<strong>" + escapeHtml(String(presence.nearby_total)) + "</strong>" : "")
                + "</button>"
            + "</div>"
        );
    };

    var buildRoomNearbyMarkup = function (roomView, options) {
        var presence = getRoomSocialPresence(roomView);
        var people = presence.people || [];
        var opts = options || {};
        var summaryBits = [];
        if (presence.nearby_total) {
            summaryBits.push(String(presence.nearby_total) + " nearby");
        }
        if (presence.group_count) {
            summaryBits.push(String(presence.group_count) + " group" + (presence.group_count === 1 ? "" : "s"));
        }
        if (presence.engaged_total) {
            summaryBits.push(String(presence.engaged_total) + " engaged");
        }
        return (
            "<div class='brave-room-nearby" + (opts.mobile ? " brave-room-nearby--mobile" : "") + "'>"
            + (summaryBits.length ? "<div class='brave-room-nearby__summary'>" + escapeHtml(summaryBits.join(" · ")) + "</div>" : "")
            + (people.length
                ? "<div class='brave-room-nearby__list'>"
                    + people.map(function (person) {
                        var badgeTone = person && person.badge_tone ? " brave-room-nearby__badge--" + escapeHtml(person.badge_tone) : "";
                        return (
                            "<button type='button' class='brave-room-nearby__entry brave-click'"
                            + commandAttrs(person, false)
                            + ">"
                            + "<span class='brave-room-nearby__entry-icon'>" + icon("person") + "</span>"
                            + "<span class='brave-room-nearby__entry-body'>"
                            + "<span class='brave-room-nearby__entry-head'>"
                            + "<span class='brave-room-nearby__entry-name'>" + escapeHtml(person && person.name ? person.name : "") + "</span>"
                            + (person && person.badge ? "<span class='brave-room-nearby__badge" + badgeTone + "'>" + escapeHtml(person.badge) + "</span>" : "")
                            + "</span>"
                            + (person && person.summary ? "<span class='brave-room-nearby__entry-summary'>" + escapeHtml(person.summary) + "</span>" : "")
                            + (person && person.detail ? "<span class='brave-room-nearby__entry-detail'>" + escapeHtml(person.detail) + "</span>" : "")
                            + "</span>"
                            + "<span class='brave-room-nearby__entry-chevron'>" + icon("chevron_right") + "</span>"
                            + "</button>"
                        );
                    }).join("")
                    + "</div>"
                : "<div class='brave-room-nearby__empty'>No other players are visible here right now.</div>")
            + "</div>"
        );
    };

    var syncRoomActivityCardSurface = function (root, roomView, options) {
        if (!root) {
            return;
        }
        var opts = options || {};
        var tabsHost = root.querySelector("[data-brave-room-tabs-host]");
        var activityPane = root.querySelector("[data-brave-room-pane='activity']");
        var nearbyPane = root.querySelector("[data-brave-room-pane='nearby']");
        var nearbyHost = root.querySelector("[data-brave-room-nearby]");
        var jump = root.querySelector("[data-brave-activity-scroll='rail']");
        if (tabsHost) {
            tabsHost.innerHTML = buildRoomActivityTabsMarkup(roomView);
        }
        if (nearbyHost) {
            nearbyHost.innerHTML = buildRoomNearbyMarkup(roomView, { mobile: !!opts.mobile });
        }
        if (activityPane) {
            activityPane.classList.toggle("brave-room-activity-pane--hidden", currentRoomActivityTab !== "activity");
        }
        if (nearbyPane) {
            nearbyPane.classList.toggle("brave-room-activity-pane--hidden", currentRoomActivityTab !== "nearby");
        }
        if (jump) {
            jump.classList.toggle("brave-room-log__jump--hidden", currentRoomActivityTab !== "activity");
        }
    };

    var setRoomActivityTab = function (tab) {
        currentRoomActivityTab = normalizeRoomActivityTab(tab);
        syncRoomActivityCardSurface(document.getElementById("scene-vicinity-panel"), getCurrentRoomView(), { mobile: false });
        syncRoomActivityCardSurface(document.getElementById("mobile-utility-sheet"), getCurrentRoomView(), { mobile: true });
    };

    var getReactiveSourceId = function (viewData) {
        if (!viewData || !viewData.reactive || typeof viewData.reactive !== "object") {
            return "";
        }
        return String(viewData.reactive.source_id || "");
    };

    var shouldPreserveCurrentViewOnRoomRefresh = function (viewData) {
        if (!isRoomLikeView(viewData)) {
            return false;
        }
        if (!currentViewData || isRoomLikeView(currentViewData)) {
            return false;
        }
        if (
            currentViewData.variant === "connection"
            || currentViewData.variant === "chargen"
            || currentViewData.variant === "account"
            || currentViewData.variant === "combat"
            || currentViewData.variant === "combat-result"
        ) {
            return false;
        }
        return !!getReactiveSourceId(viewData) && getReactiveSourceId(viewData) === getReactiveSourceId(currentViewData);
    };

    var isPreservedSystemViewActive = function () {
        if (!currentViewData || isRoomLikeView(currentViewData)) {
            return false;
        }
        return !(
            currentViewData.variant === "connection"
            || currentViewData.variant === "chargen"
            || currentViewData.variant === "account"
            || currentViewData.variant === "combat"
            || currentViewData.variant === "combat-result"
        );
    };

    var isStructuredMenuViewActive = function () {
        return !!(
            currentViewData
            && !isRoomLikeView(currentViewData)
            && currentViewData.variant !== "connection"
            && currentViewData.variant !== "chargen"
            && currentViewData.variant !== "account"
            && currentViewData.variant !== "combat"
            && currentViewData.variant !== "combat-result"
        );
    };

    var canRenderSceneRailNow = function () {
        return !!(
            currentViewData
            && isRoomLikeView(currentViewData)
            && document.body
            && document.body.getAttribute("data-brave-scene") === "explore"
        );
    };

    var shouldAllowCurrentRoomRefreshNavigation = function () {
        return allowNextRoomRefreshNavigationUntil > Date.now();
    };

    var findSectionByKind = function (viewData, kind) {
        if (!viewData || !Array.isArray(viewData.sections)) {
            return null;
        }
        for (var i = 0; i < viewData.sections.length; i += 1) {
            if (viewData.sections[i] && viewData.sections[i].kind === kind) {
                return viewData.sections[i];
            }
        }
        return null;
    };

    var getRoomSwipeCommands = function () {
        var roomView = getCurrentRoomView();
        var navSection = findSectionByKind(roomView, "navpad");
        var commands = {};
        if (!navSection || !Array.isArray(navSection.items)) {
            return commands;
        }
        navSection.items.forEach(function (entry) {
            if (!entry || !entry.direction || !entry.command) {
                return;
            }
            if (entry.direction === "north") {
                commands.up = entry.command;
            } else if (entry.direction === "south") {
                commands.down = entry.command;
            } else if (entry.direction === "west") {
                commands.left = entry.command;
            } else if (entry.direction === "east") {
                commands.right = entry.command;
            }
        });
        return commands;
    };

    var getMovementDirectionKey = function (entry) {
        var raw = "";
        if (entry && entry.direction) {
            raw = String(entry.direction).trim().toLowerCase();
        } else if (entry && entry.label) {
            raw = String(entry.label).trim().toLowerCase();
        } else if (entry && entry.text) {
            raw = String(entry.text).trim().toLowerCase();
        } else if (entry && entry.badge) {
            raw = String(entry.badge).trim().toLowerCase();
        }
        if (raw === "n" || raw === "north") {
            return "north";
        }
        if (raw === "s" || raw === "south") {
            return "south";
        }
        if (raw === "e" || raw === "east") {
            return "east";
        }
        if (raw === "w" || raw === "west") {
            return "west";
        }
        if (raw === "u" || raw === "up") {
            return "up";
        }
        if (raw === "d" || raw === "down") {
            return "down";
        }
        return "";
    };

    var getDesktopMovementCommands = function () {
        var roomView = getCurrentRoomView();
        var navSection = findSectionByKind(roomView, "navpad");
        var commands = {};
        var entries = [];
        if (!navSection) {
            return commands;
        }
        if (Array.isArray(navSection.items)) {
            entries = entries.concat(navSection.items);
        }
        if (Array.isArray(navSection.vertical_items)) {
            entries = entries.concat(navSection.vertical_items);
        }
        entries.forEach(function (entry) {
            var direction = getMovementDirectionKey(entry);
            if (!direction || !entry || !entry.command || commands[direction]) {
                return;
            }
            commands[direction] = entry.command;
        });
        return commands;
    };

    var isTextEntryElement = function (element) {
        if (!element || element === document.body) {
            return false;
        }
        var tagName = element.tagName ? element.tagName.toLowerCase() : "";
        if (tagName === "input" || tagName === "textarea" || tagName === "select") {
            return true;
        }
        if (element.isContentEditable) {
            return true;
        }
        if (typeof element.closest === "function" && element.closest("[contenteditable='true'], .inputwrap")) {
            return true;
        }
        return false;
    };

    var shouldHandleDesktopMovementHotkeys = function (event) {
        if (!event || isMobileViewport() || currentArcadeState) {
            return false;
        }
        if (event.altKey || event.ctrlKey || event.metaKey) {
            return false;
        }
        if (currentPickerData || isCombatUiActive()) {
            return false;
        }
        if (
            document.body.classList.contains("brave-objectives-active")
            || document.body.classList.contains("brave-picker-active")
            || document.body.classList.contains("brave-activity-active")
            || document.body.classList.contains("brave-fishing-active")
            || document.body.classList.contains("brave-arcade-overlay-active")
        ) {
            return false;
        }
        if (!getCurrentRoomView()) {
            return false;
        }
        return !isTextEntryElement(event.target || document.activeElement);
    };

    var handleDesktopMovementHotkey = function (event) {
        var command = "";
        var key = String(event && event.key ? event.key : "").toLowerCase();
        var commands = shouldHandleDesktopMovementHotkeys(event) ? getDesktopMovementCommands() : null;
        if (!commands) {
            return false;
        }
        if (key === "arrowup" || key === "w") {
            command = commands.north || "";
        } else if (key === "arrowdown" || key === "s") {
            command = commands.south || "";
        } else if (key === "arrowleft" || key === "a") {
            command = commands.west || "";
        } else if (key === "arrowright" || key === "d") {
            command = commands.east || "";
        } else if (key === "q") {
            command = commands.up || "";
        } else if (key === "e") {
            command = commands.down || "";
        }
        if (!command) {
            return false;
        }
        event.preventDefault();
        event.stopPropagation();
        sendBrowserCommand(command);
        return true;
    };

    var hasAnySwipeCommands = function (commands) {
        return !!(commands && (commands.up || commands.down || commands.left || commands.right));
    };

    var getMobileSwipeFlashSurface = function () {
        return document.querySelector("#mobile-nav-dock [data-brave-swipe-surface]");
    };

    var canStartGlobalRoomSwipe = function (target) {
        if (!ENABLE_ROOM_SWIPE_NAV) {
            return false;
        }
        if (!isMobileViewport() || !getCurrentRoomView()) {
            return false;
        }
        if (currentMobileUtilityTab || currentPickerData || isMobileCommandTrayOpen()) {
            return false;
        }
        if (!target || !target.closest) {
            return false;
        }
        if (target.closest("#mobile-nav-dock, #mobile-utility-sheet, #brave-picker-sheet, .inputwrap, .dialog, .goldenlayout-options-ui, .lm_header")) {
            return false;
        }
        // Let the room pane scroll normally on mobile. Swipe navigation now runs
        // only from the explicit swipe surface in the mobile dock.
        return false;
    };

    var renderArcadeSurface = function (section) {
        var gameKey = section && section.game_key ? section.game_key : "";
        var highScore = section && section.high_score ? section.high_score : 0;
        var bestScore = section && section.best_score ? section.best_score : 0;
        return (
            "<div class='brave-view__arcade-shell' data-arcade-game='" + escapeHtml(gameKey) + "'"
            + " data-arcade-high='" + escapeHtml(highScore) + "'"
            + " data-arcade-best='" + escapeHtml(bestScore) + "'>"
            + "<div class='brave-view__arcade-marquee'>"
            + "<div class='brave-view__arcade-scorecard'>"
            + "<span class='brave-view__arcade-score-label'>Score</span>"
            + "<span class='brave-view__arcade-score-value' data-arcade-score>0</span>"
            + "</div>"
            + "<div class='brave-view__arcade-hud'>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--high'><span class='brave-view__arcade-stat-label'>High Score</span><span class='brave-view__arcade-stat-value' data-arcade-high-score>" + escapeHtml(highScore) + "</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--lives'><span class='brave-view__arcade-stat-label'>Lives</span><span class='brave-view__arcade-stat-value' data-arcade-lives>3</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--level'><span class='brave-view__arcade-stat-label'>Level</span><span class='brave-view__arcade-stat-value' data-arcade-level>1</span></div>"
            + "</div>"
            + "</div>"
            + "<div class='brave-view__arcade-frame'>"
            + "<pre class='brave-view__arcade-screen' aria-live='polite'></pre>"
            + "</div>"
            + "<div class='brave-view__arcade-footer'>"
            + "<span class='brave-view__arcade-hint brave-view__arcade-hint--move'>Arrows or WASD steer.</span>"
            + "<div class='brave-view__arcade-footer-actions'>"
            + "<button type='button' class='brave-view__arcade-utility' data-arcade-action='pause'>Pause</button>"
            + "<button type='button' class='brave-view__arcade-utility brave-view__arcade-utility--quit' data-arcade-action='quit'>Quit</button>"
            + "</div>"
            + "</div>"
            + "<div class='brave-view__arcade-mobile-controls' aria-label='Arcade controls'>"
            + "<div class='brave-view__arcade-dpad'>"
            + "<button type='button' class='brave-view__arcade-pad brave-view__arcade-pad--up' data-arcade-input='up' aria-label='Move up'>^</button>"
            + "<button type='button' class='brave-view__arcade-pad brave-view__arcade-pad--left' data-arcade-input='left' aria-label='Move left'>&lt;</button>"
            + "<button type='button' class='brave-view__arcade-pad brave-view__arcade-pad--right' data-arcade-input='right' aria-label='Move right'>&gt;</button>"
            + "<button type='button' class='brave-view__arcade-pad brave-view__arcade-pad--down' data-arcade-input='down' aria-label='Move down'>V</button>"
            + "</div>"
            + "<div class='brave-view__arcade-mobile-actions'>"
            + "<button type='button' class='brave-view__arcade-utility' data-arcade-action='pause'>Pause</button>"
            + "<button type='button' class='brave-view__arcade-utility brave-view__arcade-utility--quit' data-arcade-action='quit'>Quit</button>"
            + "</div>"
            + "</div>"
            + "</div>"
        );
    };

    var clearArcadeOverlay = function () {
        var root = document.getElementById("brave-arcade-overlay");
        if (root && root.parentNode) {
            root.parentNode.removeChild(root);
        }
        if (document.body) {
            document.body.classList.remove("brave-arcade-overlay-active");
        }
    };

    var requestArcadeClose = function () {
        if (currentArcadeState && typeof currentArcadeState.quit === "function") {
            currentArcadeState.quit(true);
            return;
        }
        teardownArcadeMode();
    };

    var bindArcadeOverlayControls = function (root) {
        if (!root) {
            return;
        }
        root.addEventListener("click", function (event) {
            var closeTarget = event.target.closest("[data-brave-arcade-close]");
            if (!closeTarget) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            requestArcadeClose();
        }, true);
    };

    var renderArcadeOverlay = function (payload) {
        payload = payload || {};
        clearArcadeOverlay();
        if (typeof clearActivityOverlay === "function") {
            clearActivityOverlay({ suppressArcadeRestore: true });
        }
        if (typeof clearFishingMinigame === "function") {
            clearFishingMinigame();
        }
        var root = document.createElement("div");
        root.id = "brave-arcade-overlay";
        root.className = "brave-arcade-overlay";
        root.setAttribute("aria-hidden", "false");
        root.innerHTML =
            "<div class='brave-arcade-overlay__backdrop'></div>"
            + "<section class='brave-arcade-overlay__panel' role='dialog' aria-modal='true' tabindex='0'>"
            + "<div class='brave-arcade-overlay__head'>"
            + "<div class='brave-arcade-overlay__titlebar'>"
            + "<span class='brave-arcade-overlay__icon'>" + icon("sports_esports") + "</span>"
            + "<div class='brave-arcade-overlay__titles'>"
            + "<div class='brave-arcade-overlay__eyebrow'>" + escapeHtml(payload.cabinet || "Arcade Cabinet") + "</div>"
            + "<div class='brave-arcade-overlay__title'>" + escapeHtml(payload.title || "Arcade") + "</div>"
            + "</div>"
            + "</div>"
            + "<button type='button' class='brave-arcade-overlay__close brave-view__action brave-view__action--muted brave-view__back' data-brave-arcade-close='1' aria-label='Close arcade'>"
            + icon("close")
            + "</button>"
            + "</div>"
            + "<div class='brave-arcade-overlay__body'>"
            + renderArcadeSurface({
                game_key: payload.game || "",
                high_score: payload.high_score || 0,
                best_score: payload.best_score || 0,
            })
            + "</div>"
            + "</section>";
        document.body.appendChild(root);
        document.body.classList.add("brave-arcade-overlay-active");
        bindArcadeOverlayControls(root);
        var panel = root.querySelector(".brave-arcade-overlay__panel");
        if (panel && typeof panel.focus === "function") {
            panel.focus();
        }
        return root.querySelector(".brave-view__arcade-shell");
    };

    var syncArcadeBodyState = function () {
        var body = document.body;
        if (!body) {
            return;
        }
        body.classList.toggle("brave-arcade-active", !!currentArcadeState);
        body.classList.toggle("brave-arcade-mobile-active", !!currentArcadeState && isMobileViewport());
    };

    var teardownArcadeMode = function () {
        if (currentArcadeState && currentArcadeState.frameHandle && window.cancelAnimationFrame) {
            window.cancelAnimationFrame(currentArcadeState.frameHandle);
        }
        if (currentArcadeState && currentArcadeState.host) {
            currentArcadeState.host.style.removeProperty("height");
            currentArcadeState.host.style.removeProperty("max-height");
        }
        clearArcadeOverlay();
        currentArcadeState = null;
        syncArcadeBodyState();
    };

    var createMazeRunnerGame = function (host, payload) {
        var layout = [
            "############################",
            "#............##............#",
            "#.####.#####.##.#####.####.#",
            "#o####.#####.##.#####.####o#",
            "#.####.#####.##.#####.####.#",
            "#..........................#",
            "#.####.##.########.##.####.#",
            "#.####.##.########.##.####.#",
            "#......##....##....##......#",
            "######.##### ## #####.######",
            "     #.##### ## #####.#     ",
            "     #.##          ##.#     ",
            "     #.##          ##.#     ",
            "######.##          ##.######",
            "       .            .       ",
            "######.##          ##.######",
            "     #.## ######## ##.#     ",
            "     #.##          ##.#     ",
            "     #.## ######## ##.#     ",
            "######.## ######## ##.######",
            "#............##............#",
            "#.####.#####.##.#####.####.#",
            "#.####.#####.##.#####.####.#",
            "#o..##................##..o#",
            "###.##.##.########.##.##.###",
            "#......##....##....##......#",
            "#.##########.##.##########.#",
            "#.##########.##.##########.#",
            "#.##########.##.##########.#",
            "#..........................#",
            "############################",
        ];
        var width = layout[0].length;
        var height = layout.length;
        var tunnelRow = 14;
        var houseDoor = { x: 13, y: 12 };
        var houseHome = { x: 13, y: 14 };
        var houseExitY = houseDoor.y - 1;
        var playerStart = { x: 13, y: 23 };
        var fruitSpawn = { x: 13, y: 17 };
        var houseInterior = {
            "11:13": true,
            "12:13": true,
            "13:13": true,
            "14:13": true,
            "15:13": true,
            "11:14": true,
            "12:14": true,
            "13:14": true,
            "14:14": true,
            "15:14": true,
            "11:15": true,
            "12:15": true,
            "13:15": true,
            "14:15": true,
            "15:15": true,
        };
        var houseBorder = {
            "10:12": "=",
            "11:12": "=",
            "12:12": "=",
            "14:12": "=",
            "15:12": "=",
            "16:12": "=",
            "10:13": "|",
            "16:13": "|",
            "10:14": "|",
            "16:14": "|",
            "10:15": "|",
            "16:15": "|",
            "10:16": "=",
            "11:16": "=",
            "12:16": "=",
            "13:16": "=",
            "14:16": "=",
            "15:16": "=",
            "16:16": "=",
        };
        var fruitCatalog = [
            { label: "PIE", value: 100, tone: "pie" },
            { label: "KEY", value: 300, tone: "key" },
            { label: "CHARM", value: 500, tone: "charm" },
            { label: "CAP", value: 700, tone: "cap" },
            { label: "LENS", value: 1000, tone: "lens" },
            { label: "PIN", value: 1200, tone: "pin" },
        ];
        var screen = host.querySelector(".brave-view__arcade-screen");
        var frame = host.querySelector(".brave-view__arcade-frame");
        var marquee = host.querySelector(".brave-view__arcade-marquee");
        var footer = host.querySelector(".brave-view__arcade-footer");
        var mobileControls = host.querySelector(".brave-view__arcade-mobile-controls");
        var scoreNode = host.querySelector("[data-arcade-score]");
        var highScoreNode = host.querySelector("[data-arcade-high-score]");
        var livesNode = host.querySelector("[data-arcade-lives]");
        var levelNode = host.querySelector("[data-arcade-level]");
        var bonusNode = host.querySelector("[data-arcade-bonus]");
        var queueNode = host.querySelector("[data-arcade-queue]");
        var statusNode = host.querySelector("[data-arcade-status]");
        if (!screen || !frame || !scoreNode || !highScoreNode || !livesNode || !levelNode) {
            return null;
        }

        var directionByKey = {
            up: { dx: 0, dy: -1, key: "up", glyph: "^", label: "UP" },
            right: { dx: 1, dy: 0, key: "right", glyph: ">", label: "RIGHT" },
            down: { dx: 0, dy: 1, key: "down", glyph: "V", label: "DOWN" },
            left: { dx: -1, dy: 0, key: "left", glyph: "<", label: "LEFT" },
        };
        var directions = [
            directionByKey.up,
            directionByKey.right,
            directionByKey.down,
            directionByKey.left,
        ];
        var reverseByKey = {
            up: "down",
            down: "up",
            left: "right",
            right: "left",
        };
        var ghostSpecs = [
            { id: "blinky", glyph: "B", scatterTarget: { x: width - 2, y: 0 }, start: { x: 13, y: 11 }, state: "active", releaseDelay: 0 },
            { id: "pinky", glyph: "P", scatterTarget: { x: 1, y: 0 }, start: { x: 13, y: 14 }, state: "house", releaseDelay: 1200 },
            { id: "inky", glyph: "I", scatterTarget: { x: width - 2, y: height - 1 }, start: { x: 12, y: 14 }, state: "house", releaseDelay: 5200 },
            { id: "clyde", glyph: "C", scatterTarget: { x: 1, y: height - 1 }, start: { x: 14, y: 14 }, state: "house", releaseDelay: 9000 },
        ];
        var state = {
            active: true,
            frameHandle: null,
            submitPrefix: payload && payload.submit_prefix ? payload.submit_prefix : "",
            quitCommand: payload && payload.quit_command ? payload.quit_command : "arcade quit",
            highScore: parseInt(host.getAttribute("data-arcade-high"), 10) || 0,
            bestScore: parseInt(host.getAttribute("data-arcade-best"), 10) || 0,
            score: 0,
            lives: 3,
            level: 1,
            extraLifeThreshold: 10000,
            extraLifeGranted: false,
            currentMode: "scatter",
            modeSchedule: [],
            modeIndex: 0,
            modeEndsAt: 0,
            frightenedUntil: 0,
            frightenedChain: 0,
            paused: false,
            pauseStartedAt: 0,
            phase: "ready",
            phaseUntil: 0,
            eventMessage: "",
            eventMessageUntil: 0,
            bonusMessage: "",
            bonusTone: fruitCatalog[0].tone,
            bonusUntil: 0,
            fruit: null,
            fruitTriggers: [],
            fruitTriggerIndex: 0,
            pelletsRemaining: 0,
            totalPellets: 0,
            pelletsEaten: 0,
            player: null,
            ghosts: [],
            base: [],
            dots: {},
            powerPellets: {},
            moveFrame: 0,
            host: host,
        };

        var tileKey = function (x, y) {
            return x + ":" + y;
        };

        var formatNumber = function (value) {
            var safe = Math.max(0, parseInt(value, 10) || 0);
            return safe.toLocaleString("en-US");
        };

        var getFruitForLevel = function (level) {
            return fruitCatalog[Math.min(fruitCatalog.length - 1, Math.max(0, level - 1))];
        };

        var getModeScheduleForLevel = function (level) {
            if (level >= 5) {
                return [
                    { mode: "scatter", duration: 4500 },
                    { mode: "chase", duration: 20000 },
                    { mode: "scatter", duration: 4500 },
                    { mode: "chase", duration: 20000 },
                    { mode: "scatter", duration: 3500 },
                    { mode: "chase", duration: null },
                ];
            }
            if (level >= 3) {
                return [
                    { mode: "scatter", duration: 5500 },
                    { mode: "chase", duration: 20000 },
                    { mode: "scatter", duration: 5500 },
                    { mode: "chase", duration: 20000 },
                    { mode: "scatter", duration: 4000 },
                    { mode: "chase", duration: null },
                ];
            }
            return [
                { mode: "scatter", duration: 7000 },
                { mode: "chase", duration: 20000 },
                { mode: "scatter", duration: 7000 },
                { mode: "chase", duration: 20000 },
                { mode: "scatter", duration: 5000 },
                { mode: "chase", duration: null },
            ];
        };

        var getPlayerStepMs = function () {
            return Math.max(82, 114 - ((state.level - 1) * 4));
        };

        var getGhostStepMs = function (ghost) {
            if (ghost.state === "eaten") {
                return 72;
            }
            if (ghost.state === "frightened") {
                return Math.max(118, 164 - ((state.level - 1) * 2));
            }
            if (ghost.state === "house" || ghost.state === "leaving") {
                return 136;
            }
            if (ghost.y === tunnelRow) {
                return 156;
            }
            var bonus = ghost.id === "blinky" ? -6 : 0;
            return Math.max(92, 128 - ((state.level - 1) * 4) + bonus);
        };

        var getFrightenedMs = function () {
            return Math.max(1800, 5600 - ((state.level - 1) * 420));
        };

        var clearHouseArea = function () {
            delete state.dots[tileKey(houseDoor.x, houseDoor.y)];
            delete state.powerPellets[tileKey(houseDoor.x, houseDoor.y)];
            Object.keys(houseInterior).forEach(function (key) {
                delete state.dots[key];
                delete state.powerPellets[key];
            });
            Object.keys(houseBorder).forEach(function (key) {
                delete state.dots[key];
                delete state.powerPellets[key];
            });
        };

        var buildBoard = function () {
            state.base = [];
            state.dots = {};
            state.powerPellets = {};
            layout.forEach(function (row, y) {
                var baseRow = [];
                row.split("").forEach(function (cell, x) {
                    var isWall = cell === "#";
                    baseRow.push(isWall ? "#" : " ");
                    if (cell === ".") {
                        state.dots[tileKey(x, y)] = true;
                    } else if (cell === "o") {
                        state.powerPellets[tileKey(x, y)] = true;
                    }
                });
                state.base.push(baseRow);
            });
            clearHouseArea();
            state.totalPellets = Object.keys(state.dots).length + Object.keys(state.powerPellets).length;
            state.pelletsRemaining = state.totalPellets;
            state.pelletsEaten = 0;
            state.fruitTriggerIndex = 0;
            state.fruitTriggers = [
                Math.max(18, Math.floor(state.totalPellets * 0.35)),
                Math.max(36, Math.floor(state.totalPellets * 0.68)),
            ];
            state.fruit = null;
        };

        var isHouseInterior = function (x, y) {
            return !!houseInterior[tileKey(x, y)];
        };

        var isHouseBorder = function (x, y) {
            return !!houseBorder[tileKey(x, y)];
        };

        var isDoor = function (x, y) {
            return x === houseDoor.x && y === houseDoor.y;
        };

        var isWall = function (x, y) {
            if (y < 0 || y >= height || x < 0 || x >= width) {
                return true;
            }
            return state.base[y][x] === "#";
        };

        var wrapPosition = function (x, y) {
            if (y !== tunnelRow) {
                return { x: x, y: y, wrapped: false };
            }
            if (x < 0) {
                return { x: width - 1, y: y, wrapped: true };
            }
            if (x >= width) {
                return { x: 0, y: y, wrapped: true };
            }
            return { x: x, y: y, wrapped: false };
        };

        var canEnterCell = function (entity, x, y) {
            var wrapped = wrapPosition(x, y);
            x = wrapped.x;
            y = wrapped.y;
            if (isWall(x, y)) {
                return false;
            }
            if (entity.kind === "player") {
                return !isDoor(x, y) && !isHouseInterior(x, y) && !isHouseBorder(x, y);
            }
            if (entity.state === "eaten") {
                return !isHouseBorder(x, y);
            }
            if (entity.state === "house") {
                return isHouseInterior(x, y);
            }
            if (entity.state === "leaving") {
                return !isHouseBorder(x, y);
            }
            return !isDoor(x, y) && !isHouseInterior(x, y) && !isHouseBorder(x, y);
        };

        var getNextPosition = function (entity, direction) {
            if (!direction) {
                return null;
            }
            var next = wrapPosition(entity.x + direction.dx, entity.y + direction.dy);
            if (!canEnterCell(entity, next.x, next.y)) {
                return null;
            }
            return next;
        };

        var reverseDirection = function (direction) {
            if (!direction || !reverseByKey[direction.key]) {
                return null;
            }
            return directionByKey[reverseByKey[direction.key]];
        };

        var setEventMessage = function (message, now, duration) {
            state.eventMessage = message;
            state.eventMessageUntil = now + (duration || 900);
        };

        var setBonusMessage = function (message, now, duration, tone) {
            state.bonusMessage = message;
            state.bonusTone = tone || state.bonusTone;
            state.bonusUntil = now + (duration || 1400);
        };

        var addScore = function (amount, now) {
            state.score += Math.max(0, amount);
            if (state.score > state.highScore) {
                state.highScore = state.score;
            }
            if (!state.extraLifeGranted && state.score >= state.extraLifeThreshold) {
                state.extraLifeGranted = true;
                state.lives += 1;
                setEventMessage("1UP!", now, 1300);
                setBonusMessage("EXTRA LIFE", now, 1600, "life");
            }
        };

        var currentBonusLabel = function (now) {
            if (state.bonusMessage && state.bonusUntil > now) {
                return state.bonusMessage;
            }
            if (state.fruit && state.fruit.visible) {
                return state.fruit.label + " " + state.fruit.value;
            }
            var nextFruit = getFruitForLevel(state.level);
            return nextFruit.label + " " + nextFruit.value;
        };

        var currentBonusTone = function (now) {
            if (state.bonusMessage && state.bonusUntil > now) {
                return state.bonusTone || "life";
            }
            if (state.fruit && state.fruit.visible) {
                return state.fruit.tone || "pie";
            }
            return getFruitForLevel(state.level).tone || "pie";
        };

        var currentStatusLabel = function (now) {
            if (state.phase === "ready") {
                return "READY!";
            }
            if (state.phase === "dying") {
                return "CAUGHT!";
            }
            if (state.phase === "cleared") {
                return "LEVEL CLEAR";
            }
            if (state.phase === "gameover") {
                return "GAME OVER";
            }
            if (state.phase === "submitting") {
                return "CASH OUT";
            }
            if (state.paused) {
                return "PAUSED";
            }
            if (state.eventMessage && state.eventMessageUntil > now) {
                return state.eventMessage;
            }
            if (state.frightenedUntil > now) {
                return "FRIGHT!";
            }
            return state.currentMode === "scatter" ? "SCATTER" : "CHASE";
        };

        var currentStatusTone = function (now) {
            if (state.phase === "ready") {
                return "ready";
            }
            if (state.phase === "dying" || state.phase === "gameover") {
                return "danger";
            }
            if (state.phase === "cleared") {
                return "clear";
            }
            if (state.phase === "submitting") {
                return "cashout";
            }
            if (state.paused) {
                return "paused";
            }
            if (state.eventMessage && state.eventMessageUntil > now) {
                if (state.eventMessage === "FRIGHT!") {
                    return "fright";
                }
                if (state.eventMessage === "1UP!") {
                    return "life";
                }
                if (state.eventMessage === "CLEAR!") {
                    return "clear";
                }
                return "event";
            }
            if (state.frightenedUntil > now) {
                return "fright";
            }
            return state.currentMode === "scatter" ? "scatter" : "chase";
        };

        var dirDisplay = function (direction) {
            return direction ? direction.label : "NONE";
        };

        var fitScreen = function () {
            var overlayBody = host.closest(".brave-arcade-overlay__body");
            var shellRect = host.getBoundingClientRect();
            var shellTop = Math.max(0, shellRect.top);
            var viewportHeight = window.visualViewport && window.visualViewport.height
                ? Math.floor(window.visualViewport.height)
                : window.innerHeight;
            var viewportPadding = isMobileViewport() ? 8 : 18;
            var shellHeight = overlayBody
                ? Math.max(overlayBody.clientHeight || 0, isMobileViewport() ? 360 : 420)
                : Math.max(
                    isMobileViewport() ? 360 : 420,
                    Math.floor(viewportHeight - shellTop - viewportPadding)
                );
            var shellWidth = Math.max(host.clientWidth || 0, Math.floor(shellRect.width || 0));
            var layout = "default";
            if (shellHeight <= 560 || shellWidth <= 500) {
                layout = "tight";
            } else if (shellHeight <= 720 || shellWidth <= 760) {
                layout = "compact";
            }
            host.setAttribute("data-arcade-layout", layout);
            host.classList.toggle("brave-view__arcade-shell--overlay", !!overlayBody);
            host.style.height = shellHeight + "px";
            host.style.maxHeight = shellHeight + "px";

            var hostStyles = window.getComputedStyle(host);
            var hostVerticalPadding = (parseFloat(hostStyles.paddingTop) || 0) + (parseFloat(hostStyles.paddingBottom) || 0);
            var hostGap = parseFloat(hostStyles.rowGap || hostStyles.gap || 0) || 0;
            var frameStyles = window.getComputedStyle(frame);
            var frameVerticalPadding = (parseFloat(frameStyles.paddingTop) || 0) + (parseFloat(frameStyles.paddingBottom) || 0);
            var availableWidth = Math.max(200, frame.clientWidth - 12);
            var reservedHeight = hostVerticalPadding;
            var visibleSections = 0;
            var footerVisible = footer && window.getComputedStyle(footer).display !== "none";
            var controlsVisible = mobileControls && window.getComputedStyle(mobileControls).display !== "none";
            if (marquee && marquee.offsetHeight) {
                reservedHeight += marquee.offsetHeight;
                visibleSections += 1;
            }
            if (footerVisible && footer.offsetHeight) {
                reservedHeight += footer.offsetHeight;
                visibleSections += 1;
            }
            if (controlsVisible && mobileControls.offsetHeight) {
                reservedHeight += mobileControls.offsetHeight;
                visibleSections += 1;
            }
            reservedHeight += hostGap * visibleSections;
            var frameOuterHeight = Math.max(148, Math.floor(shellHeight - reservedHeight));
            var availableHeight = Math.max(132, Math.floor(frameOuterHeight - frameVerticalPadding));
            var widthFit = availableWidth / (width * 0.66);
            var heightFit = availableHeight / height;
            var minimum = isMobileViewport() ? 5.6 : 6.8;
            if (layout === "tight") {
                minimum = isMobileViewport() ? 5.1 : 6.1;
            }
            var maximum = isMobileViewport() ? 13 : 19;
            var fontSize = Math.max(minimum, Math.min(maximum, Math.floor(Math.min(widthFit, heightFit) * 100) / 100));
            var limitWidth = Math.max(0, frame.clientWidth - 2);
            var limitHeight = Math.max(0, availableHeight - 2);
            var guard = 0;

            frame.style.maxHeight = availableHeight + "px";
            frame.style.overflow = "hidden";
            screen.style.fontSize = fontSize + "px";

            // The grid math gets us close; this loop makes the final board obey the
            // actual rendered width/height so the full game stays in frame.
            while (
                guard < 24
                && fontSize > minimum
                && (screen.scrollWidth > limitWidth || screen.scrollHeight > limitHeight)
            ) {
                fontSize = Math.max(minimum, Math.floor((fontSize - 0.2) * 100) / 100);
                screen.style.fontSize = fontSize + "px";
                guard += 1;
            }
        };

        var syncPadState = function () {
            var queued = state.player && state.player.nextDir ? state.player.nextDir.key : "";
            var active = state.player && state.player.dir ? state.player.dir.key : "";
            host.querySelectorAll("[data-arcade-input]").forEach(function (button) {
                var key = button.getAttribute("data-arcade-input") || "";
                button.classList.toggle("is-queued", !!queued && key === queued);
                button.classList.toggle("is-active", !queued && !!active && key === active);
            });
            host.setAttribute("data-arcade-phase", state.phase || "ready");
            host.setAttribute("data-arcade-mode", state.currentMode || "scatter");
            host.classList.toggle("brave-view__arcade-shell--fright", state.frightenedUntil > state.lastTimestamp);
            host.classList.toggle("brave-view__arcade-shell--paused", !!state.paused);
            host.classList.toggle("brave-view__arcade-shell--danger", state.phase === "dying" || state.phase === "gameover");
        };

        var render = function (now) {
            now = now || 0;
            state.lastTimestamp = now;
            var ghostMap = {};
            state.ghosts.forEach(function (ghost) {
                ghostMap[tileKey(ghost.x, ghost.y)] = ghost;
            });
            var fruitKey = state.fruit && state.fruit.visible ? tileKey(state.fruit.x, state.fruit.y) : "";
            var lines = [];
            for (var y = 0; y < height; y += 1) {
                var line = "";
                for (var x = 0; x < width; x += 1) {
                    var key = tileKey(x, y);
                    var classes = ["brave-view__arcade-char"];
                    var glyph = " ";
                    if (state.player && state.player.x === x && state.player.y === y) {
                        classes.push("brave-view__arcade-char--player");
                        if (state.phase === "dying") {
                            classes.push("brave-view__arcade-char--player-dead");
                            glyph = (Math.floor(now / 90) % 2 === 0) ? "X" : "*";
                        } else if ((state.moveFrame % 2) === 0) {
                            glyph = state.player.dir ? state.player.dir.glyph : "O";
                        } else {
                            glyph = "O";
                        }
                    } else if (ghostMap[key]) {
                        var ghost = ghostMap[key];
                        classes.push("brave-view__arcade-char--ghost");
                        classes.push("brave-view__arcade-char--ghost-" + ghost.id);
                        if (ghost.state === "frightened") {
                            classes.push("brave-view__arcade-char--ghost-fright");
                            if ((state.frightenedUntil - now) < 1200 && Math.floor(now / 120) % 2 === 0) {
                                classes.push("brave-view__arcade-char--ghost-recover");
                            }
                            glyph = "?";
                        } else if (ghost.state === "eaten") {
                            classes.push("brave-view__arcade-char--ghost-eyes");
                            glyph = "e";
                        } else {
                            glyph = ghost.glyph;
                        }
                    } else if (fruitKey && key === fruitKey) {
                        classes.push("brave-view__arcade-char--fruit");
                        if (state.fruit && state.fruit.tone) {
                            classes.push("brave-view__arcade-char--fruit-" + state.fruit.tone);
                        }
                        glyph = "$";
                    } else if (isDoor(x, y)) {
                        classes.push("brave-view__arcade-char--door");
                        glyph = "-";
                    } else if (houseBorder[key]) {
                        classes.push("brave-view__arcade-char--house");
                        glyph = houseBorder[key];
                    } else if (state.base[y][x] === "#") {
                        classes.push("brave-view__arcade-char--wall");
                        glyph = "#";
                    } else if (state.powerPellets[key]) {
                        classes.push("brave-view__arcade-char--power");
                        glyph = "o";
                    } else if (state.dots[key]) {
                        classes.push("brave-view__arcade-char--dot");
                        glyph = ".";
                    } else {
                        classes.push("brave-view__arcade-char--empty");
                    }
                    line += "<span class='" + classes.join(" ") + "'>" + escapeHtml(glyph) + "</span>";
                }
                lines.push(line);
            }
            var bonusTone = currentBonusTone(now);
            var statusTone = currentStatusTone(now);
            screen.innerHTML = lines.join("<br>");
            scoreNode.textContent = formatNumber(state.score);
            highScoreNode.textContent = formatNumber(Math.max(state.highScore, state.bestScore));
            livesNode.textContent = String(Math.max(0, state.lives));
            levelNode.textContent = String(state.level);
            if (bonusNode) {
                bonusNode.textContent = currentBonusLabel(now);
                bonusNode.setAttribute("data-arcade-tone", bonusTone);
                host.setAttribute("data-arcade-bonus-tone", bonusTone);
            } else {
                host.removeAttribute("data-arcade-bonus-tone");
            }
            if (queueNode) {
                queueNode.textContent = dirDisplay(state.player && state.player.nextDir ? state.player.nextDir : state.player && state.player.dir ? state.player.dir : null);
            }
            if (statusNode) {
                statusNode.textContent = currentStatusLabel(now);
                statusNode.setAttribute("data-arcade-tone", statusTone);
                host.setAttribute("data-arcade-status-tone", statusTone);
            } else {
                host.removeAttribute("data-arcade-status-tone");
            }
            syncPadState();
        };

        var resetActors = function (now) {
            state.player = {
                kind: "player",
                x: playerStart.x,
                y: playerStart.y,
                prevX: playerStart.x,
                prevY: playerStart.y,
                dir: directionByKey.left,
                nextDir: directionByKey.left,
                nextMoveAt: now + getPlayerStepMs(),
            };
            state.ghosts = ghostSpecs.map(function (spec) {
                var ghost = {
                    kind: "ghost",
                    id: spec.id,
                    glyph: spec.glyph,
                    x: spec.start.x,
                    y: spec.start.y,
                    prevX: spec.start.x,
                    prevY: spec.start.y,
                    dir: spec.id === "blinky" ? directionByKey.left : directionByKey.up,
                    nextMoveAt: now + getGhostStepMs(spec),
                    state: spec.state,
                    releaseAt: now + spec.releaseDelay,
                    scatterTarget: spec.scatterTarget,
                    houseDir: spec.id === "inky" ? directionByKey.left : directionByKey.right,
                };
                ghost.nextMoveAt = now + getGhostStepMs(ghost);
                return ghost;
            });
            state.frightenedUntil = 0;
            state.frightenedChain = 0;
            state.eventMessage = "";
            state.eventMessageUntil = 0;
            state.bonusMessage = "";
            state.bonusTone = getFruitForLevel(state.level).tone || "pie";
            state.bonusUntil = 0;
            state.fruit = null;
            state.modeSchedule = getModeScheduleForLevel(state.level);
            state.modeIndex = 0;
            state.currentMode = state.modeSchedule[0].mode;
            state.modeEndsAt = state.modeSchedule[0].duration ? now + state.modeSchedule[0].duration : 0;
            state.phase = "ready";
            state.phaseUntil = now + 1450;
        };

        var startLevel = function (now) {
            buildBoard();
            resetActors(now);
        };

        var maybeSpawnFruit = function (now) {
            if (state.fruitTriggerIndex >= state.fruitTriggers.length) {
                return;
            }
            if (state.pelletsEaten < state.fruitTriggers[state.fruitTriggerIndex]) {
                return;
            }
            var fruitDef = getFruitForLevel(state.level);
            state.fruit = {
                x: fruitSpawn.x,
                y: fruitSpawn.y,
                label: fruitDef.label,
                tone: fruitDef.tone,
                value: fruitDef.value,
                visible: true,
                expiresAt: now + 8500,
            };
            state.fruitTriggerIndex += 1;
            setEventMessage(fruitDef.label + "!", now, 1000);
        };

        var maybeCollectFruit = function (now) {
            if (!state.fruit || !state.fruit.visible) {
                return;
            }
            if (state.player.x !== state.fruit.x || state.player.y !== state.fruit.y) {
                return;
            }
            addScore(state.fruit.value, now);
            setBonusMessage(state.fruit.label + " +" + state.fruit.value, now, 1700, state.fruit.tone);
            state.fruit.visible = false;
        };

        var maybeCollectPellet = function (now) {
            var key = tileKey(state.player.x, state.player.y);
            if (state.dots[key]) {
                delete state.dots[key];
                state.pelletsRemaining -= 1;
                state.pelletsEaten += 1;
                addScore(10, now);
                maybeSpawnFruit(now);
            } else if (state.powerPellets[key]) {
                delete state.powerPellets[key];
                state.pelletsRemaining -= 1;
                state.pelletsEaten += 1;
                addScore(50, now);
                maybeSpawnFruit(now);
                state.frightenedUntil = now + getFrightenedMs();
                state.frightenedChain = 0;
                state.ghosts.forEach(function (ghost) {
                    if (ghost.state === "active") {
                        ghost.state = "frightened";
                        ghost.dir = reverseDirection(ghost.dir) || ghost.dir;
                    }
                });
                setEventMessage("FRIGHT!", now, 1200);
            }
            maybeCollectFruit(now);
            if (state.pelletsRemaining <= 0) {
                addScore(1200 + ((state.level - 1) * 200), now);
                state.phase = "cleared";
                state.phaseUntil = now + 1500;
                setEventMessage("CLEAR!", now, 1500);
            }
        };

        var crossedPaths = function (ghost) {
            return ghost.x === state.player.prevX && ghost.y === state.player.prevY
                && ghost.prevX === state.player.x && ghost.prevY === state.player.y;
        };

        var collideWithGhost = function (ghost, now) {
            var sameTile = ghost.x === state.player.x && ghost.y === state.player.y;
            if (!sameTile && !crossedPaths(ghost)) {
                return false;
            }
            if (ghost.state === "frightened") {
                ghost.state = "eaten";
                ghost.dir = reverseDirection(ghost.dir) || directionByKey.up;
                state.frightenedChain += 1;
                var comboValue = [200, 400, 800, 1600][Math.min(3, state.frightenedChain - 1)];
                addScore(comboValue, now);
                setBonusMessage("GHOST +" + comboValue, now, 1500, "ghost");
                return false;
            }
            if (ghost.state === "eaten" || ghost.state === "house") {
                return false;
            }
            if (state.phase !== "running") {
                return false;
            }
            state.lives -= 1;
            state.phase = "dying";
            state.phaseUntil = now + 1250;
            state.fruit = null;
            setEventMessage("CAUGHT!", now, 1200);
            return true;
        };

        var getPlayerAheadTarget = function (distance) {
            var direction = state.player && state.player.dir ? state.player.dir : directionByKey.left;
            return {
                x: state.player.x + (direction.dx * distance),
                y: state.player.y + (direction.dy * distance),
            };
        };

        var getGhostTarget = function (ghost) {
            if (ghost.state === "eaten") {
                return { x: houseHome.x, y: houseHome.y };
            }
            if (state.currentMode === "scatter") {
                return ghost.scatterTarget;
            }
            if (ghost.id === "blinky") {
                return { x: state.player.x, y: state.player.y };
            }
            if (ghost.id === "pinky") {
                return getPlayerAheadTarget(4);
            }
            if (ghost.id === "inky") {
                var lookAhead = getPlayerAheadTarget(2);
                var blinky = state.ghosts[0];
                return {
                    x: lookAhead.x + (lookAhead.x - blinky.x),
                    y: lookAhead.y + (lookAhead.y - blinky.y),
                };
            }
            var distance = Math.abs(ghost.x - state.player.x) + Math.abs(ghost.y - state.player.y);
            if (distance > 6) {
                return { x: state.player.x, y: state.player.y };
            }
            return ghost.scatterTarget;
        };

        var getLegalDirections = function (ghost, allowReverse) {
            var reverseKey = reverseByKey[ghost.dir && ghost.dir.key];
            var options = directions.filter(function (direction) {
                if (!allowReverse && reverseKey && direction.key === reverseKey) {
                    return false;
                }
                return !!getNextPosition(ghost, direction);
            });
            if (!options.length) {
                options = directions.filter(function (direction) {
                    return !!getNextPosition(ghost, direction);
                });
            }
            return options;
        };

        var chooseGhostDirection = function (ghost, now) {
            if (ghost.state === "house") {
                if (now >= ghost.releaseAt) {
                    ghost.state = "leaving";
                    return directionByKey.up;
                }
                if (ghost.x <= 8) {
                    ghost.houseDir = directionByKey.right;
                } else if (ghost.x >= 10) {
                    ghost.houseDir = directionByKey.left;
                }
                return ghost.houseDir;
            }
            if (ghost.state === "leaving") {
                if (ghost.x < houseDoor.x) {
                    return directionByKey.right;
                }
                if (ghost.x > houseDoor.x) {
                    return directionByKey.left;
                }
                if (ghost.y > houseExitY) {
                    return directionByKey.up;
                }
                ghost.state = state.frightenedUntil > now ? "frightened" : "active";
                return ghost.dir || directionByKey.left;
            }
            var options = getLegalDirections(ghost, false);
            if (!options.length) {
                return reverseDirection(ghost.dir) || null;
            }
            if (ghost.state === "frightened") {
                return options[Math.floor(Math.random() * options.length)];
            }
            var target = getGhostTarget(ghost);
            options.sort(function (left, right) {
                var leftPos = getNextPosition(ghost, left);
                var rightPos = getNextPosition(ghost, right);
                var leftDistance = Math.pow(leftPos.x - target.x, 2) + Math.pow(leftPos.y - target.y, 2);
                var rightDistance = Math.pow(rightPos.x - target.x, 2) + Math.pow(rightPos.y - target.y, 2);
                if (leftDistance !== rightDistance) {
                    return leftDistance - rightDistance;
                }
                return left.key.localeCompare(right.key);
            });
            return options[0];
        };

        var moveEntity = function (entity, direction) {
            var next = getNextPosition(entity, direction);
            if (!next) {
                return false;
            }
            entity.prevX = entity.x;
            entity.prevY = entity.y;
            entity.x = next.x;
            entity.y = next.y;
            entity.dir = direction;
            return true;
        };

        var movePlayerStep = function (now) {
            var steps = 0;
            while (state.player.nextMoveAt <= now && steps < 3) {
                state.player.prevX = state.player.x;
                state.player.prevY = state.player.y;
                if (!moveEntity(state.player, state.player.nextDir)) {
                    moveEntity(state.player, state.player.dir);
                }
                maybeCollectPellet(now);
                state.ghosts.some(function (ghost) {
                    return collideWithGhost(ghost, now);
                });
                state.moveFrame += 1;
                state.player.nextMoveAt += getPlayerStepMs();
                steps += 1;
                if (state.phase !== "running") {
                    break;
                }
            }
        };

        var moveGhostStep = function (ghost, now) {
            var steps = 0;
            while (ghost.nextMoveAt <= now && steps < 3 && state.phase === "running") {
                if (ghost.state === "frightened" && state.frightenedUntil <= now) {
                    ghost.state = "active";
                }
                var nextDirection = chooseGhostDirection(ghost, now);
                moveEntity(ghost, nextDirection);
                if (ghost.state === "eaten" && ghost.x === houseHome.x && ghost.y === houseHome.y) {
                    ghost.state = "house";
                    ghost.releaseAt = now + 1600;
                    ghost.dir = directionByKey.left;
                }
                collideWithGhost(ghost, now);
                ghost.nextMoveAt += getGhostStepMs(ghost);
                steps += 1;
            }
        };

        var updateModeCycle = function (now) {
            if (!state.modeEndsAt || state.frightenedUntil > now) {
                return;
            }
            while (state.modeEndsAt && now >= state.modeEndsAt) {
                state.modeIndex = Math.min(state.modeSchedule.length - 1, state.modeIndex + 1);
                state.currentMode = state.modeSchedule[state.modeIndex].mode;
                state.ghosts.forEach(function (ghost) {
                    if (ghost.state === "active") {
                        ghost.dir = reverseDirection(ghost.dir) || ghost.dir;
                    }
                });
                if (state.modeSchedule[state.modeIndex].duration) {
                    state.modeEndsAt += state.modeSchedule[state.modeIndex].duration;
                } else {
                    state.modeEndsAt = 0;
                }
            }
        };

        var updateFruit = function (now) {
            if (state.fruit && state.fruit.visible && state.fruit.expiresAt <= now) {
                state.fruit.visible = false;
            }
        };

        var finishRun = function (reason) {
            if (!state.active) {
                return;
            }
            if (reason === "quit") {
                state.phase = "submitting";
            }
            state.active = false;
            render(state.lastTimestamp || 0);
            if (reason === "quit" && state.score <= 0 && !state.submitPrefix) {
                sendBrowserCommand(state.quitCommand);
                return;
            }
            if (reason === "quit" && state.score <= 0) {
                sendBrowserCommand(state.quitCommand);
                return;
            }
            if (state.submitPrefix) {
                window.setTimeout(function () {
                    sendBrowserCommand(state.submitPrefix + " " + state.score);
                }, reason === "quit" ? 260 : 1150);
                return;
            }
            if (reason === "quit") {
                sendBrowserCommand(state.quitCommand);
            }
        };

        var shiftTimers = function (delta) {
            if (!delta) {
                return;
            }
            state.phaseUntil += delta;
            state.modeEndsAt += state.modeEndsAt ? delta : 0;
            state.frightenedUntil += state.frightenedUntil ? delta : 0;
            state.eventMessageUntil += state.eventMessageUntil ? delta : 0;
            state.bonusUntil += state.bonusUntil ? delta : 0;
            if (state.fruit && state.fruit.visible) {
                state.fruit.expiresAt += delta;
            }
            if (state.player) {
                state.player.nextMoveAt += delta;
            }
            state.ghosts.forEach(function (ghost) {
                ghost.nextMoveAt += delta;
                ghost.releaseAt += ghost.releaseAt ? delta : 0;
            });
        };

        state.queueDirection = function (directionKey) {
            if (!state.player || !directionByKey[directionKey]) {
                return false;
            }
            state.player.nextDir = directionByKey[directionKey];
            render(state.lastTimestamp || 0);
            return true;
        };

        state.togglePause = function () {
            if (state.phase !== "running" && !state.paused) {
                return false;
            }
            state.paused = !state.paused;
            if (state.paused) {
                state.pauseStartedAt = state.lastTimestamp || window.performance.now();
            } else {
                shiftTimers((state.lastTimestamp || window.performance.now()) - state.pauseStartedAt);
                state.pauseStartedAt = 0;
            }
            render(state.lastTimestamp || window.performance.now());
            return true;
        };

        state.quit = function () {
            var dismissNow = arguments.length ? !!arguments[0] : false;
            finishRun("quit");
            if (dismissNow) {
                teardownArcadeMode();
            }
        };

        state.handleInput = function (key) {
            if (key === "ArrowUp" || key === "w" || key === "W") {
                return state.queueDirection("up");
            }
            if (key === "ArrowRight" || key === "d" || key === "D") {
                return state.queueDirection("right");
            }
            if (key === "ArrowDown" || key === "s" || key === "S") {
                return state.queueDirection("down");
            }
            if (key === "ArrowLeft" || key === "a" || key === "A") {
                return state.queueDirection("left");
            }
            if (key === "p" || key === "P" || key === "Escape") {
                return state.togglePause();
            }
            if (key === "q" || key === "Q") {
                state.quit();
                return true;
            }
            return false;
        };

        state.update = function (timestamp) {
            if (!state.player) {
                startLevel(timestamp);
            }
            state.lastTimestamp = timestamp;
            updateFruit(timestamp);
            if (state.paused) {
                render(timestamp);
                return;
            }
            if (state.phase === "ready") {
                if (timestamp >= state.phaseUntil) {
                    state.phase = "running";
                    state.player.nextMoveAt = timestamp + getPlayerStepMs();
                    state.ghosts.forEach(function (ghost) {
                        ghost.nextMoveAt = timestamp + getGhostStepMs(ghost);
                    });
                }
                render(timestamp);
                return;
            }
            if (state.phase === "dying") {
                if (timestamp >= state.phaseUntil) {
                    if (state.lives > 0) {
                        resetActors(timestamp);
                    } else {
                        state.phase = "gameover";
                        state.phaseUntil = timestamp + 1200;
                        render(timestamp);
                        finishRun("gameover");
                        return;
                    }
                }
                render(timestamp);
                return;
            }
            if (state.phase === "cleared") {
                if (timestamp >= state.phaseUntil) {
                    state.level += 1;
                    startLevel(timestamp);
                }
                render(timestamp);
                return;
            }
            if (state.phase === "submitting" || state.phase === "gameover") {
                render(timestamp);
                return;
            }

            if (state.frightenedUntil && timestamp >= state.frightenedUntil) {
                state.ghosts.forEach(function (ghost) {
                    if (ghost.state === "frightened") {
                        ghost.state = "active";
                    }
                });
                state.frightenedUntil = 0;
                state.frightenedChain = 0;
            }

            updateModeCycle(timestamp);
            movePlayerStep(timestamp);
            state.ghosts.forEach(function (ghost) {
                moveGhostStep(ghost, timestamp);
            });
            render(timestamp);
        };

        state.fitScreen = fitScreen;

        startLevel(window.performance.now());
        fitScreen();
        render(window.performance.now());
        return state;
    };

    var startArcadeMode = function (payload, attempt) {
        attempt = attempt || 0;
        teardownArcadeMode();

        var host = null;
        if (document.body) {
            host = renderArcadeOverlay(payload || {});
        }
        if (!host) {
            if (attempt < 10) {
                window.setTimeout(function () {
                    startArcadeMode(payload, attempt + 1);
                }, 60);
            }
            return;
        }

        if (!payload || payload.game !== "maze_runner") {
            var status = host.querySelector("[data-arcade-status]");
            if (status) {
                status.textContent = "PROGRAM MISSING";
            }
            return;
        }

        currentArcadeState = createMazeRunnerGame(host, payload);
        if (!currentArcadeState) {
            return;
        }
        syncArcadeBodyState();
        if (currentArcadeState.fitScreen) {
            currentArcadeState.fitScreen();
        }

        var tick = function (timestamp) {
            if (!currentArcadeState) {
                syncArcadeBodyState();
                return;
            }
            currentArcadeState.update(timestamp);
            if (!currentArcadeState.active && currentArcadeState.phase === "submitting") {
                syncArcadeBodyState();
                return;
            }
            currentArcadeState.frameHandle = window.requestAnimationFrame(tick);
        };
        currentArcadeState.frameHandle = window.requestAnimationFrame(tick);
    };

    var buildMobileRoomUtilityMarkup = function () {
        if (!isMobileViewport()) {
            return "";
        }
        var roomView = getCurrentRoomView();
        if (!roomView) {
            return "";
        }
        var panels = getCurrentMobilePanels(roomView);
        var character = panels.character || {};
        var pack = panels.pack || roomView.mobile_pack || {};
        var tracked = currentSceneData && currentSceneData.tracked_quest
            ? currentSceneData.tracked_quest
            : (panels.quests && panels.quests.tracked ? panels.quests.tracked : null);
        var navSection = findSectionByKind(roomView, "navpad");
        var objective = tracked && Array.isArray(tracked.objectives) && tracked.objectives.length ? tracked.objectives[0] : "";
        var routeCount = 0;
        if (navSection) {
            routeCount += Array.isArray(navSection.items) ? navSection.items.length : 0;
            routeCount += Array.isArray(navSection.vertical_items) ? navSection.vertical_items.length : 0;
            routeCount += Array.isArray(navSection.extra_items) ? navSection.extra_items.length : 0;
        }
        var routeLabel = routeCount + " route" + (routeCount === 1 ? "" : "s");
        var stateLabel = roomView.tone === "danger" ? "Danger" : "Safe";
        var stateCopy = roomView.tone === "danger" ? "Stay ready for a fight." : "No immediate threats nearby.";

        var mapMarkup =
            "<button type='button' class='brave-view__mobile-map brave-click'"
            + " data-brave-command='map' title='Open map'>"
            + "<span class='brave-view__mobile-utility-label'>Micromap</span>"
            + (currentMapGrid
                ? "<div class='brave-view__mobile-map-grid'>" + renderMapGrid(currentMapGrid, "brave-view__map-grid--compact") + "</div>"
                : (currentMapText
                    ? "<pre class='brave-view__mobile-map-pre'>" + escapeHtml(currentMapText) + "</pre>"
                    : "<div class='brave-view__mobile-map-placeholder'>" + icon("explore") + "<span>Open map</span></div>"))
            + "</button>";
        var questMarkup = (
            "<button type='button' class='brave-view__mobile-quest brave-click'"
            + " data-brave-mobile-panel='quests' title='Open quests'>"
            + "<div class='brave-view__mobile-utility-label'>Quests</div>"
            + (tracked
                ? "<div class='brave-view__mobile-quest-title'>" + escapeHtml(tracked.title || "") + "</div>"
                    + (objective ? "<div class='brave-view__mobile-quest-line'>" + escapeHtml(objective) + "</div>" : "<div class='brave-view__mobile-quest-line'>Open the journal for full objectives.</div>")
                : "<div class='brave-view__mobile-quest-title'>No tracked quest</div>"
                    + "<div class='brave-view__mobile-quest-line'>Open your journal to track one.</div>")
            + "</button>"
        );
        var statusMarkup =
            "<button type='button' class='brave-view__mobile-status' data-brave-mobile-panel='room' aria-label='Open room details'>"
            + "<div class='brave-view__mobile-utility-label'>Status</div>"
            + "<div class='brave-view__mobile-status-main'>"
            + "<span class='brave-view__mobile-status-value'>" + escapeHtml(stateLabel) + "</span>"
            + "<span class='brave-view__mobile-status-routes'>" + escapeHtml(routeLabel) + "</span>"
            + "</div>"
            + "<div class='brave-view__mobile-status-copy'>" + escapeHtml(stateCopy) + "</div>"
            + "</button>";
        var quickMarkup =
            "<div class='brave-view__mobile-quickrow'>"
            + "<button type='button' class='brave-view__mobile-quick' data-brave-mobile-panel='character'>"
            + "<span class='brave-view__mobile-utility-label'>Character</span>"
            + "<strong>" + escapeHtml(character.identity || "Open sheet") + "</strong>"
            + "</button>"
            + "<button type='button' class='brave-view__mobile-quick' data-brave-mobile-panel='pack'>"
            + "<span class='brave-view__mobile-utility-label'>Pack</span>"
            + "<strong>" + escapeHtml(String(pack.silver || 0) + " silver · " + String(pack.item_types || 0) + " types") + "</strong>"
            + "</button>"
            + "</div>";
        return "<div class='brave-view__mobile-utility'>" + mapMarkup + "<div class='brave-view__mobile-utility-side'>" + questMarkup + statusMarkup + quickMarkup + "</div></div>";
    };

    var buildMobileUtilityButton = function (key, label, iconName, active, badgeCount) {
        var activeClass = active ? " brave-mobile-tools__button--active" : "";
        var badgeMarkup = badgeCount > 0
            ? "<span class='brave-mobile-tools__button-badge' aria-label='" + escapeHtml(String(badgeCount)) + " new activity messages'>" + escapeHtml(String(badgeCount > 9 ? "9+" : badgeCount)) + "</span>"
            : "";
        return (
            "<button type='button' class='brave-mobile-tools__button" + activeClass + "' data-brave-mobile-panel='" + escapeHtml(key) + "'>"
            + icon(iconName, "brave-mobile-tools__button-icon")
            + "<span>" + escapeHtml(label) + "</span>"
            + badgeMarkup
            + "</button>"
        );
    };

    var buildMobileCommandButton = function () {
        var activeClass = isMobileCommandTrayOpen() ? " brave-mobile-tools__button--active" : "";
        var inputMode = getInputMode();
        var label = inputMode === "chat" ? "Chat" : "Command";
        var iconName = inputMode === "chat" ? "chat" : "terminal";
        return (
            "<button type='button' class='brave-mobile-tools__button brave-mobile-tools__button--command" + activeClass + "' data-brave-mobile-action='command'>"
            + icon(iconName, "brave-mobile-tools__button-icon")
            + "<span>" + escapeHtml(label) + "</span>"
            + "</button>"
        );
    };

    var buildMobileDockToolsMarkup = function () {
        var roomView = getCurrentRoomView();
        var presence = getRoomSocialPresence(roomView);
        return (
            "<div class='brave-mobile-tools'>"
            + buildMobileUtilityButton("activity", "Activity", "timeline", currentMobileUtilityTab === "activity", mobileRoomActivityUnreadCount)
            + buildMobileUtilityButton("nearby", "Nearby", "groups", currentMobileUtilityTab === "nearby", presence.nearby_total)
            + buildMobileUtilityButton("menu", "Menu", "menu", currentMobileUtilityTab === "menu")
            + "</div>"
        );
    };

    var buildMobileCommandDockMarkup = function () {
        return (
            "<div class='brave-mobile-tools brave-mobile-tools--command-only'>"
            + buildMobileCommandButton()
            + "</div>"
        );
    };

    var MOBILE_SUMMARY_TABS = [
        { key: "room", label: "Room", icon: "home" },
        { key: "pack", label: "Pack", icon: "backpack" },
        { key: "character", label: "Character", icon: "person" },
        { key: "quests", label: "Journal", icon: "menu_book" },
        { key: "party", label: "Party", icon: "groups" },
        { key: "nearby", label: "Nearby", icon: "groups" },
        { key: "menu", label: "Menu", icon: "menu" }
    ];

    var getCurrentMobilePanels = function (roomView) {
        return roomView && roomView.mobile_panels ? roomView.mobile_panels : {};
    };

    var buildMobilePanelTabStripMarkup = function (activeTab) {
        return "";
    };

    var buildMobileSummaryStatsMarkup = function (items) {
        if (!Array.isArray(items) || !items.length) {
            return "<div class='brave-mobile-sheet__empty'>No details available.</div>";
        }
        return (
            "<div class='brave-mobile-sheet__stats'>"
            + items.map(function (item) {
                return (
                    "<div class='brave-mobile-sheet__stat'>"
                    + "<span>" + escapeHtml(item && item.label ? item.label : "") + "</span>"
                    + "<strong>" + escapeHtml(item && item.value ? item.value : "") + "</strong>"
                    + "</div>"
                );
            }).join("")
            + "</div>"
        );
    };

    var buildMobileSummaryRowsMarkup = function (items, emptyText) {
        if (!Array.isArray(items) || !items.length) {
            return "<div class='brave-mobile-sheet__empty'>" + escapeHtml(emptyText || "Nothing to show.") + "</div>";
        }
        return (
            "<div class='brave-mobile-sheet__list'>"
            + items.map(function (item) {
                var interactive = !!(item && item.command);
                var tag = interactive ? "button" : "div";
                var className = "brave-mobile-sheet__row" + (interactive ? " brave-click brave-mobile-sheet__row--action" : "");
                var attrs = interactive ? commandAttrs({ command: item.command }, false) : "";
                return (
                    "<" + tag + (interactive ? " type='button'" : "") + " class='" + className + "'" + attrs + ">"
                    + "<span class='brave-mobile-sheet__row-label'>" + escapeHtml(item && item.label ? item.label : "") + "</span>"
                    + "<span class='brave-mobile-sheet__row-value'>" + escapeHtml(item && item.value ? item.value : "") + "</span>"
                    + "</" + tag + ">"
                );
            }).join("")
            + "</div>"
        );
    };

    var buildMobileSummaryBulletMarkup = function (items, emptyText) {
        if (!Array.isArray(items) || !items.length) {
            return "<div class='brave-mobile-sheet__empty'>" + escapeHtml(emptyText || "Nothing to show.") + "</div>";
        }
        return (
            "<div class='brave-mobile-sheet__list'>"
            + items.map(function (item) {
                var interactive = !!(item && item.command);
                var tag = interactive ? "button" : "div";
                var className = "brave-mobile-sheet__bullet" + (interactive ? " brave-click brave-mobile-sheet__bullet--action" : "");
                var attrs = interactive ? commandAttrs({ command: item.command }, false) : "";
                return (
                    "<" + tag + (interactive ? " type='button'" : "") + " class='" + className + "'" + attrs + ">"
                    + (item && item.badge ? "<span class='brave-mobile-sheet__bullet-badge'>" + escapeHtml(String(item.badge)) + "</span>" : "")
                    + "<span class='brave-mobile-sheet__bullet-copy'>"
                    + "<span class='brave-mobile-sheet__bullet-text'>" + escapeHtml(item && (item.text || item.label || item.title || item.name) ? (item.text || item.label || item.title || item.name) : "") + "</span>"
                    + ((item && (item.detail || item.meta || item.line || item.resource))
                        ? "<span class='brave-mobile-sheet__bullet-detail'>" + escapeHtml(item.detail || item.meta || item.line || item.resource) + "</span>"
                        : "")
                    + "</span>"
                    + "</" + tag + ">"
                );
            }).join("")
            + "</div>"
        );
    };

    var buildMobilePrimaryActionMarkup = function (label, command) {
        return (
            "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='" + escapeHtml(command) + "'>"
            + escapeHtml(label)
            + "</button>"
        );
    };

    var buildMobileRoomPanelMarkup = function (roomView) {
        var panels = getCurrentMobilePanels(roomView);
        var room = panels.room || panels;
        return (
            "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__empty brave-mobile-sheet__empty--intro'>" + escapeHtml(room.description || "") + "</div>"
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobileSummaryStatsMarkup([
                { label: "Status", value: room.status_label || "" },
                { label: "Routes", value: String(room.route_count || 0) },
                { label: "Vicinity", value: String(Array.isArray(room.vicinity) ? room.vicinity.length : 0) }
            ])
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Ways Forward</div>"
            + buildMobileSummaryBulletMarkup(room.routes || [], "No obvious routes.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>The Vicinity</div>"
            + buildMobileSummaryBulletMarkup(room.vicinity || [], "All is quiet.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobilePrimaryActionMarkup("Open Full Map", "map")
            + "</div>"
        );
    };

    var buildMobileCharacterPanelMarkup = function (roomView) {
        var panels = getCurrentMobilePanels(roomView);
        var character = panels.character || {};
        var feature = character.feature || {};
        return (
            "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>" + escapeHtml(character.name || "") + "</div>"
            + "<div class='brave-mobile-sheet__quest-meta'>" + escapeHtml(character.identity || "") + "</div>"
            + "<div class='brave-mobile-sheet__empty brave-mobile-sheet__empty--intro'>" + escapeHtml(character.summary || "") + "</div>"
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Resources</div>"
            + buildMobileSummaryRowsMarkup(character.resources || [], "No resource data.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Combat Stats</div>"
            + buildMobileSummaryStatsMarkup(character.stats || [])
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Feature Focus</div>"
            + buildMobileSummaryBulletMarkup(feature && feature.name ? [{ text: feature.name, detail: feature.summary || "" }] : [], "No feature notes.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobilePrimaryActionMarkup("Open Character Sheet", "sheet")
            + buildMobilePrimaryActionMarkup("Open Equipment", "gear")
            + "</div>"
        );
    };

    var buildMobilePackPanelMarkup = function (roomView) {
        var panels = getCurrentMobilePanels(roomView);
        var pack = panels.pack || roomView.mobile_pack || {};
        var items = [];
        (pack.sections || []).forEach(function (section) {
            items.push({
                text: section.label || "",
                detail: String(section.count || 0) + " total",
            });
            (section.items || []).forEach(function (item) {
                items.push({
                    text: item.label || "",
                    detail: "x" + String(item.quantity || 0) + (item.meta ? " · " + item.meta : ""),
                });
            });
            if (section.overflow) {
                items.push({ text: section.overflow + " more in " + section.label, detail: "" });
            }
        });
        return (
            "<div class='brave-mobile-sheet__section'>"
            + buildMobileSummaryStatsMarkup([
                { label: "Silver", value: String(pack.silver || 0) },
                { label: "Types", value: String(pack.item_types || 0) },
                { label: "Consumables", value: String(pack.consumables || 0) }
            ])
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Pack Contents</div>"
            + buildMobileSummaryBulletMarkup(items, "Pack is empty.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobilePrimaryActionMarkup("Open Full Pack", "pack")
            + "</div>"
        );
    };

    var buildMobileQuestsPanelMarkup = function (roomView) {
        var panels = getCurrentMobilePanels(roomView);
        var quests = panels.quests || {};
        var tracked = quests.tracked || null;
        var objectiveItems = tracked && Array.isArray(tracked.objectives)
            ? tracked.objectives.map(function (objective) {
                return {
                    text: objective && objective.text ? objective.text : "",
                    detail: objective && objective.completed ? "Complete" : "Active",
                };
            })
            : [];
        return (
            "<div class='brave-mobile-sheet__section'>"
            + buildMobileSummaryStatsMarkup([
                { label: "Active", value: String(quests.active_count || 0) },
                { label: "Completed", value: String(quests.completed_count || 0) },
                { label: "Tracked", value: tracked ? "Yes" : "No" }
            ])
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>" + escapeHtml(tracked ? tracked.title : "No tracked quest") + "</div>"
            + "<div class='brave-mobile-sheet__quest-meta'>" + escapeHtml(tracked && tracked.meta ? tracked.meta : "Open the journal to choose a focus.") + "</div>"
            + buildMobileSummaryBulletMarkup(objectiveItems, tracked && tracked.line ? tracked.line : "No tracked objectives.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Active Quests</div>"
            + buildMobileSummaryBulletMarkup(quests.active || [], "No active quests.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobilePrimaryActionMarkup("Open Full Journal", "quests")
            + "</div>"
        );
    };

    var buildMobilePartyPanelMarkup = function (roomView) {
        var panels = getCurrentMobilePanels(roomView);
        var party = panels.party || {};
        var memberItems = (party.members || []).map(function (member) {
            return {
                text: member.name || "",
                detail: [member.meta, member.line, member.resource].filter(Boolean).join(" · "),
            };
        });
        var inviteItems = (party.invites || []).map(function (name) {
            return { text: name, detail: "Invite pending" };
        });
        return (
            "<div class='brave-mobile-sheet__section'>"
            + buildMobileSummaryStatsMarkup([
                { label: "Party", value: party.in_party ? "Active" : "Solo" },
                { label: "Members", value: String(party.member_count || 0) },
                { label: "Leader", value: party.leader_name || "None" }
            ])
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Members</div>"
            + buildMobileSummaryBulletMarkup(memberItems, "You are not currently in a party.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + "<div class='brave-mobile-sheet__quest-title'>Invites</div>"
            + buildMobileSummaryBulletMarkup(inviteItems, "No pending invites.")
            + "</div>"
            + "<div class='brave-mobile-sheet__section'>"
            + buildMobilePrimaryActionMarkup("Open Party Screen", "party")
            + "</div>"
        );
    };

    var getMobileUtilityTabLabel = function (tab) {
        if (tab === "activity") {
            return "Activity";
        }
        return ({
            room: "Room",
            pack: "Pack",
            character: "Character",
            quests: "Journal",
            party: "Party",
            nearby: "Nearby",
            menu: "Menu"
        })[tab] || "Room";
    };

    var buildMobileSheetTabsMarkup = function () {
        return (
            "<div class='brave-mobile-sheet__tabs'>"
            + "<div class='brave-mobile-sheet__titlewrap'>"
            + "<div class='brave-mobile-sheet__eyebrow'>Brave</div>"
            + "<div class='brave-mobile-sheet__title'>" + escapeHtml(getMobileUtilityTabLabel(currentMobileUtilityTab)) + "</div>"
            + "</div>"
            + "<button type='button' class='brave-mobile-sheet__close' data-brave-mobile-action='close'>"
            + icon("close", "brave-mobile-sheet__close-icon")
            + "<span>Close</span>"
            + "</button>"
            + "</div>"
        );
    };

    var buildMobileUtilitySheetMarkup = function (tab, roomView) {
        var bodyMarkup = "";
        var panelClass = "brave-mobile-sheet__panel";
        var bodyClass = "brave-mobile-sheet__body";
        var roomActionsMarkup = "";

        if (tab === "activity") {
            panelClass += " brave-mobile-sheet__panel--activity";
            bodyClass += " brave-mobile-sheet__body--activity";
            roomActionsMarkup = buildRoomActionRailMarkup(roomView);
            bodyMarkup =
                (roomActionsMarkup
                    ? "<div class='brave-mobile-sheet__section brave-mobile-sheet__section--room-actions'>"
                        + roomActionsMarkup
                        + "</div>"
                    : "")
                + "<div class='brave-mobile-sheet__section brave-mobile-sheet__section--activity'>"
                + "<div class='brave-mobile-sheet__quest-title'>Activity</div>"
                + "<div class='brave-mobile-activity-log brave-room-log'>"
                + "<div class='brave-room-log__body brave-room-log__body--mobile' role='log' aria-live='polite' aria-relevant='additions text'>"
                + currentRoomFeedEntries.map(renderRoomFeedEntryMarkup).join("")
                + "</div>"
                + "</div>"
                + "</div>";
        } else if (tab === "room") {
            bodyMarkup = buildMobileRoomPanelMarkup(roomView);
        } else if (tab === "pack") {
            bodyMarkup = buildMobilePackPanelMarkup(roomView);
        } else if (tab === "character") {
            bodyMarkup = buildMobileCharacterPanelMarkup(roomView);
        } else if (tab === "quests") {
            bodyMarkup = buildMobileQuestsPanelMarkup(roomView);
        } else if (tab === "party") {
            bodyMarkup = buildMobilePartyPanelMarkup(roomView);
        } else if (tab === "nearby") {
            panelClass += " brave-mobile-sheet__panel--nearby";
            bodyClass += " brave-mobile-sheet__body--nearby";
            bodyMarkup =
                "<div class='brave-mobile-sheet__section'>"
                + buildRoomNearbyMarkup(roomView, { mobile: true })
                + "</div>";
        } else if (tab === "menu") {
            bodyMarkup =
                "<div class='brave-mobile-sheet__section'>"
                + buildMenuOptionsMarkup(buildDesktopMenuPicker().options)
                + "</div>";
        }

        return (
            "<div class='" + panelClass + "'>"
            + buildMobileSheetTabsMarkup()
            + (tab !== "activity" ? buildMobilePanelTabStripMarkup(tab) : "")
            + "<div class='" + bodyClass + "'>"
            + bodyMarkup
            + "</div>"
            + "</div>"
        );
    };

    var clearMobileUtilitySheet = function () {
        var host = document.getElementById("mobile-utility-sheet");
        if (host) {
            host.innerHTML = "";
            host.setAttribute("aria-hidden", "true");
        }
        document.body.classList.remove("brave-mobile-sheet-active");
    };

    var renderMobileUtilitySheet = function () {
        var host = document.getElementById("mobile-utility-sheet");
        var roomView = getCurrentRoomView();
        if (!host) {
            return;
        }
        if (!isMobileViewport() || !roomView || !currentMobileUtilityTab) {
            currentMobileUtilityTab = roomView ? currentMobileUtilityTab : null;
            clearMobileUtilitySheet();
            return;
        }

        host.innerHTML = buildMobileUtilitySheetMarkup(currentMobileUtilityTab, roomView);
        host.setAttribute("aria-hidden", "false");
        document.body.classList.add("brave-mobile-sheet-active");
        syncRoomActivityCardSurface(host, roomView, { mobile: true });
        syncRoomVoiceBubbleHosts();
        if (currentMobileUtilityTab === "activity") {
            mobileRoomActivityUnreadCount = 0;
            renderMobileNavDock();
            var activityBody = host.querySelector(".brave-room-log__body--mobile");
            if (activityBody) {
                activityBody.scrollTop = activityBody.scrollHeight;
            }
        }
    };

    var clearPickerSheet = function () {
        var host = document.getElementById("brave-picker-sheet");
        currentPickerData = null;
        currentPickerAnchorRect = null;
        currentPickerSourceId = "";
        if (host) {
            host.innerHTML = "";
            host.setAttribute("aria-hidden", "true");
        }
        if (document.body) {
            document.body.classList.remove("brave-picker-active");
        }
    };

    var clearBrowserNotice = function () {
        if (currentNoticeTimer) {
            window.clearTimeout(currentNoticeTimer);
            currentNoticeTimer = null;
        }
        var host = document.getElementById("brave-notice-stack");
        if (host) {
            host.innerHTML = "";
            host.setAttribute("aria-hidden", "true");
        }
        if (document.body) {
            document.body.classList.remove("brave-notice-active");
        }
    };

    var handleEscapeKey = function () {
        if (currentPickerData) {
            clearPickerSheet();
            return true;
        }
        if (isMobileCommandTrayOpen()) {
            closeMobileCommandTray();
            return true;
        }
        if (document.body && document.body.classList.contains("brave-notice-active")) {
            clearBrowserNotice();
            return true;
        }
        if (document.getElementById("brave-activity-overlay") && typeof clearActivityOverlay === "function") {
            clearActivityOverlay();
            return true;
        }
        if (document.getElementById("brave-fishing-minigame") && typeof clearFishingMinigame === "function") {
            clearFishingMinigame();
            return true;
        }
        if (document.getElementById("brave-arcade-overlay")) {
            requestArcadeClose();
            return true;
        }
        if (
            currentViewData
            && currentViewData.back_action
            && currentViewData.back_action.command
            && currentViewData.variant !== "connection"
            && currentViewData.variant !== "chargen"
            && currentViewData.variant !== "account"
        ) {
            sendBrowserCommand(currentViewData.back_action.command, currentViewData.back_action.confirm);
            return true;
        }
        return false;
    };

    var getNoticeIcon = function (noticeData) {
        var tone = noticeData && noticeData.tone ? noticeData.tone : "muted";
        if (noticeData && noticeData.icon) {
            return noticeData.icon;
        }
        if (tone === "good") {
            return "check_circle";
        }
        if (tone === "danger") {
            return "error";
        }
        if (tone === "warn") {
            return "warning";
        }
        return "info";
    };

    var renderBrowserNotice = function (noticeData) {
        var host = document.getElementById("brave-notice-stack");
        var lines = noticeData && Array.isArray(noticeData.lines)
            ? noticeData.lines.filter(Boolean)
            : (noticeData && noticeData.lines ? [noticeData.lines] : []);
        if (!host || !noticeData || (!noticeData.title && !lines.length)) {
            clearBrowserNotice();
            return false;
        }

        clearBrowserNotice();

        var tone = noticeData.tone ? String(noticeData.tone) : "muted";
        var duration = noticeData.duration_ms === 0
            ? 0
            : Math.max(1800, parseInt(noticeData.duration_ms || (tone === "danger" ? 5600 : 4200), 10) || 0);

        host.innerHTML =
            "<div class='brave-notice brave-notice--" + escapeHtml(tone) + "' role='status' aria-live='polite' aria-atomic='true'>"
            + "<div class='brave-notice__head'>"
            + "<div class='brave-notice__titlebar'>"
            + "<span class='brave-notice__icon'>"
            + icon(getNoticeIcon(noticeData))
            + "</span>"
            + "<div class='brave-notice__title'>" + escapeHtml(noticeData.title || "Notice") + "</div>"
            + "</div>"
            + "<button type='button' class='brave-notice__close brave-view__action brave-view__action--muted brave-view__back' data-brave-notice-close='1' aria-label='Close notice'>"
            + icon("close", "brave-view__action-icon")
            + "<span>Close</span>"
            + "</button>"
            + "</div>"
            + (lines.length
                ? "<div class='brave-notice__body'>"
                    + lines.map(function (line) {
                        return "<div class='brave-notice__line'>" + escapeHtml(line) + "</div>";
                    }).join("")
                    + "</div>"
                : "")
            + "</div>";
        host.setAttribute("aria-hidden", "false");
        document.body.classList.add("brave-notice-active");

        if (!noticeData.sticky && duration > 0) {
            currentNoticeTimer = window.setTimeout(function () {
                clearBrowserNotice();
            }, duration);
        }
        var braveAudio = getBraveAudio();
        if (braveAudio && typeof braveAudio.handleNotice === "function") {
            braveAudio.handleNotice(noticeData || {});
        }
        return true;
    };

    var renderQuestCompleteOverlay = function (payload) {
        console.log("DEBUG: renderQuestCompleteOverlay called with", payload);
        if (!payload || !payload.title) {
            return;
        }

        var overlay = document.createElement("div");
        overlay.className = "brave-quest-complete-overlay";

        var rewardItems = [];
        var rewards = payload.rewards || {};
        if (rewards.xp) rewardItems.push({ label: "Experience", value: "+" + rewards.xp });
        if (rewards.silver) rewardItems.push({ label: "Silver", value: "+" + rewards.silver });

        overlay.innerHTML =
            "<div class='brave-quest-complete-overlay__panel'>"
            + "<div class='brave-quest-complete-overlay__eyebrow'>Quest Complete</div>"
            + "<div class='brave-quest-complete-overlay__title'>" + escapeHtml(payload.title) + "</div>"
            + (rewardItems.length ?
                "<div class='brave-quest-complete-overlay__rewards'>"
                + rewardItems.map(function (reward) {
                    return (
                        "<div class='brave-quest-complete-overlay__reward'>"
                        + "<span class='brave-quest-complete-overlay__reward-label'>" + escapeHtml(reward.label) + "</span>"
                        + "<span class='brave-quest-complete-overlay__reward-value'>" + escapeHtml(reward.value) + "</span>"
                        + "</div>"
                    );
                }).join("")
                + "</div>"
                : "")
            + "</div>";

        document.body.appendChild(overlay);

        // Trigger entrance animation with a small delay for better browser reliability
        window.setTimeout(function () {
            overlay.classList.add("brave-quest-complete-overlay--active");
        }, 50);

        var braveAudio = getBraveAudio();
        if (braveAudio && typeof braveAudio.handleUiAction === "function") {
            braveAudio.handleUiAction("success");
        }

        // Automatic dismissal
        window.setTimeout(function () {
            overlay.classList.remove("brave-quest-complete-overlay--active");
            window.setTimeout(function () {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 600);
        }, 5000);
    };

    var buildAudioSettingsPicker = function () {
        return {
            picker_id: "audio-settings",
            picker_kind: "audio-settings",
            title: "Audio",
            title_icon: "graphic_eq"
        };
    };

    var buildVideoSettingsPicker = function () {
        return {
            picker_id: "video-settings",
            picker_kind: "video-settings",
            title: "Video",
            title_icon: "tv"
        };
    };

    var buildAccessibilitySettingsPicker = function () {
        return {
            picker_id: "accessibility-settings",
            picker_kind: "accessibility-settings",
            title: "Accessibility",
            title_icon: "accessibility_new"
        };
    };

    var buildSettingsPicker = function () {
        return {
            picker_id: "settings-menu",
            picker_kind: "menu",
            title: "Settings",
            title_icon: "settings",
            options: [
                { label: "Video", icon: "tv", picker: buildVideoSettingsPicker() },
                { label: "Audio", icon: "graphic_eq", picker: buildAudioSettingsPicker() },
                { label: "Accessibility", icon: "accessibility_new", picker: buildAccessibilitySettingsPicker() }
            ]
        };
    };

    var formatAudioPercent = function (value) {
        var numeric = parseFloat(value);
        if (!Number.isFinite(numeric)) {
            numeric = 0;
        }
        return Math.round(Math.max(0, Math.min(1, numeric)) * 100) + "%";
    };

    var supportsFullscreenApi = function () {
        var root = document.documentElement;
        return !!(
            root
            && (
                root.requestFullscreen
                || root.webkitRequestFullscreen
                || root.msRequestFullscreen
            )
        );
    };

    var isFullscreenActive = function () {
        return !!(
            document.fullscreenElement
            || document.webkitFullscreenElement
            || document.msFullscreenElement
        );
    };

    var toggleFullscreenMode = function () {
        var root = document.documentElement;
        if (!supportsFullscreenApi() || !root) {
            return Promise.resolve(false);
        }
        if (isFullscreenActive()) {
            if (document.exitFullscreen) {
                return Promise.resolve(document.exitFullscreen()).then(function () { return true; });
            }
            if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
                return Promise.resolve(true);
            }
            if (document.msExitFullscreen) {
                document.msExitFullscreen();
                return Promise.resolve(true);
            }
            return Promise.resolve(false);
        }
        if (root.requestFullscreen) {
            return Promise.resolve(root.requestFullscreen()).then(function () { return true; });
        }
        if (root.webkitRequestFullscreen) {
            root.webkitRequestFullscreen();
            return Promise.resolve(true);
        }
        if (root.msRequestFullscreen) {
            root.msRequestFullscreen();
            return Promise.resolve(true);
        }
        return Promise.resolve(false);
    };

    var renderVideoSettingsPickerMarkup = function (pickerData, panelClass, backdropClass, panelStyle) {
        var videoSettings = getVideoSettings();

        return (
            "<div class='" + backdropClass + "' data-brave-picker-close='1'></div>"
            + "<div class='" + panelClass + "' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Video") + "'" + panelStyle + ">"
            + "<div class='brave-picker-sheet__head'>"
            + "<div class='brave-picker-sheet__titlebar'>"
            + "<span class='brave-picker-sheet__title-icon'>" + icon(pickerData.title_icon || "tv") + "</span>"
            + "<div class='brave-picker-sheet__title'>" + escapeHtml(pickerData.title || "Video") + "</div>"
            + "<button type='button' class='brave-picker-sheet__close brave-view__action brave-view__action--muted brave-view__back' data-brave-picker-close='1'>"
            + icon("close", "brave-view__action-icon")
            + "<span>Close</span>"
            + "</button>"
            + "</div>"
            + "</div>"
            + "<div class='brave-audio-settings'>"
            + "<div class='brave-audio-settings__toggles'>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-video-action='fullscreen' aria-pressed='" + (isFullscreenActive() ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(isFullscreenActive() ? "fullscreen_exit" : "fullscreen") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>" + escapeHtml(isFullscreenActive() ? "Exit fullscreen" : "Enter fullscreen") + "</span></span>"
            + "</button>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-video-toggle='reduced_motion' aria-pressed='" + (videoSettings.reduced_motion ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(prefersReducedMotion() ? "motion_photos_off" : "motion_photos_on") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Reduce motion</span></span>"
            + "</button>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-video-action='reset'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon("restart_alt") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Reset video settings</span></span>"
            + "</button>"
            + "</div>"
            + "<div class='brave-audio-settings__sliders'>"
            + "<label class='brave-audio-settings__slider-row'>"
            + "<span class='brave-audio-settings__slider-label'>"
            + "<span class='brave-audio-settings__slider-icon'>" + icon("format_size") + "</span>"
            + "<span>UI Scale</span>"
            + "</span>"
            + "<input class='brave-audio-settings__slider' type='range' min='0.85' max='1.35' step='0.01' value='" + escapeHtml(String(videoSettings.ui_scale)) + "' data-brave-video-setting='ui_scale' data-brave-video-kind='range'>"
            + "<span class='brave-audio-settings__slider-value'>" + escapeHtml(formatScalePercent(videoSettings.ui_scale)) + "</span>"
            + "</label>"
            + "</div>"
            + "</div>"
            + "</div>"
        );
    };

    var renderAccessibilitySettingsPickerMarkup = function (pickerData, panelClass, backdropClass, panelStyle) {
        var videoSettings = getVideoSettings();

        return (
            "<div class='" + backdropClass + "' data-brave-picker-close='1'></div>"
            + "<div class='" + panelClass + "' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Accessibility") + "'" + panelStyle + ">"
            + "<div class='brave-picker-sheet__head'>"
            + "<div class='brave-picker-sheet__titlebar'>"
            + "<span class='brave-picker-sheet__title-icon'>" + icon(pickerData.title_icon || "accessibility_new") + "</span>"
            + "<div class='brave-picker-sheet__title'>" + escapeHtml(pickerData.title || "Accessibility") + "</div>"
            + "<button type='button' class='brave-picker-sheet__close brave-view__action brave-view__action--muted brave-view__back' data-brave-picker-close='1'>"
            + icon("close", "brave-view__action-icon")
            + "<span>Close</span>"
            + "</button>"
            + "</div>"
            + "</div>"
            + "<div class='brave-audio-settings'>"
            + "<div class='brave-audio-settings__toggles'>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-video-toggle='reduced_motion' aria-pressed='" + (videoSettings.reduced_motion ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(prefersReducedMotion() ? "motion_photos_off" : "motion_photos_on") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Reduce motion</span></span>"
            + "</button>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-video-action='reset'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon("restart_alt") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Reset accessibility</span></span>"
            + "</button>"
            + "</div>"
            + "<div class='brave-audio-settings__sliders'>"
            + "<label class='brave-audio-settings__slider-row'>"
            + "<span class='brave-audio-settings__slider-label'>"
            + "<span class='brave-audio-settings__slider-icon'>" + icon("format_size") + "</span>"
            + "<span>Text Scale</span>"
            + "</span>"
            + "<input class='brave-audio-settings__slider' type='range' min='0.85' max='1.35' step='0.01' value='" + escapeHtml(String(videoSettings.ui_scale)) + "' data-brave-video-setting='ui_scale' data-brave-video-kind='range'>"
            + "<span class='brave-audio-settings__slider-value'>" + escapeHtml(formatScalePercent(videoSettings.ui_scale)) + "</span>"
            + "</label>"
            + "</div>"
            + "</div>"
            + "</div>"
        );
    };

    var renderAudioSettingsPickerMarkup = function (pickerData, panelClass, backdropClass, panelStyle) {
        var braveAudio = getBraveAudio();
        var state = braveAudio ? braveAudio.getState() : {
            supported: false,
            unlocked: false,
            manifest_loaded: false,
            settings: {
                enabled: false,
                muted: true,
                reduce_repetition: true,
                master: 0,
                ambience: 0,
                music: 0,
                sfx: 0
            },
            active_layers: {
                ambience: "",
                music: ""
            }
        };
        var settingsState = state.settings || {};
        var sliders = [
            { key: "master", label: "Master", icon: "tune" },
            { key: "ambience", label: "Ambience", icon: "air" },
            { key: "music", label: "Music", icon: "music_note" },
            { key: "sfx", label: "Effects", icon: "bolt" }
        ];

        return (
            "<div class='" + backdropClass + "' data-brave-picker-close='1'></div>"
            + "<div class='" + panelClass + "' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Audio") + "'" + panelStyle + ">"
            + "<div class='brave-picker-sheet__head'>"
            + "<div class='brave-picker-sheet__titlebar'>"
            + "<span class='brave-picker-sheet__title-icon'>" + icon(pickerData.title_icon || "graphic_eq") + "</span>"
            + "<div class='brave-picker-sheet__title'>" + escapeHtml(pickerData.title || "Audio") + "</div>"
            + "<button type='button' class='brave-picker-sheet__close brave-view__action brave-view__action--muted brave-view__back' data-brave-picker-close='1'>"
            + icon("close", "brave-view__action-icon")
            + "<span>Close</span>"
            + "</button>"
            + "</div>"
            + (pickerData.subtitle ? "<div class='brave-picker-sheet__subtitle'>" + escapeHtml(pickerData.subtitle) + "</div>" : "")
            + "</div>"
            + "<div class='brave-audio-settings'>"
            + "<div class='brave-audio-settings__toggles'>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-audio-toggle='enabled' aria-pressed='" + (settingsState.enabled ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(settingsState.enabled ? "check_circle" : "radio_button_unchecked") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Audio enabled</span></span>"
            + "</button>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-audio-toggle='muted' aria-pressed='" + (settingsState.muted ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(settingsState.muted ? "volume_off" : "volume_up") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Mute all</span></span>"
            + "</button>"
            + "<button type='button' class='brave-picker-sheet__option brave-audio-settings__toggle brave-click' data-brave-audio-toggle='reduce_repetition' aria-pressed='" + (settingsState.reduce_repetition ? "true" : "false") + "'>"
            + "<span class='brave-picker-sheet__option-icon brave-audio-settings__toggle-indicator'>" + icon(settingsState.reduce_repetition ? "repeat_one" : "all_inclusive") + "</span>"
            + "<span class='brave-picker-sheet__option-body'><span class='brave-picker-sheet__option-label'>Reduce repeat SFX</span></span>"
            + "</button>"
            + "</div>"
            + "<div class='brave-audio-settings__sliders'>"
            + sliders.map(function (entry) {
                var value = settingsState[entry.key] || 0;
                return (
                    "<label class='brave-audio-settings__slider-row'>"
                    + "<span class='brave-audio-settings__slider-label'>"
                    + "<span class='brave-audio-settings__slider-icon'>" + icon(entry.icon) + "</span>"
                    + "<span>" + escapeHtml(entry.label) + "</span>"
                    + "</span>"
                    + "<input class='brave-audio-settings__slider' type='range' min='0' max='1' step='0.01' value='" + escapeHtml(String(value)) + "' data-brave-audio-setting='" + escapeHtml(entry.key) + "' data-brave-audio-kind='range'>"
                    + "<span class='brave-audio-settings__slider-value'>" + escapeHtml(formatAudioPercent(value)) + "</span>"
                    + "</label>"
                );
            }).join("")
            + "</div>"
            + "</div>"
            + "</div>"
        );
    };

    var toggleObjectives = function (force) {
        var body = document.body;
        if (!body) {
            return;
        }
        var active = typeof force === "boolean" ? force : !body.classList.contains("brave-objectives-active");
        body.classList.toggle("brave-objectives-active", active);
        var sheet = document.getElementById("brave-objectives-sheet");
        if (sheet) {
            sheet.setAttribute("aria-hidden", String(!active));
            if (!active) {
                sheet.classList.remove("brave-objectives-sheet--tutorial");
            }
        }
        if (!active) {
            currentWelcomePages = [];
            if (currentViewData && Array.isArray(currentViewData.welcome_pages)) {
                currentViewData.welcome_pages = [];
            }
        }
    };

    var renderWelcomePage = function () {
        var host = document.getElementById("brave-objectives-sheet");
        if (!host || !currentWelcomePages.length) {
            return;
        }
        host.classList.add("brave-objectives-sheet--tutorial");
        var page = currentWelcomePages[currentWelcomePageIndex];
        var isLast = currentWelcomePageIndex === currentWelcomePages.length - 1;

        host.innerHTML =
            "<div class='brave-objectives-sheet__backdrop brave-objectives-sheet__backdrop--welcome' data-brave-objectives-toggle='1'></div>"
            + "<div class='brave-objectives-sheet__panel brave-objectives-sheet__panel--welcome' role='dialog' aria-modal='true'>"
            + "<div class='brave-objectives-sheet__head'>"
            + "<div class='brave-objectives-sheet__eyebrow'>Step " + (currentWelcomePageIndex + 1) + " of " + currentWelcomePages.length + "</div>"
            + "<div class='brave-objectives-sheet__title'>" + escapeHtml(page.title) + "</div>"
            + "</div>"
            + "<div class='brave-objectives-sheet__body'>"
            + "<div class='brave-objectives-sheet__welcome-hero'>"
            + icon(page.icon || "auto_awesome", "brave-objectives-sheet__welcome-icon")
            + "</div>"
            + "<div class='brave-objectives-sheet__welcome-text'>" + escapeHtml(page.text) + "</div>"
            + "</div>"
            + "<div class='brave-objectives-sheet__foot'>"
            + (currentWelcomePageIndex > 0 ? "<button type='button' class='brave-objectives-sheet__nav-btn brave-click' data-brave-welcome-prev='1'>Back</button>" : "<div></div>")
            + "<button type='button' class='brave-objectives-sheet__nav-btn brave-objectives-sheet__nav-btn--primary brave-click' "
            + (isLast ? "data-brave-objectives-toggle='1'" : "data-brave-welcome-next='1'") + ">"
            + (isLast ? "Begin Adventure" : "Next")
            + "</button>"
            + "</div>"
            + "</div>";
    };

    var renderObjectives = function (viewData) {
        // console.log("DEBUG: renderObjectives called with", viewData);
        var host = document.getElementById("brave-objectives-sheet");
        if (!host) {
            return;
        }

        if (viewData && Array.isArray(viewData.welcome_pages) && viewData.welcome_pages.length) {
            currentWelcomePages = viewData.welcome_pages;
            currentWelcomePageIndex = 0;
            renderWelcomePage();
            toggleObjectives(true);
            return;
        }

        // If we are currently showing a welcome flow, DO NOT let anything clear it or update it
        if (document.body.classList.contains("brave-objectives-active") && currentWelcomePages.length > 0) {
            // console.log("DEBUG: skipping objective update because welcome flow is active");
            return;
        }

        var objectives = viewData && viewData.guidance;
        if (!Array.isArray(objectives) || !objectives.length) {
            host.innerHTML = "";
            host.setAttribute("aria-hidden", "true");
            document.body.classList.remove("brave-objectives-active");
            return;
        }

        var objectivesEyebrow = viewData && viewData.guidance_eyebrow ? viewData.guidance_eyebrow : "TUTORIAL";
        var objectivesTitle = viewData && viewData.guidance_title ? viewData.guidance_title : (viewData.title || viewData.eyebrow || "Current Tasks");

        host.classList.add("brave-objectives-sheet--tutorial");
        host.innerHTML =
            "<div class='brave-objectives-sheet__backdrop' data-brave-objectives-toggle='1'></div>"
            + "<div class='brave-objectives-sheet__panel' role='dialog' aria-modal='true' aria-label='Current Objectives'>"
            + "<div class='brave-objectives-sheet__head'>"
            + "<div class='brave-objectives-sheet__eyebrow'>" + escapeHtml(objectivesEyebrow) + "</div>"
            + "<div class='brave-objectives-sheet__title'>" + escapeHtml(objectivesTitle) + "</div>"
            + "<button type='button' class='brave-objectives-sheet__close' data-brave-objectives-toggle='1'>"
            + icon("close", "brave-objectives-sheet__close-icon")
            + "<span>Close Guide</span>"
            + "</button>"
            + "</div>"
            + "<div class='brave-objectives-sheet__body'>"
            + objectives.map(function (entry) {
                var text = Array.isArray(entry) ? entry[0] : String(entry);
                var entryIcon = Array.isArray(entry) && entry[1] ? entry[1] : "info";
                var isDone = entryIcon === "check_circle";
                var doneClass = isDone ? " brave-objectives-sheet__entry--done" : "";
                return (
                    "<div class='brave-objectives-sheet__entry" + doneClass + "'>"
                    + "<span class='brave-objectives-sheet__entry-icon-wrap'>"
                    + icon(entryIcon, "brave-objectives-sheet__entry-icon")
                    + "</span>"
                    + "<span class='brave-objectives-sheet__entry-text'>" + escapeHtml(text) + "</span>"
                    + "</div>"
                );
            }).join("")
            + "</div>"
            + "</div>";

        toggleObjectives(true);
    };

    var renderPickerSheet = function () {
        var host = document.getElementById("brave-picker-sheet");
        var pickerData = currentPickerData;
        var pickerOptions = pickerData && Array.isArray(pickerData.options) ? pickerData.options : [];
        var pickerBody = pickerData && Array.isArray(pickerData.body)
            ? pickerData.body.filter(Boolean)
            : (pickerData && pickerData.body ? [pickerData.body] : []);
        var anchoredMenu = !!(
            pickerData
            && pickerData.anchor === "toolbar"
            && !isMobileViewport()
            && currentPickerAnchorRect
        );
        if (!host) {
            return;
        }
        if (
            !pickerData
            || (
                !pickerOptions.length
                && !pickerBody.length
                && pickerData.picker_kind !== "audio-settings"
                && pickerData.picker_kind !== "video-settings"
                && pickerData.picker_kind !== "accessibility-settings"
            )
        ) {
            clearPickerSheet();
            return;
        }

        var panelClass = anchoredMenu
            ? "brave-picker-sheet__panel brave-picker-sheet__panel--popover"
            : "brave-picker-sheet__panel";
        var backdropClass = anchoredMenu
            ? "brave-picker-sheet__backdrop brave-picker-sheet__backdrop--clear"
            : "brave-picker-sheet__backdrop";
        var panelStyle = "";
        if (anchoredMenu) {
            var viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
            var viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
            var right = Math.max(12, Math.round(viewportWidth - currentPickerAnchorRect.right));
            var bottom = Math.max(12, Math.round(viewportHeight - currentPickerAnchorRect.top + 8));
            panelStyle = " style='right: " + right + "px; bottom: " + bottom + "px;'";
        }

        if (pickerData.picker_kind === "audio-settings") {
            host.innerHTML = renderAudioSettingsPickerMarkup(pickerData, panelClass, backdropClass, panelStyle);
        } else if (pickerData.picker_kind === "video-settings") {
            host.innerHTML = renderVideoSettingsPickerMarkup(pickerData, panelClass, backdropClass, panelStyle);
        } else if (pickerData.picker_kind === "accessibility-settings") {
            host.innerHTML = renderAccessibilitySettingsPickerMarkup(pickerData, panelClass, backdropClass, panelStyle);
        } else {
            host.innerHTML =
                "<div class='" + backdropClass + "' data-brave-picker-close='1'></div>"
                + "<div class='" + panelClass + "' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Details") + "'" + panelStyle + ">"
                + "<div class='brave-picker-sheet__head'>"
                + "<div class='brave-picker-sheet__titlebar'>"
                + (pickerData.title_icon ? "<span class='brave-picker-sheet__title-icon'>" + icon(pickerData.title_icon) + "</span>" : "")
                + "<div class='brave-picker-sheet__title'>" + escapeHtml(pickerData.title || "") + "</div>"
                + "<button type='button' class='brave-picker-sheet__close brave-view__action brave-view__action--muted brave-view__back' data-brave-picker-close='1'>"
                + icon("close", "brave-view__action-icon")
                + "<span>Close</span>"
                + "</button>"
                + "</div>"
                + (pickerData.subtitle ? "<div class='brave-picker-sheet__subtitle'>" + escapeHtml(pickerData.subtitle) + "</div>" : "")
                + "</div>"
                + (pickerBody.length
                    ? "<div class='brave-picker-sheet__bodycopy'>"
                        + pickerBody.map(function (line) {
                            return "<div class='brave-picker-sheet__bodyline'>" + escapeHtml(line) + "</div>";
                        }).join("")
                        + "</div>"
                    : "")
                + (pickerOptions.length
                    ? "<div class='brave-picker-sheet__options'>"
                        + pickerOptions.map(function (option) {
                            var toneClass = option && option.tone ? " brave-picker-sheet__option--" + escapeHtml(option.tone) : "";
                            return (
                                "<button type='button' class='brave-picker-sheet__option brave-click" + toneClass + "'"
                                + commandAttrs(option, false)
                                + ">"
                                + "<span class='brave-picker-sheet__option-icon'>"
                                + icon(option && option.icon ? option.icon : "arrow_right_alt")
                                + "</span>"
                                + "<span class='brave-picker-sheet__option-body'>"
                                + "<span class='brave-picker-sheet__option-label'>" + escapeHtml(option && option.label ? option.label : "") + "</span>"
                                + (option && option.meta ? "<span class='brave-picker-sheet__option-meta'>" + escapeHtml(option.meta) + "</span>" : "")
                                + "</span>"
                                + "</button>"
                            );
                        }).join("")
                        + "</div>"
                    : "")
                + "</div>";
        }
        host.setAttribute("aria-hidden", "false");
        document.body.classList.add("brave-picker-active");
    };

    var openPickerSheet = function (pickerData) {
        var hasOptions = !!(pickerData && Array.isArray(pickerData.options) && pickerData.options.length);
        var hasBody = !!(
            pickerData
            && (
                (Array.isArray(pickerData.body) && pickerData.body.some(Boolean))
                || (!!pickerData.body && !Array.isArray(pickerData.body))
            )
        );
        if (
            !pickerData
            || (
                !hasOptions
                && !hasBody
                && pickerData.picker_kind !== "audio-settings"
                && pickerData.picker_kind !== "video-settings"
                && pickerData.picker_kind !== "accessibility-settings"
            )
        ) {
            return false;
        }
        currentPickerData = pickerData;
        currentPickerAnchorRect = pickerData && pickerData.anchorRect ? pickerData.anchorRect : null;
        if (pickerData && pickerData.picker_id) {
            currentPickerSourceId = String(pickerData.picker_id);
        }
        renderPickerSheet();
        return true;
    };

    var openPickerFromTarget = function (target) {
        if (!target || !target.hasAttribute("data-brave-picker")) {
            return false;
        }
        try {
            var pickerData = JSON.parse(target.getAttribute("data-brave-picker"));
            var pickerSourceId = target.getAttribute("data-brave-picker-id") || (pickerData && pickerData.picker_id) || "";
            if (!isMobileViewport() && target.closest("#toolbar")) {
                var rect = target.getBoundingClientRect();
                pickerData.anchor = "toolbar";
                pickerData.anchorRect = {
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    left: rect.left,
                };
            }
            currentPickerSourceId = String(pickerSourceId || "");
            var opened = openPickerSheet(pickerData);
            var dismissSpeaker = target.getAttribute("data-brave-dismiss-bubble-speaker") || "";
            if (opened && dismissSpeaker) {
                dismissRoomVoiceBubblesForSpeaker(dismissSpeaker);
            }
            var onOpenCommand = target.getAttribute("data-brave-on-open-command") || "";
            if (opened && onOpenCommand && plugin_handler && plugin_handler.onSend) {
                plugin_handler.onSend(onOpenCommand);
            }
            return opened;
        } catch (error) {
            return false;
        }
    };

    var preserveCombatPickerOnViewRefresh = function (viewData) {
        return !!(
            currentPickerData
            && currentViewData
            && currentViewData.variant === "combat"
            && viewData
            && viewData.variant === "combat"
        );
    };

    var isMenuPickerData = function (pickerData) {
        if (!pickerData || typeof pickerData !== "object") {
            return false;
        }
        if (pickerData.picker_kind === "menu" || pickerData.picker_id === "main-menu") {
            return true;
        }
        if (pickerData.title !== "Menu" || !Array.isArray(pickerData.options)) {
            return false;
        }
        var commands = pickerData.options.map(function (option) {
            return String(option && option.command ? option.command : "").trim().toLowerCase();
        });
        return commands.indexOf("sheet") !== -1
            && commands.indexOf("gear") !== -1
            && commands.indexOf("pack") !== -1
            && commands.indexOf("quests") !== -1
            && commands.indexOf("map") !== -1
            && commands.indexOf("party") !== -1
            && commands.indexOf("quit") !== -1;
    };

    var shouldPreservePickerOnViewRefresh = function (viewData) {
        if (preserveCombatPickerOnViewRefresh(viewData)) {
            return true;
        }
        return !!(
            currentPickerData
            && isRoomLikeView(viewData)
        );
    };

    var isRoomRefreshContextActive = function () {
        return !!(
            isRoomLikeView(currentViewData)
            || isRoomLikeView(currentRoomViewData)
            || (document.body && document.body.getAttribute("data-brave-scene") === "explore")
        );
    };

    var getRoomRefreshPopupPreservationOptions = function () {
        var roomRefreshActive = isRoomRefreshContextActive();
        return {
            preservePicker: !!(roomRefreshActive && currentPickerData),
            preserveMobileSheet: !!(roomRefreshActive && currentMobileUtilityTab),
            preserveScroll: !!roomRefreshActive,
        };
    };

    var shouldPreserveMenuPickerDuringRoomClear = function () {
        return !!(
            currentPickerData
            && getRoomRefreshPopupPreservationOptions().preservePicker
        );
    };

    var syncOpenCombatPickerFromDom = function () {
        if (!currentPickerData || !currentViewData || currentViewData.variant !== "combat") {
            return;
        }
        var pickerSourceId = String(currentPickerSourceId || (currentPickerData && currentPickerData.picker_id) || "").trim();
        if (!pickerSourceId) {
            renderPickerSheet();
            return;
        }
        var matched = document.querySelector(
            ".brave-view--combat [data-brave-picker-id='" + escapeCssAttributeValue(pickerSourceId) + "']"
        );
        if (!matched) {
            renderPickerSheet();
            return;
        }
        try {
            var pickerData = JSON.parse(matched.getAttribute("data-brave-picker"));
            if (!isMobileViewport() && currentPickerData && currentPickerData.anchor === "toolbar") {
                var rect = matched.getBoundingClientRect();
                pickerData.anchor = "toolbar";
                pickerData.anchorRect = {
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    left: rect.left,
                };
            }
            currentPickerData = pickerData;
            currentPickerAnchorRect = pickerData && pickerData.anchorRect ? pickerData.anchorRect : null;
            currentPickerSourceId = pickerSourceId;
        } catch (_error) {
            // keep the existing picker data if the refreshed control can't be parsed
        }
        renderPickerSheet();
    };

    var focusCommandInput = function () {
        var inputPlugin = getDefaultInPlugin();
        var canOpenChat = !!(
            (inputPlugin && typeof inputPlugin.getInputContext === "function" && inputPlugin.getInputContext() === "play")
            || viewSupportsBottomInput(currentViewData)
            || isBottomInputSceneActive()
        );
        if (!canOpenChat) {
            return;
        }
        if (inputPlugin && typeof inputPlugin.clearChatDraft === "function") {
            inputPlugin.clearChatDraft();
        }
        if (inputPlugin && typeof inputPlugin.setInputContext === "function" && viewSupportsBottomInput(currentViewData)) {
            inputPlugin.setInputContext("play");
        }
        if (inputPlugin && typeof inputPlugin.setInputMode === "function") {
            inputPlugin.setInputMode("chat");
        }
        if (openMobileCommandTray()) {
            return;
        }
        var inputfield = getCommandInput();
        if (!inputfield.length) {
            return;
        }
        inputfield.focus();
        var element = inputfield.get(0);
        if (element && typeof element.setSelectionRange === "function") {
            var length = inputfield.val().length;
            element.setSelectionRange(length, length);
        }
    };

    var toggleMobileUtilityTab = function (tabKey) {
        if (!isMobileViewport()) {
            return;
        }
        if (tabKey === "map") {
            sendBrowserCommand("map");
            return;
        }
        if (tabKey === "quest") {
            tabKey = "quests";
        }
        closeMobileCommandTray();
        currentMobileUtilityTab = currentMobileUtilityTab === tabKey ? null : tabKey;
        if (currentMobileUtilityTab === "activity") {
            mobileRoomActivityUnreadCount = 0;
        }
        renderMobileUtilitySheet();
        renderMobileNavDock();
    };

    var handleMobileUtilityAction = function (action) {
        if (action === "command") {
            currentMobileUtilityTab = null;
            renderMobileUtilitySheet();
            if (isMobileCommandTrayOpen()) {
                closeMobileCommandTray();
                renderMobileNavDock();
                return;
            }
            renderMobileNavDock();
            focusCommandInput();
            return;
        }
        if (action === "close") {
            currentMobileUtilityTab = null;
            renderMobileUtilitySheet();
            renderMobileNavDock();
        }
    };

    var clearPackPanel = function () {
        var panel = document.getElementById("scene-pack-panel");
        if (!panel) {
            return;
        }
        panel.innerHTML = "";
        panel.classList.add("scene-rail__panel--hidden");
    };

    var clearVicinityPanel = function () {
        var panel = document.getElementById("scene-vicinity-panel");
        if (!panel) {
            return;
        }
        panel.innerHTML = "";
        panel.classList.add("scene-rail__panel--hidden");
    };

    var buildDesktopMenuPicker = function () {
        return {
            picker_id: "main-menu",
            picker_kind: "menu",
            title: "Menu",
            options: [
                { label: "Character Sheet", icon: "person", command: "sheet" },
                { label: "Equipment", icon: "shield", command: "gear" },
                { label: "Pack", icon: "backpack", command: "pack" },
                { label: "Journal", icon: "menu_book", command: "quests" },
                { label: "Map", icon: "map", command: "map" },
                { label: "Party", icon: "group", command: "party" },
                { label: "Settings", icon: "settings", picker: buildSettingsPicker() },
                { label: "Quit", icon: "logout", command: "quit", tone: "danger" }
            ]
        };
    };

    var buildMenuOptionsMarkup = function (options) {
        return (
            "<div class='brave-picker-sheet__options brave-mobile-sheet__menu-options'>"
            + (options || []).map(function (option) {
                var toneClass = option && option.tone ? " brave-picker-sheet__option--" + escapeHtml(option.tone) : "";
                return (
                    "<button type='button' class='brave-picker-sheet__option brave-click" + toneClass + "'"
                    + commandAttrs(option, false)
                    + ">"
                    + "<span class='brave-picker-sheet__option-icon'>"
                    + icon(option && option.icon ? option.icon : "menu")
                    + "</span>"
                    + "<span class='brave-picker-sheet__option-body'>"
                    + "<span class='brave-picker-sheet__option-label'>" + escapeHtml(option && option.label ? option.label : "") + "</span>"
                    + (option && option.meta ? "<span class='brave-picker-sheet__option-meta'>" + escapeHtml(option.meta) + "</span>" : "")
                    + "</span>"
                    + "</button>"
                );
            }).join("")
            + "</div>"
        );
    };

    var positionDesktopToolbar = function () {
        var toolbar = document.getElementById("toolbar");
        if (!toolbar || toolbar.getAttribute("aria-hidden") !== "false" || isMobileViewport() || !isBottomInputSceneActive()) {
            return;
        }
        var inputWrap = document.querySelector(".inputwrap");
        if (!inputWrap) {
            return;
        }
        var inputRect = inputWrap.getBoundingClientRect();
        var toolbarHeight = toolbar.offsetHeight || 40;
        var top = Math.max(12, Math.round(inputRect.top - toolbarHeight - 12));
        toolbar.style.top = top + "px";
        toolbar.style.right = "22px";
        toolbar.style.bottom = "auto";
        toolbar.style.left = "auto";
        if (currentPickerData && currentPickerData.anchor === "toolbar") {
            var button = toolbar.querySelector(".brave-toolbar__button");
            if (button) {
                var rect = button.getBoundingClientRect();
                currentPickerAnchorRect = {
                    top: rect.top,
                    right: rect.right,
                    bottom: rect.bottom,
                    left: rect.left,
                };
                renderPickerSheet();
            }
        }
    };

    var positionSceneRail = function () {
        var rail = document.getElementById("scene-rail");
        var host = document.getElementById("main-sub");
        if (!rail || !host) {
            return;
        }
        if (
            isMobileViewport()
            || !currentViewData
            || !isRoomLikeView(currentViewData)
            || document.body.getAttribute("data-brave-scene") !== "explore"
        ) {
            rail.style.removeProperty("bottom");
            return;
        }

        var roomView = document.querySelector("#messagewindow > .brave-sticky-view > .brave-view--room")
            || document.querySelector("#messagewindow > .brave-view--room");
        if (!roomView) {
            rail.style.removeProperty("bottom");
            return;
        }

        var navSection = roomView.querySelector(".brave-view__section--navpad");
        var vicinitySection = roomView.querySelector(".brave-view__section--vicinity");
        if (!navSection || !vicinitySection) {
            rail.style.removeProperty("bottom");
            return;
        }

        var hostRect = host.getBoundingClientRect();
        var rowBottom = Math.max(
            navSection.getBoundingClientRect().bottom,
            vicinitySection.getBoundingClientRect().bottom
        );
        rail.style.bottom = Math.max(0, Math.round(hostRect.bottom - rowBottom)) + "px";
    };

    var renderDesktopToolbar = function () {
        var toolbar = document.getElementById("toolbar");
        if (!toolbar) {
            return;
        }
        toolbar.innerHTML = "";
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.style.removeProperty("top");
        toolbar.style.removeProperty("right");
        toolbar.style.removeProperty("bottom");
        toolbar.style.removeProperty("left");
    };

    var getMapPayloadState = function (payload) {
        var raw = "";
        var grid = null;
        if (typeof payload === "string") {
            raw = payload;
        } else if (payload && typeof payload === "object") {
            if (typeof payload.map_text === "string") {
                raw = payload.map_text;
            } else if (typeof payload.text === "string") {
                raw = payload.text;
            }
            if (payload.map_tiles && typeof payload.map_tiles === "object") {
                grid = payload.map_tiles;
            } else if (payload.grid && typeof payload.grid === "object") {
                grid = payload.grid;
            }
        }
        return {
            text: raw.replace(/\n+$/, ""),
            grid: grid,
        };
    };

    var renderMicromapMarkup = function (payload, extraClass) {
        var state = getMapPayloadState(payload);
        if (state.text) {
            return escapeHtml(state.text);
        }
        var mapMarkup = state.grid ? renderMapGrid(state.grid, extraClass || "brave-view__map-grid--micro") : "";
        if (mapMarkup) {
            return mapMarkup;
        }
        return "";
    };

    var renderRoomCardMicromap = function (payload) {
        var state = getMapPayloadState(payload);
        if (!state.grid || !Array.isArray(state.grid.rows) || !state.grid.rows.length) {
            return state.text ? escapeHtml(state.text) : "";
        }
        var columns = state.grid.columns || (Array.isArray(state.grid.rows[0]) ? state.grid.rows[0].length : 0);
        if (!columns) {
            return state.text ? escapeHtml(state.text) : "";
        }
        var cells = [];
        state.grid.rows.forEach(function (row) {
            (Array.isArray(row) ? row : []).forEach(function (cell) {
                var tile = cell && typeof cell === "object" ? cell : {};
                var kind = tile.kind || "empty";
                var classes = "brave-view__room-micromap-cell brave-view__room-micromap-cell--" + escapeHtml(kind);
                var body = "";
                var title = tile.title ? " title='" + escapeHtml(tile.title) + "'" : "";

                if (kind === "connector") {
                    var axis = tile.axis === "vertical" ? "vertical" : "horizontal";
                    classes += " brave-view__room-micromap-cell--connector-" + escapeHtml(axis);
                    body = "<span class='brave-view__room-micromap-connector brave-view__room-micromap-connector--" + escapeHtml(axis) + "'></span>";
                } else if (kind === "room") {
                    var symbol = String(tile.symbol || "");
                    if (symbol === "player") {
                        classes += " brave-view__room-micromap-cell--player";
                        body = "<span class='brave-view__room-micromap-node brave-view__room-micromap-node--player'>"
                            + icon("player", "brave-view__room-micromap-player-icon")
                            + "</span>";
                    } else if (symbol === "double-team") {
                        classes += " brave-view__room-micromap-cell--party";
                        body = "<span class='brave-view__room-micromap-node brave-view__room-micromap-node--party'></span>";
                    } else {
                        body = "<span class='brave-view__room-micromap-node'></span>";
                    }
                }

                cells.push("<span class='" + classes + "'" + title + ">" + body + "</span>");
            });
        });
        return "<div class='brave-view__room-micromap-grid' style='--brave-room-micromap-columns: " + columns + ";'>" + cells.join("") + "</div>";
    };

    var renderMap = function (payload) {
        var micromaps = document.querySelectorAll(".brave-view__micromap");
        var state = getMapPayloadState(payload);
        currentMapText = state.text;
        currentMapGrid = state.grid;
        if (micromaps.length) {
            micromaps.forEach(function (micromap) {
                var mapMarkup = renderRoomCardMicromap(payload);
                if (mapMarkup) {
                    micromap.innerHTML = mapMarkup;
                    micromap.setAttribute("aria-hidden", "false");
                } else {
                    micromap.textContent = currentMapText;
                    micromap.setAttribute("aria-hidden", String(!currentMapText.trim()));
                }
            });
        }
        syncSceneRailLayout();
        syncMobileShell();
    };

    var clearMicromap = function () {
        var micromaps = document.querySelectorAll(".brave-view__micromap");
        currentMapGrid = null;
        micromaps.forEach(function (micromap) {
            micromap.innerHTML = "";
            micromap.textContent = "";
            micromap.setAttribute("aria-hidden", "true");
        });
    };

    var syncSceneRailLayout = function () {
        var rail = document.getElementById("scene-rail");
        var card = document.getElementById("scene-card");
        var packPanel = document.getElementById("scene-pack-panel");
        var vicinityPanel = document.getElementById("scene-vicinity-panel");
        if (!rail) {
            return;
        }

        var hasCard = !!(card && card.textContent && card.textContent.trim());
        var hasPack = !!(packPanel && packPanel.textContent && packPanel.textContent.trim());
        var hasVicinity = !!(vicinityPanel && vicinityPanel.textContent && vicinityPanel.textContent.trim());
        if (window.matchMedia && window.matchMedia("(max-width: 1099px)").matches) {
            hasCard = false;
            hasVicinity = false;
        }

        if (packPanel) {
            packPanel.classList.toggle("scene-rail__panel--hidden", !hasPack);
        }
        if (vicinityPanel) {
            vicinityPanel.classList.toggle("scene-rail__panel--hidden", !hasVicinity);
        }

        rail.classList.toggle("scene-rail--vicinity-hidden", !hasVicinity);
        rail.classList.toggle("scene-rail--pack-hidden", !hasPack);
        rail.classList.toggle("scene-rail--card-hidden", !hasCard);
        rail.classList.toggle("scene-rail--detail-hidden", !hasCard && !hasPack && !hasVicinity);
        rail.classList.toggle("scene-rail--empty", !hasCard && !hasPack && !hasVicinity);
        if (window.requestAnimationFrame) {
            window.requestAnimationFrame(positionSceneRail);
        } else {
            positionSceneRail();
        }
    };

    var escapeHtml = function (value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    var ICON_MAP = {
        // People & Social
        "person": "player",
        "person_add": "player-lift",
        "person_off": "player-despair",
        "groups": "double-team",
        "diversity_3": "all-for-one",
        "person_pin": "player",
        "assignment_ind": "scroll-unfurled",
        "forum": "speech-bubbles",

        // Actions & UI
        "play_arrow": "forward",
        "delete": "demolish",
        "palette": "kaleidoscope",
        "tune": "gears",
        "check_circle": "check",
        "radio_button_unchecked": "circle-of-circles",
        "task_alt": "on-target",
        "checklist": "on-target",
        "remove_circle": "health-decrease",
        "block": "cancel",
        "chevron_right": "forward",
        "arrow_right_alt": "forward",
        "arrow_forward": "forward",
        "arrow_back": "reverse",
        "settings": "gears",
        "save": "save",
        "near_me": "on-target",
        "alt_route": "divert",
        "location_searching": "targeted",
        "flag": "castle-flag",
        "assignment": "scroll-unfurled",
        "info": "help",
        "help": "help",
        "search": "searching",
        "close": "cancel",
        "menu": "hamburger",
        "more_vert": "dots-vertical",
        "more_horiz": "dots-horizontal",
        "login": "key",
        "logout": "unplugged",
        "schedule": "hourglass",
        "edit_note": "quill-ink",
        "star_outline": "trophy",
        "school": "book",
        "straighten": "arrow-cluster",
        "north_east": "forward",
        "military_tech": "trophy",
        "leaderboard": "trophy",

        // Combat & Adventure
        "swords": "crossed-swords",
        "shield": "shield",
        "favorite": "hearts",
        "directions_run": "player-dodge",
        "directions_walk": "walking-boot",
        "backpack": "ammo-bag",
        "inventory_2": "mine-wagon",
        "category": "cubes",
        "layers": "doubled",
        "lock": "key",
        "key": "key",
        "bolt": "lightning-bolt",
        "auto_awesome": "aura",
        "warning": "uncertainty",
        "sports_esports": "gamepad-cross",
        "videogame_asset": "gamepad-cross",
        "construction": "anvil",
        "build": "wrench",
        "do_not_disturb_on": "cancel",
        "group": "double-team",
        "groups": "double-team",
        "visibility": "eyeball",
        "visibility_off": "cloak-and-dagger",
        "power_off": "unplugged",

        // Nature & Elements
        "forest": "pine-tree",
        "air": "fizzing-flask",
        "local_fire_department": "fire",
        "public": "ocean-emblem",
        "eco": "sprout",
        "water": "water-drop",
        "wb_sunny": "sun",

        // Objects & Places
        "savings": "gold-bar",
        "sell": "gold-bar",
        "storefront": "wooden-sign",
        "church": "capitol",
        "restaurant": "knife-fork",
        "soup_kitchen": "knife-fork",
        "lunch_dining": "meat",
        "label": "wooden-sign",
        "menu_book": "book",
        "article": "scroll-unfurled",
        "quill": "quill-ink",
        "spellcheck": "quill-ink",
        "badge": "scroll-unfurled",
        "home": "guarded-tower",
        "home_pin": "guarded-tower",
        "place": "guarded-tower",

        // Navigation
        "travel_explore": "compass",
        "explore": "compass",
        "route": "trail",
        "map": "scroll-unfurled",
    };

    var icon = function (name, extraClass) {
        if (name === "check_box" || name === "check_box_outline_blank") {
            var checkboxClasses = "brave-icon brave-icon--checkbox";
            if (name === "check_box") {
                checkboxClasses += " brave-icon--checkbox-checked";
            } else {
                checkboxClasses += " brave-icon--checkbox-unchecked";
            }
            if (extraClass) {
                checkboxClasses += " " + extraClass;
            }
            return "<span class='" + checkboxClasses + "' aria-hidden='true'></span>";
        }
        if (name === "sentiment_satisfied") {
            var smileClasses = "brave-icon brave-icon--smile";
            if (extraClass) {
                smileClasses += " " + extraClass;
            }
            return "<span class='" + smileClasses + "' aria-hidden='true'></span>";
        }
        if (name === "check_circle" || name === "task_alt") {
            var checkClasses = "brave-icon brave-icon--check-circle";
            if (extraClass) {
                checkClasses += " " + extraClass;
            }
            return "<span class='" + checkClasses + "' aria-hidden='true'></span>";
        }
        if (name === "trash") {
            var trashClasses = "brave-icon brave-icon--trash";
            if (extraClass) {
                trashClasses += " " + extraClass;
            }
            return "<span class='" + trashClasses + "' aria-hidden='true'></span>";
        }
        var raName = ICON_MAP[name] || name.replace(/_/g, "-");
        var classes = "ra ra-" + raName;
        if (extraClass) {
            classes += " " + extraClass;
        }
        return "<i class='" + classes + "' aria-hidden='true'></i>";
    };

    var normalizeThemeKey = function (themeKey) {
        var raw = typeof themeKey === "string" ? themeKey.trim().toLowerCase() : "";
        if (THEME_PRESETS[raw]) {
            return raw;
        }
        if (THEME_ALIASES[raw] && THEME_PRESETS[THEME_ALIASES[raw]]) {
            return THEME_ALIASES[raw];
        }
        return "hearth";
    };

    var commandAttrs = function (entry, includeRole) {
        if (!entry || (!entry.command && !entry.prefill && !entry.picker && !entry.connection_screen && !entry.chat_open)) {
            return "";
        }
        var attrs = "";
        var titleValue = entry && entry.tooltip ? entry.tooltip : "";
        if (entry.command) {
            attrs += " data-brave-command='" + escapeHtml(entry.command) + "'";
            if (!titleValue) {
                titleValue = entry.command;
            }
        }
        if (entry.prefill) {
            attrs += " data-brave-prefill='" + escapeHtml(entry.prefill) + "'";
            if (!titleValue) {
                titleValue = entry.prefill;
            }
        }
        if (entry.chat_open) {
            attrs += " data-brave-chat-open='1'";
        }
        if (entry.chat_prompt) {
            attrs += " data-brave-chat-prompt='" + escapeHtml(entry.chat_prompt) + "'";
        }
        if (entry.picker) {
            attrs += " data-brave-picker='" + escapeHtml(JSON.stringify(entry.picker)) + "'";
            if (entry.picker.picker_id) {
                attrs += " data-brave-picker-id='" + escapeHtml(String(entry.picker.picker_id)) + "'";
            }
            if (!titleValue && entry.label) {
                titleValue = entry.label;
            }
        }
        if (entry.on_open_command) {
            attrs += " data-brave-on-open-command='" + escapeHtml(entry.on_open_command) + "'";
        }
        if (entry.dismiss_bubble_speaker) {
            attrs += " data-brave-dismiss-bubble-speaker='" + escapeHtml(entry.dismiss_bubble_speaker) + "'";
        }
        if (entry.connection_screen) {
            attrs += " data-brave-connection-screen='" + escapeHtml(entry.connection_screen) + "'";
            if (!titleValue && (entry.text || entry.label || entry.title)) {
                titleValue = entry.text || entry.label || entry.title;
            }
        }
        if (titleValue) {
            attrs += " title='" + escapeHtml(titleValue) + "'";
        }
        if (entry.confirm) {
            attrs += " data-brave-confirm='" + escapeHtml(entry.confirm) + "'";
        }
        if (includeRole !== false) {
            attrs += " role='button' tabindex='0'";
        }
        return attrs;
    };

    var getMobileDirectionLabel = function (entry) {
        if (!entry) {
            return "";
        }
        if (entry.label) {
            return entry.label;
        }
        switch (entry.direction) {
            case "north":
                return "North";
            case "south":
                return "South";
            case "east":
                return "East";
            case "west":
                return "West";
            case "up":
                return "Up";
            case "down":
                return "Down";
            default:
                return entry.badge || "";
        }
    };

    var getMobileDirectionAriaLabel = function (entry) {
        if (!entry) {
            return "";
        }
        var directionLabel = getMobileDirectionLabel(entry);
        if (entry.label && entry.label !== directionLabel) {
            return directionLabel + " to " + entry.label;
        }
        return directionLabel || entry.label || "";
    };

    var renderMobileNavButton = function (entry, positionClass) {
        if (!entry || !entry.command) {
            return "<div class='brave-view__navslot " + positionClass.replace("navcard", "navslot") + "'></div>";
        }
        var label = getMobileDirectionLabel(entry);
        var ariaLabel = getMobileDirectionAriaLabel(entry);
        return (
            "<button type='button' class='brave-view__navcard brave-click " + positionClass + "'"
            + commandAttrs(entry, false)
            + (ariaLabel ? " aria-label='" + escapeHtml(ariaLabel) + "'" : "")
            + ">"
            + "<span class='brave-view__navcard-badge'>" + escapeHtml(entry.badge || "") + "</span>"
            + "<span class='brave-view__navcard-label'>" + escapeHtml(label) + "</span>"
            + "</button>"
        );
    };

    var renderMobileNavCenter = function (items) {
        if (!Array.isArray(items) || !items.length) {
            return "<div class='brave-view__navcenter'></div>";
        }
        var visibleItems = items.slice(0, 2);
        var wrapClass = "brave-view__nav-centerstack";
        if (visibleItems.length === 1) {
            wrapClass += " brave-view__nav-centerstack--single";
        }
        return (
            "<div class='brave-view__navcenter'>"
            + "<div class='" + wrapClass + "'>"
            + visibleItems.map(function (entry) {
                var label = getMobileDirectionLabel(entry);
                var ariaLabel = getMobileDirectionAriaLabel(entry);
                return (
                    "<button type='button' class='brave-view__nav-centercard brave-click'"
                    + commandAttrs(entry, false)
                    + (ariaLabel ? " aria-label='" + escapeHtml(ariaLabel) + "'" : "")
                    + ">"
                    + "<span class='brave-view__nav-chip-badge'>" + escapeHtml(entry.badge || "") + "</span>"
                    + "<span class='brave-view__nav-centercard-label'>" + escapeHtml(label) + "</span>"
                    + "</button>"
                );
            }).join("")
            + "</div>"
            + "</div>"
        );
    };

    var renderMobileOtherRoutes = function (items) {
        if (!Array.isArray(items) || !items.length) {
            return "";
        }
        return (
            "<div class='brave-view__nav-extra brave-view__nav-extra--routes'>"
            + items.map(function (entry) {
                return (
                    "<button type='button' class='brave-view__nav-chip brave-click'"
                    + commandAttrs(entry, false)
                    + ">"
                    + icon(entry && entry.icon ? entry.icon : "route", "brave-view__nav-chip-icon")
                    + "<span class='brave-view__nav-chip-label'>" + escapeHtml(entry && entry.text ? entry.text : entry && entry.label ? entry.label : "") + "</span>"
                    + "</button>"
                );
            }).join("")
            + "</div>"
        );
    };

    var renderMobileNavPad = function (section) {
        var entryMap = {};
        (section && section.items ? section.items : []).forEach(function (entry) {
            if (entry && entry.direction) {
                entryMap[entry.direction] = entry;
            }
        });

        return (
            "<div class='brave-view__navpad brave-view__navpad--mobile'>"
            + "<div class='brave-view__navgrid brave-view__navgrid--mobile'>"
            + renderMobileNavButton(entryMap.north, "brave-view__navcard--north")
            + renderMobileNavButton(entryMap.west, "brave-view__navcard--west")
            + renderMobileNavCenter(section && section.vertical_items)
            + renderMobileNavButton(entryMap.east, "brave-view__navcard--east")
            + renderMobileNavButton(entryMap.south, "brave-view__navcard--south")
            + "</div>"
            + renderMobileOtherRoutes(section && section.extra_items)
            + "</div>"
        );
    };

    var hasBrowserInteraction = function (entry) {
        return !!(entry && (entry.command || entry.prefill || entry.picker || entry.connection_screen || entry.chat_open));
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

    var prefillBrowserInput = function (value) {
        var normalized = String(value || "");
        if (normalized && normalized.charAt(0) !== "/") {
            normalized = "/" + normalized;
        }
        var inputPlugin = getDefaultInPlugin();
        if (inputPlugin && typeof inputPlugin.setInputValue === "function") {
            inputPlugin.setInputValue(normalized, { mode: "chat" });
            return;
        }
        var inputfield = getCommandInput();
        if (!inputfield.length) {
            return;
        }
        inputfield.focus();
        inputfield.val(normalized);
        var element = inputfield.get(0);
        if (element && typeof element.setSelectionRange === "function") {
            var length = inputfield.val().length;
            element.setSelectionRange(length, length);
        }
    };

    var htmlToPlainText = function (html) {
        var element = document.createElement("div");
        element.innerHTML = html || "";
        return (element.textContent || element.innerText || "")
            .replace(/\u00a0/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    };

    var isConnectionScreenText = function (html) {
        var text = htmlToPlainText(html).toLowerCase();
        return (
            text.indexOf("brave") !== -1
            && text.indexOf("connect <username> <password>") !== -1
            && text.indexOf("create <username> <password>") !== -1
            && text.indexOf("character creation happens after login.") !== -1
        );
    };

    var isConnectionScreenFragment = function (html) {
        var text = htmlToPlainText(html).toLowerCase();
        if (!text) {
            return false;
        }
        return (
            text === "brave"
            || text.indexOf("connect <username> <password>") !== -1
            || text.indexOf("sign in to an existing account.") !== -1
            || text.indexOf("create <username> <password>") !== -1
            || text.indexOf("create a new account. character creation happens after login.") !== -1
            || text.indexOf("help for more options.") !== -1
        );
    };

    var buildConnectionViewData = function () {
        var mode = currentConnectionScreen || "menu";
        if (mode === "signin") {
            return {
                variant: "connection",
                wordmark: "BRAVE",
                eyebrow: "Sign In",
                eyebrow_icon: "login",
                title: "",
                title_icon: null,
                subtitle: "",
                chips: [],
                actions: [
                    { text: "Back", icon: "arrow_back", connection_screen: "menu", tone: "muted" },
                ],
                sections: [
                    {
                        label: "Sign In",
                        icon: "login",
                        kind: "form",
                        fields: [
                            {
                                field_name: "username",
                                field_label: "Username",
                                placeholder: "Username",
                                autocomplete: "username",
                                autocapitalize: "none",
                                spellcheck: false,
                                autofocus: true,
                            },
                            {
                                field_name: "password",
                                field_label: "Password",
                                input_type: "password",
                                placeholder: "Password",
                                autocomplete: "current-password",
                                autocapitalize: "none",
                                spellcheck: false,
                                enterkeyhint: "go",
                            },
                        ],
                        submit_template: "connect {username} {password}",
                        submit_label: "Sign In",
                        submit_icon: "login",
                    },
                ],
                reactive: {
                    scene: "account",
                    world_tone: "neutral",
                },
            };
        }
        if (mode === "create") {
            return {
                variant: "connection",
                wordmark: "BRAVE",
                eyebrow: "Create Account",
                eyebrow_icon: "person_add",
                title: "",
                title_icon: null,
                subtitle: "",
                chips: [],
                actions: [
                    { text: "Back", icon: "arrow_back", connection_screen: "menu", tone: "muted" },
                ],
                sections: [
                    {
                        label: "Create Account",
                        icon: "person_add",
                        kind: "form",
                        fields: [
                            {
                                field_name: "username",
                                field_label: "Username",
                                placeholder: "Choose a username",
                                autocomplete: "username",
                                autocapitalize: "none",
                                spellcheck: false,
                                autofocus: true,
                            },
                            {
                                field_name: "password",
                                field_label: "Password",
                                input_type: "password",
                                placeholder: "Choose a password",
                                autocomplete: "new-password",
                                autocapitalize: "none",
                                spellcheck: false,
                                enterkeyhint: "next",
                            },
                            {
                                field_name: "password_confirm",
                                field_label: "Confirm Password",
                                input_type: "password",
                                placeholder: "Repeat your password",
                                autocomplete: "new-password",
                                autocapitalize: "none",
                                spellcheck: false,
                                enterkeyhint: "go",
                            },
                        ],
                        submit_template: "create {username} {password} {password_confirm}",
                        submit_label: "Create Account",
                        submit_icon: "person_add",
                    },
                ],
                reactive: {
                    scene: "account",
                    world_tone: "neutral",
                },
            };
        }
        return {
            variant: "connection",
            wordmark: "BRAVE",
            eyebrow: "",
            eyebrow_icon: null,
            title: "",
            title_icon: null,
            subtitle: "",
            chips: [],
            actions: [],
            sections: [
                {
                    label: "Enter Brave",
                    icon: "key",
                    kind: "list",
                    items: [
                        {
                            text: "Sign In",
                            icon: "key",
                            connection_screen: "signin",
                        },
                        {
                            text: "Create Account",
                            icon: "quill",
                            connection_screen: "create",
                        },
                    ],
                },
            ],
            reactive: {
                scene: "account",
                world_tone: "neutral",
            },
        };
    };

    var isLegacyConnectionBoilerplate = function (text) {
        var normalized = String(text || "").toLowerCase().replace(/\s+/g, " ").trim();
        if (!normalized) {
            return false;
        }
        return (
            normalized === "brave"
            || normalized.indexOf("connect <username> <password>") !== -1
            || normalized.indexOf("sign in to an existing account.") !== -1
            || normalized.indexOf("create <username> <password>") !== -1
            || normalized.indexOf("create a new account. character creation happens after login.") !== -1
            || normalized.indexOf("help for more options.") !== -1
        );
    };

    var pruneLegacyConnectionBoilerplate = function () {
        var mwin = document.getElementById("messagewindow");
        if (!mwin) {
            return;
        }
        Array.prototype.slice.call(mwin.childNodes).forEach(function (child) {
            if (!child) {
                return;
            }
            if (child.nodeType === Node.TEXT_NODE) {
                if (isLegacyConnectionBoilerplate(child.textContent || "")) {
                    child.remove();
                }
                return;
            }
            if (child.nodeType !== Node.ELEMENT_NODE) {
                return;
            }
            if (child.classList.contains("brave-view") || child.classList.contains("brave-sticky-view")) {
                return;
            }
            if (
                isLegacyConnectionBoilerplate(child.textContent || "")
                || isLegacyConnectionBoilerplate(child.innerText || "")
                || isLegacyConnectionBoilerplate(child.innerHTML || "")
            ) {
                child.remove();
            }
        });
    };

    var ensureConnectionBoilerplateObserver = function () {
        var mwin = document.getElementById("messagewindow");
        if (!window.MutationObserver || !mwin) {
            return;
        }
        if (connectionBoilerplateObserver) {
            connectionBoilerplateObserver.disconnect();
        }
        connectionBoilerplateObserver = new MutationObserver(function () {
            if (currentViewData && currentViewData.variant === "connection") {
                pruneLegacyConnectionBoilerplate();
            }
        });
        connectionBoilerplateObserver.observe(mwin, {
            childList: true,
            subtree: false,
            characterData: true,
        });
    };

    var ensureRoomActivityObserver = function () {
        var mwin = document.getElementById("messagewindow");
        if (!window.MutationObserver || !mwin) {
            return;
        }
        if (roomActivityObserver) {
            roomActivityObserver.disconnect();
        }
        roomActivityObserver = new MutationObserver(function () {
            if (isCombatUiActive()) {
                clearVicinityPanel();
                syncSceneRailLayout();
                return;
            }
            if (!isRoomLikeView(currentViewData)) {
                return;
            }
            ensureRoomActivityLog();
        });
        roomActivityObserver.observe(mwin, {
            childList: true,
            subtree: false,
        });
    };

    var claimCombatLogEntries = function () {
        var mwin = $("#messagewindow");
        var claimedCount = 0;
        if (!mwin.length) {
            return claimedCount;
        }

        var logBody = ensureCombatLog();
        if (!logBody || !logBody.length) {
            return claimedCount;
        }

        var logBodyNode = logBody.get(0);
        syncCombatLogScrollState(logBodyNode);
        var shouldStickToBottom = combatLogPinnedToBottom;

        var strayEntries = mwin.children(".out, .msg, .err, .sys, .inp");
        if (!strayEntries.length) {
            return claimedCount;
        }

        logBody.append(strayEntries);
        strayEntries.each(function () {
            applyCombatFloatersFromNode(this);
        });
        claimedCount = strayEntries.length;
        restoreCombatLogScroll(logBodyNode, shouldStickToBottom);
        updateCombatLogCue();
        return claimedCount;
    };

    var normalizeCombatName = function (value) {
        return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
    };

    var extractCombatFxMarkers = function (rawText) {
        var events = [];
        var cleaned = String(rawText || "").replace(/\s*\[\[BRAVEFX ([^\]]+)\]\]/g, function (_full, payload) {
            var params = new URLSearchParams(String(payload || ""));
            var event = {};
            params.forEach(function (value, key) {
                event[key] = value;
            });
            if (Object.keys(event).length) {
                events.push(event);
            }
            return "";
        });
        return {
            html: cleaned,
            events: events,
        };
    };

    var getCombatEntryNodes = function () {
        return Array.prototype.slice.call(document.querySelectorAll(".brave-view--combat [data-entry-ref]"));
    };

    var getCombatEntryRef = function (node) {
        return node ? (node.getAttribute("data-entry-ref") || "") : "";
    };

    var escapeCssAttributeValue = function (value) {
        return String(value || "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    };

    var findCombatEntryByRef = function (ref) {
        if (!ref) {
            return null;
        }
        return document.querySelector(".brave-view--combat [data-entry-ref='" + escapeCssAttributeValue(ref) + "']");
    };

    var getCombatAtbMeter = function (node) {
        return node ? node.querySelector(".brave-view__meter[data-meter-kind='atb']") : null;
    };

    var suppressCombatEntryRef = function (ref) {
        if (!ref) {
            return;
        }
        suppressedCombatEntryRefs[ref] = true;
        var styleId = "brave-suppress-" + ref.replace(/[^a-zA-Z0-9-]/g, "-");
        if (!document.getElementById(styleId)) {
            var style = document.createElement("style");
            style.id = styleId;
            style.textContent = ".brave-view--combat [data-entry-ref='" + ref + "'] { visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }";
            document.head.appendChild(style);
        }
    };

    var clearSuppressedCombatEntryRefs = function () {
        suppressedCombatEntryRefs = {};
        Array.prototype.slice.call(document.head.querySelectorAll("style[id^='brave-suppress-']")).forEach(function (style) {
            if (style && style.parentNode) {
                style.parentNode.removeChild(style);
            }
        });
    };

    var applySuppressedCombatEntries = function () {
        Object.keys(suppressedCombatEntryRefs).forEach(function (ref) {
            var node = document.querySelector(".brave-view--combat [data-entry-ref='" + ref + "']");
            if (node && node.parentNode) {
                node.parentNode.removeChild(node);
            }
        });
    };

    var getFillWidthPercent = function (fill) {
        if (!fill || !fill.getBoundingClientRect) {
            return null;
        }
        var track = fill.parentElement;
        if (!track || !track.getBoundingClientRect) {
            return null;
        }
        var trackRect = track.getBoundingClientRect();
        var fillRect = fill.getBoundingClientRect();
        if (!(trackRect.width > 0)) {
            return null;
        }
        return Math.max(0, Math.min(100, (fillRect.width / trackRect.width) * 100));
    };

    var getCombatAtbFillPercent = function (node) {
        var meter = getCombatAtbMeter(node);
        var fill = meter ? meter.querySelector(".brave-view__meter-fill") : null;
        if (!fill) {
            return null;
        }
        var renderedPercent = getFillWidthPercent(fill);
        if (renderedPercent != null && !isNaN(renderedPercent)) {
            return renderedPercent;
        }
        var gauge = parseFloat(meter.getAttribute("data-atb-gauge") || "0");
        var ready = Math.max(1, parseFloat(meter.getAttribute("data-atb-ready") || "400"));
        return Math.max(0, Math.min(100, (gauge / ready) * 100));
    };

    var captureCombatEntrySnapshot = function (node) {
        if (!node || !node.getBoundingClientRect) {
            return null;
        }
        var rect = node.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return null;
        }
        var meter = getCombatAtbMeter(node);
        return {
            ref: getCombatEntryRef(node),
            rect: {
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
            },
            html: node.outerHTML,
            atbPercent: getCombatAtbFillPercent(node),
            atbPhase: meter ? (meter.getAttribute("data-atb-phase") || "charging") : "",
            atbPhaseStartedAt: meter ? (meter.getAttribute("data-atb-phase-started-at") || "") : "",
        };
    };

    var collectCombatEntryRefsFromMarkup = function (markup) {
        var refs = {};
        String(markup || "").replace(/data-entry-ref='([^']+)'/g, function (_full, ref) {
            if (ref) {
                refs[ref] = true;
            }
            return _full;
        });
        return refs;
    };

    var queueCombatFxEvents = function (events) {
        if (!Array.isArray(events) || !events.length) {
            return;
        }
        pendingCombatFxEvents = pendingCombatFxEvents.concat(events).slice(-24);
        scheduleCombatFxFlush(0);
    };

    var scheduleCombatFxFlush = function (delayMs) {
        delayMs = Math.max(0, delayMs || 0);
        if (pendingCombatFxFlushTimeout) {
            if (delayMs > 0) {
                return;
            }
            window.clearTimeout(pendingCombatFxFlushTimeout);
            pendingCombatFxFlushTimeout = null;
        }
        pendingCombatFxFlushTimeout = window.setTimeout(function () {
            pendingCombatFxFlushTimeout = null;
            window.requestAnimationFrame(function () {
                flushPendingCombatFxEvents();
            });
        }, delayMs);
    };

    var getCombatEntryTitle = function (node) {
        var titleNode = node ? node.querySelector(".brave-view__entry-title") : null;
        return titleNode ? titleNode.textContent || "" : "";
    };

    var findCombatEntryByName = function (name) {
        var normalized = normalizeCombatName(name);
        if (!normalized) {
            return null;
        }
        var matches = getCombatEntryNodes().filter(function (node) {
            return normalizeCombatName(getCombatEntryTitle(node)) === normalized;
        });
        if (matches.length) {
            return matches[0];
        }
        var contains = getCombatEntryNodes().filter(function (node) {
            return normalized.indexOf(normalizeCombatName(getCombatEntryTitle(node))) >= 0
                || normalizeCombatName(getCombatEntryTitle(node)).indexOf(normalized) >= 0;
        });
        return contains.length ? contains[0] : null;
    };

    var findCombatEntryForEvent = function (event, role) {
        if (!event) {
            return null;
        }
        var refNode = findCombatEntryByRef(event[role + "_ref"]);
        if (refNode) {
            return refNode;
        }
        return findCombatEntryByName(event[role]);
    };

    var getCombatFxOverlayRoot = function () {
        var overlay = document.getElementById("brave-combat-fx-overlay");
        if (overlay) {
            return overlay;
        }
        overlay = document.createElement("div");
        overlay.id = "brave-combat-fx-overlay";
        overlay.className = "brave-view brave-view--combat brave-combat-fx-overlay";
        overlay.style.position = "fixed";
        overlay.style.left = "0";
        overlay.style.top = "0";
        overlay.style.width = "100vw";
        overlay.style.height = "100vh";
        overlay.style.pointerEvents = "none";
        overlay.style.zIndex = "980";
        overlay.style.overflow = "visible";
        document.body.appendChild(overlay);
        return overlay;
    };

    var clearCombatFxOverlay = function () {
        var overlay = document.getElementById("brave-combat-fx-overlay");
        if (overlay && overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    };

    var createCombatOverlayBox = function (rect, extraClass) {
        if (!rect || !rect.width || !rect.height) {
            return null;
        }
        var overlay = getCombatFxOverlayRoot();
        var box = document.createElement("div");
        box.className = extraClass || "";
        box.style.position = "fixed";
        box.style.left = rect.left + "px";
        box.style.top = rect.top + "px";
        box.style.width = rect.width + "px";
        box.style.height = rect.height + "px";
        box.style.pointerEvents = "none";
        box.style.overflow = "visible";
        overlay.appendChild(box);
        return box;
    };

    var createCombatGhostElement = function (snapshot, extraClasses) {
        if (!snapshot || !snapshot.rect) {
            return null;
        }
        var host = createCombatOverlayBox(snapshot.rect, "brave-combat-ghost-host");
        if (!host) {
            return null;
        }
        host.style.zIndex = "995";
        host.innerHTML = snapshot.html || "";
        var ghost = host.firstElementChild;
        if (!ghost) {
            if (host.parentNode) {
                host.parentNode.removeChild(host);
            }
            return null;
        }
        ghost.removeAttribute("data-entry-ref");
        ghost.classList.add("brave-combat-ghost");
        if (Array.isArray(extraClasses)) {
            extraClasses.forEach(function (className) {
                if (className) {
                    ghost.classList.add(className);
                }
            });
        }
        ghost.style.width = "100%";
        ghost.style.height = "100%";
        ghost.style.margin = "0";
        ghost.style.pointerEvents = "none";
        return { host: host, ghost: ghost };
    };

    var removeCombatOverlayNodeLater = function (node, delayMs) {
        window.setTimeout(function () {
            if (node && node.parentNode) {
                node.parentNode.removeChild(node);
            }
        }, Math.max(0, delayMs || 0));
    };

    var spawnCombatFloaterFromSnapshot = function (snapshot, text, tone, element) {
        if (!snapshot || !text) {
            return;
        }
        var host = createCombatOverlayBox(snapshot.rect, "brave-combat-floater-host");
        if (!host) {
            return;
        }
        host.style.zIndex = "997";
        var floater = document.createElement("span");
        floater.className = "brave-combat-floater brave-combat-floater--" + (tone || "neutral");
        var driftX = ((Math.random() * 18) - 9).toFixed(2) + "px";
        var driftY = (18 + (Math.random() * 12)).toFixed(2) + "px";
        var popScale = (1.06 + (Math.random() * 0.16)).toFixed(2);
        floater.style.setProperty("--brave-floater-drift-x", driftX);
        floater.style.setProperty("--brave-floater-rise-y", driftY);
        floater.style.setProperty("--brave-floater-pop-scale", popScale);
        if (element) {
            floater.classList.add("brave-combat-floater--element-" + element);
        }
        floater.textContent = text;
        host.appendChild(floater);
        removeCombatOverlayNodeLater(host, 1300);
    };

    var animateCombatImpactFromSnapshot = function (snapshot, tone, element) {
        if (!snapshot) {
            return;
        }
        var created = createCombatGhostElement(snapshot);
        if (!created || !created.ghost) {
            return;
        }
        var ghost = created.ghost;
        var host = created.host;
        var impactTone = tone || "damage";
        var durationMs = impactTone === "break" ? 340 : impactTone === "miss" ? 280 : 320;
        var animationName = {
            damage: "brave-combat-impact-damage",
            heal: "brave-combat-impact-heal",
            guard: "brave-combat-impact-guard",
            break: "brave-combat-impact-break",
            miss: "brave-combat-impact-miss",
        }[impactTone] || "brave-combat-impact-damage";
        var rgbKey = element || impactTone;
        if (COMBAT_IMPACT_RGB[rgbKey]) {
            ghost.style.setProperty("--brave-impact-rgb", COMBAT_IMPACT_RGB[rgbKey]);
        }
        ghost.style.animation = animationName + " " + durationMs + "ms ease-out 1";
        removeCombatOverlayNodeLater(host, durationMs + 80);
    };

    var animateCombatLungeFromSnapshots = function (attackerSnapshot, targetSnapshot) {
        if (!attackerSnapshot || !targetSnapshot || !attackerSnapshot.rect || !targetSnapshot.rect) {
            return;
        }
        var created = createCombatGhostElement(attackerSnapshot);
        if (!created || !created.ghost) {
            return;
        }
        var ghost = created.ghost;
        var host = created.host;
        var attackerRect = attackerSnapshot.rect;
        var targetRect = targetSnapshot.rect;
        var dx = (targetRect.left + (targetRect.width / 2)) - (attackerRect.left + (attackerRect.width / 2));
        var dy = (targetRect.top + (targetRect.height / 2)) - (attackerRect.top + (attackerRect.height / 2));
        var magnitude = Math.sqrt((dx * dx) + (dy * dy));
        if (!magnitude) {
            if (host.parentNode) {
                host.parentNode.removeChild(host);
            }
            return;
        }
        var lungeDistance = Math.min(18, Math.max(8, magnitude * 0.08));
        ghost.style.setProperty("--brave-combat-lunge-x", ((dx / magnitude) * lungeDistance).toFixed(2) + "px");
        ghost.style.setProperty("--brave-combat-lunge-y", ((dy / magnitude) * lungeDistance).toFixed(2) + "px");
        ghost.style.willChange = "transform";
        ghost.style.animation = "brave-combat-card-lunge 300ms cubic-bezier(0.2, 0.86, 0.24, 1) 1";
        removeCombatOverlayNodeLater(host, 360);
    };

    var parseMarkupRoot = function (markup) {
        var shell = document.createElement("div");
        shell.innerHTML = String(markup || "");
        return shell.firstElementChild;
    };

    var syncElementAttributes = function (target, source, options) {
        options = options || {};
        var preserve = options.preserve || {};
        Array.prototype.slice.call(target.attributes || []).forEach(function (attr) {
            if (preserve[attr.name]) {
                return;
            }
            if (!source.hasAttribute(attr.name)) {
                target.removeAttribute(attr.name);
            }
        });
        Array.prototype.slice.call(source.attributes || []).forEach(function (attr) {
            if (preserve[attr.name]) {
                return;
            }
            target.setAttribute(attr.name, attr.value);
        });
    };

    var patchCombatEntryNode = function (target, source) {
        if (!target || !source) {
            return;
        }
        var preservedClasses = Array.prototype.slice.call(target.classList || []).filter(function (className) {
            return className === "brave-view__entry--lunge"
                || className === "brave-view__entry--defeating"
                || className.indexOf("brave-view__entry--impact-") === 0;
        });
        syncElementAttributes(target, source, { preserve: { style: true } });
        target.className = source.className;
        preservedClasses.forEach(function (className) {
            target.classList.add(className);
        });
        if (target.hasAttribute("data-combat-cluster-ref") && source.hasAttribute("data-combat-cluster-ref")) {
            var targetMain = target.querySelector(":scope > .brave-view__entry");
            var sourceMain = source.querySelector(":scope > .brave-view__entry");
            var targetSidecars = target.querySelector(":scope > .brave-view__entry-sidecars");
            var sourceSidecars = source.querySelector(":scope > .brave-view__entry-sidecars");
            if (targetMain && sourceMain) {
                patchCombatEntryNode(targetMain, sourceMain);
            }
            if (targetSidecars && sourceSidecars) {
                reconcileCombatEntryCollection(targetSidecars, sourceSidecars);
            } else if (targetSidecars && !sourceSidecars) {
                targetSidecars.parentNode.removeChild(targetSidecars);
            } else if (!targetSidecars && sourceSidecars) {
                target.appendChild(sourceSidecars.cloneNode(true));
            }
            return;
        }
        target.innerHTML = source.innerHTML;
    };

    var getCombatCollectionKey = function (node) {
        if (!node || !node.getAttribute) {
            return "";
        }
        return node.getAttribute("data-combat-cluster-ref") || node.getAttribute("data-entry-ref") || "";
    };

    var reconcileCombatEntryCollection = function (targetEntries, sourceEntries) {
        if (!targetEntries || !sourceEntries) {
            return;
        }
        var currentChildren = Array.prototype.slice.call(targetEntries.children || []);
        var currentByRef = {};
        currentChildren.forEach(function (child) {
            var ref = getCombatCollectionKey(child);
            if (ref) {
                currentByRef[ref] = child;
            }
        });
        var nextOrder = [];
        Array.prototype.slice.call(sourceEntries.children || []).forEach(function (sourceChild) {
            var ref = getCombatCollectionKey(sourceChild);
            var currentChild = ref ? currentByRef[ref] : null;
            if (currentChild) {
                patchCombatEntryNode(currentChild, sourceChild);
                nextOrder.push(currentChild);
                delete currentByRef[ref];
            } else {
                nextOrder.push(sourceChild.cloneNode(true));
            }
        });
        currentChildren.forEach(function (child) {
            if (child.parentNode === targetEntries) {
                targetEntries.removeChild(child);
            }
        });
        nextOrder.forEach(function (child) {
            targetEntries.appendChild(child);
        });
    };

    var patchCombatStickyView = function (stickyNode, markup) {
        var currentView = stickyNode ? stickyNode.querySelector(".brave-view--combat") : null;
        var nextView = parseMarkupRoot(markup);
        if (!currentView || !nextView) {
            return false;
        }
        syncElementAttributes(currentView, nextView);
        currentView.className = nextView.className;

        var currentHero = currentView.querySelector(".brave-view__hero");
        var nextHero = nextView.querySelector(".brave-view__hero");
        if (currentHero && nextHero) {
            currentHero.innerHTML = nextHero.innerHTML;
        }

        var currentSectionsWrap = currentView.querySelector(".brave-view__sections");
        var nextSectionsWrap = nextView.querySelector(".brave-view__sections");
        if (!currentSectionsWrap || !nextSectionsWrap) {
            currentView.innerHTML = nextView.innerHTML;
            return true;
        }

        var currentSections = Array.prototype.slice.call(currentSectionsWrap.children || []).filter(function (section) {
            return !section.classList || !section.classList.contains("brave-combat-log");
        });
        var nextSections = Array.prototype.slice.call(nextSectionsWrap.children || []).filter(function (section) {
            return !section.classList || !section.classList.contains("brave-combat-log");
        });
        if (currentSections.length !== nextSections.length) {
            currentView.innerHTML = nextView.innerHTML;
            return true;
        }

        for (var index = 0; index < nextSections.length; index += 1) {
            var currentSection = currentSections[index];
            var nextSection = nextSections[index];
            if (!currentSection || !nextSection) {
                currentView.innerHTML = nextView.innerHTML;
                return true;
            }
            syncElementAttributes(currentSection, nextSection);
            currentSection.className = nextSection.className;
            var currentLabel = currentSection.querySelector(".brave-view__section-label");
            var nextLabel = nextSection.querySelector(".brave-view__section-label");
            if (currentLabel && nextLabel) {
                currentLabel.innerHTML = nextLabel.innerHTML;
            } else if (!currentLabel && nextLabel) {
                currentSection.insertBefore(nextLabel.cloneNode(true), currentSection.firstChild || null);
            } else if (currentLabel && !nextLabel) {
                currentLabel.parentNode.removeChild(currentLabel);
            }

            var currentEntries = currentSection.querySelector(".brave-view__entries");
            var nextEntries = nextSection.querySelector(".brave-view__entries");
            if (currentEntries && nextEntries) {
                reconcileCombatEntryCollection(currentEntries, nextEntries);
            } else {
                currentSection.innerHTML = nextSection.innerHTML;
            }
        }
        return true;
    };

    var patchRoomViewInPlace = function (roomNode, markup) {
        var currentView = roomNode;
        var nextView = parseMarkupRoot(markup);
        if (!currentView || !nextView) {
            return false;
        }
        syncElementAttributes(currentView, nextView);
        currentView.className = nextView.className;

        var currentHero = currentView.querySelector(".brave-view__hero");
        var nextHero = nextView.querySelector(".brave-view__hero");
        if (currentHero && nextHero) {
            currentHero.innerHTML = nextHero.innerHTML;
        } else if (currentHero && !nextHero) {
            currentHero.parentNode.removeChild(currentHero);
        } else if (!currentHero && nextHero) {
            currentView.insertBefore(nextHero.cloneNode(true), currentView.firstChild || null);
        }

        var currentSectionsWrap = currentView.querySelector(".brave-view__sections");
        var nextSectionsWrap = nextView.querySelector(".brave-view__sections");
        if (currentSectionsWrap && nextSectionsWrap) {
            currentSectionsWrap.innerHTML = nextSectionsWrap.innerHTML;
            syncElementAttributes(currentSectionsWrap, nextSectionsWrap);
            currentSectionsWrap.className = nextSectionsWrap.className;
        } else if (currentSectionsWrap || nextSectionsWrap) {
            currentView.innerHTML = nextView.innerHTML;
        }

        return true;
    };

    var spawnCombatFloater = function (node, text, tone, element) {
        if (!node || !text) {
            return;
        }
        var floater = document.createElement("span");
        floater.className = "brave-combat-floater brave-combat-floater--" + (tone || "neutral");
        var driftX = ((Math.random() * 18) - 9).toFixed(2) + "px";
        var driftY = (18 + (Math.random() * 12)).toFixed(2) + "px";
        var popScale = (1.06 + (Math.random() * 0.16)).toFixed(2);
        floater.style.setProperty("--brave-floater-drift-x", driftX);
        floater.style.setProperty("--brave-floater-rise-y", driftY);
        floater.style.setProperty("--brave-floater-pop-scale", popScale);
        if (element) {
            floater.classList.add("brave-combat-floater--element-" + element);
        }
        floater.textContent = text;
        node.appendChild(floater);
        window.setTimeout(function () {
            if (floater && floater.parentNode) {
                floater.parentNode.removeChild(floater);
            }
        }, 1300);
    };

    var animateCombatImpact = function (node, tone, element) {
        if (!node) {
            return;
        }
        var impactTone = tone || "damage";
        node.classList.remove("brave-view__entry--impact-damage", "brave-view__entry--impact-heal", "brave-view__entry--impact-guard", "brave-view__entry--impact-break", "brave-view__entry--impact-miss");
        Array.prototype.slice.call(node.classList).forEach(function (className) {
            if (className.indexOf("brave-view__entry--impact-element-") === 0) {
                node.classList.remove(className);
            }
        });
        void node.offsetWidth;
        node.classList.add("brave-view__entry--impact-" + impactTone);
        if (element) {
            node.classList.add("brave-view__entry--impact-element-" + element);
        }
        window.setTimeout(function () {
            node.classList.remove("brave-view__entry--impact-" + impactTone);
            if (element) {
                node.classList.remove("brave-view__entry--impact-element-" + element);
            }
        }, 360);
    };

    var animateCombatLunge = function (attackerNode, targetNode) {
        if (!attackerNode || !targetNode) {
            return;
        }
        var attackerRect = attackerNode.getBoundingClientRect();
        var targetRect = targetNode.getBoundingClientRect();
        var dx = (targetRect.left + (targetRect.width / 2)) - (attackerRect.left + (attackerRect.width / 2));
        var dy = (targetRect.top + (targetRect.height / 2)) - (attackerRect.top + (attackerRect.height / 2));
        var magnitude = Math.sqrt((dx * dx) + (dy * dy));
        if (!magnitude) {
            return;
        }

        var lungeDistance = Math.min(18, Math.max(8, magnitude * 0.08));
        var unitX = dx / magnitude;
        var unitY = dy / magnitude;

        attackerNode.style.setProperty("--brave-combat-lunge-x", (unitX * lungeDistance).toFixed(2) + "px");
        attackerNode.style.setProperty("--brave-combat-lunge-y", (unitY * lungeDistance).toFixed(2) + "px");
        attackerNode.classList.remove("brave-view__entry--lunge");
        void attackerNode.offsetWidth;
        attackerNode.classList.add("brave-view__entry--lunge");
        window.setTimeout(function () {
            attackerNode.classList.remove("brave-view__entry--lunge");
            attackerNode.style.removeProperty("--brave-combat-lunge-x");
            attackerNode.style.removeProperty("--brave-combat-lunge-y");
        }, 320);
    };

    var animateCombatDefeat = function (nodeOrSnapshot) {
        if (!nodeOrSnapshot) {
            return;
        }
        if (nodeOrSnapshot.nodeType) {
            if (nodeOrSnapshot.classList.contains("brave-view__entry--defeating")) {
                return;
            }
            nodeOrSnapshot.classList.add("brave-view__entry--defeating");
            var liveRef = getCombatEntryRef(nodeOrSnapshot);
            window.setTimeout(function () {
                if (liveRef) {
                    suppressCombatEntryRef(liveRef);
                }
            }, 900);
            return;
        }
        var snapshot = nodeOrSnapshot.nodeType ? captureCombatEntrySnapshot(nodeOrSnapshot) : nodeOrSnapshot;
        if (!snapshot || !snapshot.rect) {
            return;
        }
        var rect = snapshot.rect;
        if (!rect.width || !rect.height) {
            return;
        }
        var ghost = document.createElement("div");
        ghost.className = "brave-combat-ghost brave-combat-ghost--defeat";
        ghost.innerHTML = snapshot.html;
        ghost = ghost.firstElementChild || ghost;
        ghost.classList.add("brave-combat-ghost", "brave-combat-ghost--defeat");
        ghost.style.position = "fixed";
        ghost.style.left = rect.left + "px";
        ghost.style.top = rect.top + "px";
        ghost.style.width = rect.width + "px";
        ghost.style.height = rect.height + "px";
        ghost.style.margin = "0";
        ghost.style.pointerEvents = "none";
        ghost.style.zIndex = "999";
        document.body.appendChild(ghost);
        if (snapshot.ref) {
            suppressCombatEntryRef(snapshot.ref);
        }
        window.setTimeout(function () {
            if (ghost && ghost.parentNode) {
                ghost.parentNode.removeChild(ghost);
            }
        }, 900);
    };

    var parseCombatFloaters = function (text) {
        var clean = String(text || "").replace(/\s+/g, " ").trim();
        var results = [];
        var match = clean.match(/^(.+?) hits (.+?) for (\d+) damage/i);
        if (match) {
            results.push({ source: match[1], target: match[2], text: match[3], tone: "damage", impact: "damage", lunge: true });
        }
        match = clean.match(/^(.+?) restores (\d+) HP to (.+?)\./i);
        if (match) {
            results.push({ target: match[3], text: match[2], tone: "heal", impact: "heal" });
        }
        match = clean.match(/^(.+?)'s (.+?) breaks (.+?)'s (.+?)\./i);
        if (match) {
            results.push({ target: match[3], text: "BREAK", tone: "break", impact: "break" });
        }
        match = clean.match(/^(.+?) cuts in front of (.+?)'s (.+?), pulling it off (.+?)\./i);
        if (match) {
            results.push({ target: match[1], text: "COVER", tone: "guard", impact: "guard" });
        }
        match = clean.match(/^(.+?)'s (.+?) takes the edge off (.+?)'s (.+?)\./i);
        if (match) {
            results.push({ target: match[1], text: "GUARD", tone: "guard", impact: "guard" });
        }
        match = clean.match(/^(.+?)'s (.+?) lands clean\./i);
        if (match) {
            results.push({ target: match[1], text: "HIT", tone: "damage", impact: "damage" });
        }
        match = clean.match(/^(.+?) falls\./i);
        if (match) {
            results.push({ target: match[1], text: "DOWN", tone: "break", impact: "break" });
        }
        return results;
    };

    var normalizeCombatEvent = function (event) {
        var mapped = {};
        Object.keys(event || {}).forEach(function (key) {
            mapped[key] = event[key];
        });
        if (mapped.amount && !mapped.text) {
            mapped.text = mapped.amount;
        }
        mapped.tone = mapped.tone || (mapped.kind === "heal" ? "heal" : "damage");
        mapped.impact = mapped.impact || (mapped.kind === "heal" ? "heal" : "damage");
        mapped.lunge = mapped.lunge === "1" || mapped.lunge === "true" || mapped.lunge === true;
        return mapped;
    };

    var applyCombatEventToTarget = function (event, targetNode, targetSnapshot) {
        if (!event || !targetNode || event._appliedTarget) {
            return;
        }
        if (targetSnapshot) {
            spawnCombatFloaterFromSnapshot(targetSnapshot, event.text, event.tone, event.element);
        } else {
            spawnCombatFloater(targetNode, event.text, event.tone, event.element);
        }
        if (event.impact) {
            animateCombatImpact(targetNode, event.impact, event.element);
        }
        if (event.defeat) {
            animateCombatDefeat(targetSnapshot || targetNode);
        }
        event._appliedTarget = true;
    };

    var applyCombatFloatersFromNode = function (node) {
        if (!node) {
            return;
        }
        var text = node.textContent || "";
        var events = [];
        if (node.dataset && node.dataset.braveFx) {
            try {
                events = JSON.parse(node.dataset.braveFx);
            } catch (_error) {
                events = [];
            }
        }
        if (!events.length) {
            events = parseCombatFloaters(text);
        } else {
            events = events.map(normalizeCombatEvent);
        }
        queueCombatFxEvents(events.filter(function (event) {
            return event && event.kind !== "action";
        }));
    };

    var combatFxEventDelay = function (event) {
        if (!event) {
            return 140;
        }
        if (event.defeat) {
            return 900;
        }
        if (event.lunge) {
            return 360;
        }
        if (event.impact) {
            return 220;
        }
        return 140;
    };

    var requeueUnresolvedCombatFxEvent = function (event) {
        if (!event) {
            return false;
        }
        event._attempts = (event._attempts || 0) + 1;
        if (event._attempts <= 8) {
            pendingCombatFxEvents.push(event);
            scheduleCombatFxFlush(90);
            return true;
        }
        return false;
    };

    var finishCombatFxEvent = function (delayMs) {
        combatFxProcessing = true;
        window.setTimeout(function () {
            combatFxProcessing = false;
            flushDeferredCombatViewRender(false);
            flushQueuedCombatResultView();
            scheduleCombatFxFlush(0);
        }, Math.max(0, delayMs || 0));
    };

    var flushPendingCombatFxEvents = function () {
        if (combatFxProcessing || !pendingCombatFxEvents.length || !isCombatUiActive() || combatViewTransitionActive) {
            return;
        }
        var event = pendingCombatFxEvents.shift();
        var targetNode = findCombatEntryForEvent(event, "target");
        var attackerNode = event.source || event.source_ref ? findCombatEntryForEvent(event, "source") : null;
        var targetSnapshot = targetNode ? captureCombatEntrySnapshot(targetNode) : null;
        var attackerSnapshot = attackerNode ? captureCombatEntrySnapshot(attackerNode) : null;
        if (!targetNode) {
            if (!requeueUnresolvedCombatFxEvent(event)) {
                flushQueuedCombatResultView();
                scheduleCombatFxFlush(0);
            }
            return;
        }
        if (event.lunge && attackerNode) {
            animateCombatLunge(attackerNode, targetNode);
            window.setTimeout(function () {
                applyCombatEventToTarget(event, targetNode, targetSnapshot);
            }, 120);
        } else {
            applyCombatEventToTarget(event, targetNode, targetSnapshot);
        }
        finishCombatFxEvent(combatFxEventDelay(event));
    };

    var handleCombatFxEvent = function (payload) {
        if (!payload || typeof payload !== "object") {
            return;
        }
        var event = normalizeCombatEvent(payload);
        if (event && event.defeat && isCombatUiActive()) {
            var targetNode = findCombatEntryForEvent(event, "target");
            var targetSnapshot = targetNode ? captureCombatEntrySnapshot(targetNode) : null;
            if (targetNode) {
                applyCombatEventToTarget(event, targetNode, targetSnapshot);
                finishCombatFxEvent(combatFxEventDelay(event));
                return;
            }
        }
        queueCombatFxEvents([event]);
    };

    var syncAnimatedAtbMeters = function () {
        if (currentAtbAnimationFrame && window.cancelAnimationFrame) {
            window.cancelAnimationFrame(currentAtbAnimationFrame);
            currentAtbAnimationFrame = null;
        }
        if (!currentViewData || currentViewData.variant !== "combat") {
            return;
        }
        var meters = Array.prototype.slice.call(document.querySelectorAll(".brave-view--combat .brave-view__meter[data-meter-kind='atb']"));
        meters.forEach(function (meter) {
            var fill = meter.querySelector(".brave-view__meter-fill");
            if (!fill) {
                return;
            }
            var phase = meter.getAttribute("data-atb-phase") || "charging";
            fill.style.transitionDuration = "0ms";
            if (phase !== "charging") {
                if (phase === "ready" || phase === "resolving" || phase === "winding") {
                    fill.style.width = "100%";
                } else if (phase === "recovering" || phase === "cooldown") {
                    fill.style.width = "0%";
                }
                return;
            }
            var gauge = parseFloat(meter.getAttribute("data-atb-gauge") || "0");
            var ready = Math.max(1, parseFloat(meter.getAttribute("data-atb-ready") || "400"));
            var remainingMs = Math.max(0, parseFloat(meter.getAttribute("data-atb-phase-remaining") || "0"));
            var currentPercent = Math.max(0, Math.min(100, (gauge / ready) * 100));
            var continuityPercent = parseFloat(meter.getAttribute("data-atb-visual-start") || "");
            if (!isNaN(continuityPercent)) {
                currentPercent = Math.max(currentPercent, Math.max(0, Math.min(100, continuityPercent)));
                meter.removeAttribute("data-atb-visual-start");
            }
            fill.style.width = currentPercent.toFixed(2) + "%";
            if (!(remainingMs > 0) || currentPercent >= 100) {
                return;
            }
            window.requestAnimationFrame(function () {
                fill.style.transitionDuration = remainingMs + "ms";
                fill.style.width = "100%";
            });
        });
    };

    var restoreCombatAtbContinuity = function (previousSnapshots) {
        if (!Array.isArray(previousSnapshots) || !previousSnapshots.length) {
            return;
        }
        previousSnapshots.forEach(function (snapshot) {
            if (!snapshot || !snapshot.ref) {
                return;
            }
            var node = document.querySelector(".brave-view--combat [data-entry-ref='" + snapshot.ref + "']");
            var meter = getCombatAtbMeter(node);
            var fill = meter ? meter.querySelector(".brave-view__meter-fill") : null;
            if (!fill || snapshot.atbPercent == null) {
                return;
            }
            var phase = meter.getAttribute("data-atb-phase") || "charging";
            if (phase !== "charging") {
                return;
            }
            if (snapshot.atbPhase !== "charging") {
                return;
            }
            var currentPhaseStartedAt = meter.getAttribute("data-atb-phase-started-at") || "";
            if (!snapshot.atbPhaseStartedAt || snapshot.atbPhaseStartedAt !== currentPhaseStartedAt) {
                return;
            }
            var meterGauge = parseFloat(meter.getAttribute("data-atb-gauge") || "0");
            var meterReady = Math.max(1, parseFloat(meter.getAttribute("data-atb-ready") || "400"));
            var serverPercent = Math.max(0, Math.min(100, (meterGauge / meterReady) * 100));
            var restoredPercent = Math.max(serverPercent, Math.max(0, Math.min(100, snapshot.atbPercent)));
            meter.setAttribute("data-atb-visual-start", restoredPercent.toFixed(2));
            fill.style.transitionDuration = "0ms";
            fill.style.width = restoredPercent.toFixed(2) + "%";
        });
    };

    var ensureCombatLogObserver = function () {
        var mwin = document.getElementById("messagewindow");
        if (!window.MutationObserver || !mwin) {
            return;
        }
        if (combatLogObserver) {
            combatLogObserver.disconnect();
        }
        combatLogObserver = new MutationObserver(function () {
            if (!currentViewData || currentViewData.variant !== "combat") {
                return;
            }
            claimCombatLogEntries();
        });
        combatLogObserver.observe(mwin, {
            childList: true,
            subtree: false,
        });
    };

    var finishGameIntroVeil = function () {
        var veil = document.getElementById("brave-intro-veil");
        if (veil) {
            veil.classList.remove("brave-intro-veil--active");
        }
    };

    var startGameIntroVeil = function () {
        var veil = document.getElementById("brave-intro-veil");
        if (veil) {
            veil.classList.add("brave-intro-veil--active");
            braveGameLoaded = false;
        }
    };

    var renderConnectionView = function () {
        renderMainView(buildConnectionViewData());
        pruneLegacyConnectionBoilerplate();
        window.setTimeout(finishGameIntroVeil, 100);
    };

    var resetToConnectionView = function (screen) {
        clearTextOutput();
        clearSceneRail();
        clearReactiveState();
        braveGameLoaded = false;
        currentConnectionScreen = screen || "menu";
        renderConnectionView();
    };

    var openConnectionScreen = function (screen) {
        currentConnectionScreen = screen || "menu";
        renderConnectionView();
    };

    var renderInlineActions = function (actions) {
        if (!Array.isArray(actions) || !actions.length) {
            return "";
        }
        return (
            "<div class='brave-view__inline-actions'>"
            + actions.map(function (entry) {
                var toneClass = entry && entry.tone ? " brave-view__mini-action--" + escapeHtml(entry.tone) : "";
                var iconOnlyClass = entry && entry.icon_only ? " brave-view__mini-action--icon-only" : "";
                var aria = entry && (entry.aria_label || entry.label)
                    ? " aria-label='" + escapeHtml(entry.aria_label || entry.label) + "'"
                    : "";
                return (
                    "<button type='button' class='brave-view__mini-action brave-click" + toneClass + iconOnlyClass + "'"
                    + commandAttrs(entry, false)
                    + aria
                    + ">"
                    + (entry && entry.icon ? icon(entry.icon, "brave-view__mini-action-icon") : "")
                    + (entry && entry.icon_only ? "" : "<span>" + escapeHtml(entry && entry.label ? entry.label : "") + "</span>")
                    + "</button>"
                );
            }).join("")
            + "</div>"
        );
    };

    var chip = function (label, iconName, modifierClass) {
        var classes = "scene-card__chip";
        if (modifierClass) {
            classes += " " + modifierClass;
        }
        return (
            "<span class='" + classes + "'>"
            + icon(iconName, "scene-card__chip-icon")
            + "<span>" + escapeHtml(label) + "</span>"
            + "</span>"
        );
    };

    var setMainViewMode = function (active) {
        document.body.classList.toggle("brave-mainview-active", !!active);
    };

    var setStickyViewMode = function (active) {
        document.body.classList.toggle("brave-sticky-view-active", !!active);
    };

    var focusWithoutScroll = function (node) {
        if (!node || typeof node.focus !== "function") {
            return;
        }
        try {
            node.focus({ preventScroll: true });
        } catch (err) {
            node.focus();
        }
    };

    var suppressMobileNonInputFocus = function (durationMs) {
        if (!isMobileViewport()) {
            return;
        }
        suppressMobileNonInputFocusUntil = Math.max(
            suppressMobileNonInputFocusUntil || 0,
            Date.now() + Math.max(0, durationMs || 0)
        );
    };

    var shouldSuppressMobileNonInputFocus = function (target) {
        if (!isMobileViewport() || Date.now() >= (suppressMobileNonInputFocusUntil || 0)) {
            return false;
        }
        return !isTextEntryElement(target);
    };

    var isRoomNavigationCommand = function (command) {
        var normalized = String(command || "").trim().toLowerCase();
        return normalized === "n"
            || normalized === "north"
            || normalized === "s"
            || normalized === "south"
            || normalized === "e"
            || normalized === "east"
            || normalized === "w"
            || normalized === "west"
            || normalized === "u"
            || normalized === "up"
            || normalized === "d"
            || normalized === "down";
    };

    var suppressMobileRoomNavScroll = function (durationMs) {
        if (!isMobileViewport()) {
            return;
        }
        suppressMobileRoomNavScrollUntil = Math.max(
            suppressMobileRoomNavScrollUntil || 0,
            Date.now() + Math.max(0, durationMs || 0)
        );
    };

    var shouldSuppressMobileRoomNavScroll = function (target) {
        return !!(
            isMobileViewport()
            && Date.now() < (suppressMobileRoomNavScrollUntil || 0)
            && target
            && target.id === "messagewindow"
            && currentViewData
            && isRoomLikeView(currentViewData)
        );
    };

    var pulseBodyClass = function (className, duration) {
        var body = document.body;
        if (!body) {
            return;
        }
        if (reactiveTimers[className]) {
            window.clearTimeout(reactiveTimers[className]);
        }
        body.classList.remove(className);
        void body.offsetWidth;
        body.classList.add(className);
        reactiveTimers[className] = window.setTimeout(function () {
            body.classList.remove(className);
            reactiveTimers[className] = null;
        }, duration || 220);
    };

    var clearCombatTransitionOverlay = function () {
        var overlay = document.getElementById("brave-combat-transition");
        if (overlay && overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    };

    var getRoomSceneMeta = function (viewData) {
        if (!isRoomLikeView(viewData)) {
            return null;
        }
        var explicitRegion = String(viewData && viewData.region_name ? viewData.region_name : "").trim();
        var regionLabel = String(viewData && viewData.eyebrow ? viewData.eyebrow : "").trim();
        var roomTitle = String(viewData && viewData.title ? viewData.title : "").trim();
        return {
            roomId: String(viewData && viewData.room_id ? viewData.room_id : getReactiveSourceId(viewData) || "").trim(),
            regionLabel: regionLabel,
            regionName: explicitRegion || regionLabel,
            regionKey: (explicitRegion || regionLabel).toLowerCase(),
            roomTitle: roomTitle,
        };
    };

    var getRenderedRoomSceneMeta = function () {
        var card = document.querySelector("#messagewindow > .brave-sticky-view > .brave-view--room .brave-view__room-scene-card")
            || document.querySelector("#messagewindow > .brave-view--room .brave-view__room-scene-card");
        if (!card) {
            return getRoomSceneMeta(getCurrentRoomView());
        }
        var roomId = String(card.getAttribute("data-brave-room-id") || "").trim();
        var regionName = String(card.getAttribute("data-brave-region") || "").trim();
        var titleNode = card.querySelector(".brave-view__title span");
        return {
            roomId: roomId,
            regionLabel: regionName,
            regionName: regionName,
            regionKey: regionName.toLowerCase(),
            roomTitle: titleNode ? String(titleNode.textContent || "").trim() : "",
        };
    };

    var rememberRenderedRoomSceneMeta = function (meta) {
        if (!meta || !meta.roomId) {
            return;
        }
        lastRenderedRoomSceneMeta = {
            roomId: String(meta.roomId || "").trim(),
            regionLabel: String(meta.regionLabel || "").trim(),
            regionName: String(meta.regionName || "").trim(),
            regionKey: String(meta.regionKey || "").trim(),
            roomTitle: String(meta.roomTitle || "").trim(),
        };
    };

    var clearRegionTransitionOverlay = function () {
        var overlay = document.getElementById("brave-region-transition");
        if (overlay && overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    };

    var clearRegionTransitionState = function () {
        if (pendingRegionTransitionTimeout) {
            window.clearTimeout(pendingRegionTransitionTimeout);
            pendingRegionTransitionTimeout = null;
        }
        if (pendingRegionTransitionCleanupTimeout) {
            window.clearTimeout(pendingRegionTransitionCleanupTimeout);
            pendingRegionTransitionCleanupTimeout = null;
        }
        pendingRegionTransitionViewData = null;
        pendingRegionTransitionMeta = null;
        if (document.body) {
            document.body.classList.remove("brave-region-transition-active");
        }
        clearRegionTransitionOverlay();
    };

    var showRegionTransitionOverlay = function (viewData, metaOverride) {
        clearRegionTransitionOverlay();
        var meta = metaOverride || getRoomSceneMeta(viewData) || {};
        var overlay = document.createElement("div");
        overlay.id = "brave-region-transition";
        overlay.className = "brave-region-transition";
        overlay.innerHTML =
            "<div class='brave-region-transition__veil'></div>"
            + "<div class='brave-region-transition__titlecard'>"
                + "<div class='brave-region-transition__eyebrow'>Region</div>"
                + "<div class='brave-region-transition__title'>"
                + escapeHtml(meta.regionName || meta.regionLabel || meta.roomTitle || "Unknown Region")
                + "</div>"
            + "</div>";
        document.body.appendChild(overlay);
    };

    var shouldStartRegionTransition = function (viewData) {
        if (prefersReducedMotion() || !isRoomLikeView(viewData)) {
            return false;
        }
        var nextMeta = getRoomSceneMeta(viewData);
        if (!nextMeta || !nextMeta.regionKey) {
            return false;
        }
        var candidates = [
            getRenderedRoomSceneMeta(),
            getRoomSceneMeta(currentViewData),
            getRoomSceneMeta(currentRoomViewData),
            getRoomSceneMeta(getCurrentRoomView()),
        ].filter(function (meta) {
            return !!(meta && meta.regionKey && meta.roomId);
        });
        for (var i = 0; i < candidates.length; i += 1) {
            var previousMeta = candidates[i];
            if (!previousMeta) {
                continue;
            }
            if (previousMeta.roomId === nextMeta.roomId) {
                continue;
            }
            if (previousMeta.regionKey !== nextMeta.regionKey) {
                return true;
            }
        }
        return false;
    };

    var startRegionTransition = function (viewData, options) {
        if (!viewData || !shouldStartRegionTransition(viewData)) {
            return false;
        }
        clearRegionTransitionState();
        pendingRegionTransitionViewData = viewData;
        pendingRegionTransitionMeta = getRoomSceneMeta(viewData);
        if (document.body) {
            document.body.classList.add("brave-region-transition-active");
        }
        showRegionTransitionOverlay(viewData, pendingRegionTransitionMeta);
        pendingRegionTransitionTimeout = window.setTimeout(function () {
            var queuedViewData = pendingRegionTransitionViewData;
            var nextOptions = {};
            Object.keys(options || {}).forEach(function (key) {
                nextOptions[key] = options[key];
            });
            pendingRegionTransitionTimeout = null;
            pendingRegionTransitionViewData = null;
            nextOptions.skipRegionTransition = true;
            nextOptions.skipRoomCardTransition = true;
            if (!queuedViewData) {
                clearRegionTransitionState();
                return;
            }
            renderMainView(queuedViewData, nextOptions);
        }, 360);
        pendingRegionTransitionCleanupTimeout = window.setTimeout(function () {
            clearRegionTransitionState();
        }, 1320);
        return true;
    };

    var triggerRoomSceneCardTransition = function () {
        if (prefersReducedMotion()) {
            return;
        }
        var roomView = document.querySelector("#messagewindow > .brave-sticky-view > .brave-view--room")
            || document.querySelector("#messagewindow > .brave-view--room");
        if (!roomView) {
            return;
        }
        var card = roomView.querySelector(".brave-view__room-scene-card");
        if (!card) {
            return;
        }
        if (roomSceneCardTransitionTimeout) {
            window.clearTimeout(roomSceneCardTransitionTimeout);
            roomSceneCardTransitionTimeout = null;
        }
        card.classList.remove("brave-view__room-scene-card--transition");
        void card.offsetWidth;
        card.classList.add("brave-view__room-scene-card--transition");
        roomSceneCardTransitionTimeout = window.setTimeout(function () {
            card.classList.remove("brave-view__room-scene-card--transition");
            roomSceneCardTransitionTimeout = null;
        }, 280);
    };

    var showCombatTransitionOverlay = function (viewData, mode) {
        if (!document.body) {
            return;
        }
        clearCombatTransitionOverlay();
        var overlay = document.createElement("div");
        overlay.id = "brave-combat-transition";
        overlay.className = "brave-combat-transition brave-combat-transition--" + escapeHtml(mode || "enter");
        var title = viewData && viewData.title ? String(viewData.title) : "Combat";
        var subtitle = viewData && viewData.subtitle ? String(viewData.subtitle) : "";
        overlay.innerHTML =
            "<div class='brave-combat-transition__wash'></div>"
            + "<div class='brave-combat-transition__flash'></div>"
            + "<div class='brave-combat-transition__shutters'>"
            + "<span class='brave-combat-transition__shutter brave-combat-transition__shutter--1'></span>"
            + "<span class='brave-combat-transition__shutter brave-combat-transition__shutter--2'></span>"
            + "<span class='brave-combat-transition__shutter brave-combat-transition__shutter--3'></span>"
            + "</div>"
            + "<div class='brave-combat-transition__ring'></div>"
            + (
                mode === "return"
                    ? ""
                    : "<div class='brave-combat-transition__card'>"
                        + "<div class='brave-combat-transition__eyebrow'>"
                        + icon("swords", "brave-combat-transition__eyebrow-icon")
                        + "<span>Encounter</span>"
                        + "</div>"
                        + "<div class='brave-combat-transition__title'>" + escapeHtml(title) + "</div>"
                        + (subtitle ? "<div class='brave-combat-transition__subtitle'>" + escapeHtml(subtitle) + "</div>" : "")
                        + "</div>"
            );
        document.body.appendChild(overlay);
    };

    var clearCombatTransitionState = function () {
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
            pendingCombatTransitionTimeout = null;
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        pendingCombatTransitionViewData = null;
        pendingCombatTransitionMode = "";
        combatViewTransitionActive = false;
        if (document.body) {
            document.body.classList.remove("brave-combat-transition-active");
            document.body.classList.remove("brave-combat-return-active");
        }
        clearCombatTransitionOverlay();
    };

    var finishCombatTransitionOverlay = function () {
        var overlay = document.getElementById("brave-combat-transition");
        var cleanupDelay = getCombatTransitionCleanupDelay(pendingCombatTransitionMode || (overlay && overlay.classList.contains("brave-combat-transition--return") ? "return" : "enter"));
        if (overlay) {
            overlay.classList.add("brave-combat-transition--out");
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
        }
        pendingCombatTransitionCleanupTimeout = window.setTimeout(function () {
            pendingCombatTransitionCleanupTimeout = null;
            if (document.body) {
                document.body.classList.remove("brave-combat-transition-active");
                document.body.classList.remove("brave-combat-return-active");
            }
            clearCombatTransitionOverlay();
        }, cleanupDelay);
    };

    var startCombatReturnOverlay = function (viewData) {
        if (!viewData || !isRoomLikeView(viewData) || prefersReducedMotion()) {
            return false;
        }
        pendingCombatResultReturnTransition = false;
        pendingCombatTransitionMode = "return";
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        if (document.body) {
            document.body.classList.remove("brave-combat-transition-active");
            document.body.classList.add("brave-combat-return-active");
        }
        showCombatTransitionOverlay(viewData, "return");
        pendingCombatTransitionTimeout = window.setTimeout(function () {
            pendingCombatTransitionTimeout = null;
            finishCombatTransitionOverlay();
        }, getCombatTransitionRevealDelay("return"));
        return true;
    };

    var startCombatTransition = function (viewData, mode) {
        mode = mode || "enter";
        if (!viewData || prefersReducedMotion()) {
            return false;
        }
        if (mode === "enter" && viewData.variant !== "combat") {
            return false;
        }
        pendingCombatTransitionViewData = viewData;
        pendingCombatTransitionMode = mode;
        combatViewTransitionActive = true;
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        if (document.body) {
            document.body.classList.toggle("brave-combat-transition-active", mode === "enter");
            document.body.classList.toggle("brave-combat-return-active", mode === "return");
        }
        showCombatTransitionOverlay(viewData, mode);
        var revealDelay = getCombatTransitionRevealDelay(mode);
        pendingCombatTransitionTimeout = window.setTimeout(function () {
            var queuedViewData = pendingCombatTransitionViewData;
            pendingCombatTransitionTimeout = null;
            pendingCombatTransitionViewData = null;
            var resolvedMode = pendingCombatTransitionMode || mode;
            pendingCombatTransitionMode = resolvedMode;
            if (!queuedViewData) {
                clearCombatTransitionState();
                return;
            }
            if (resolvedMode === "return") {
                combatViewTransitionActive = false;
            }
            renderMainView(queuedViewData, { skipCombatTransition: true });
            finishCombatTransitionOverlay();
        }, revealDelay);
        return true;
    };

    var setBodyState = function (name, value) {
        var body = document.body;
        if (!body) {
            return;
        }
        var attr = "data-brave-" + name;
        if (value === undefined || value === null || value === "" || value === false) {
            body.removeAttribute(attr);
            return;
        }
        body.setAttribute(attr, String(value));
    };

    var applyReactiveState = function (state) {
        var body = document.body;
        if (!body) {
            return;
        }

        var nextScene = state && state.scene ? state.scene : "system";
        var nextTone = state && state.world_tone ? state.world_tone : "neutral";
        var nextDanger = state && state.danger ? state.danger : "";
        var nextBoss = !!(state && state.boss);

        var previousScene = body.getAttribute("data-brave-scene") || "";
        var previousTone = body.getAttribute("data-brave-world-tone") || "";

        setBodyState("scene", nextScene);
        setBodyState("world-tone", nextTone);
        setBodyState("danger", nextDanger);
        setBodyState("boss", nextBoss ? "true" : "");

        if (previousTone && previousTone !== nextTone) {
            pulseBodyClass("brave-tone-shift", 260);
        }
        if (previousScene && previousScene !== nextScene) {
            pulseBodyClass(nextScene === "combat" ? "brave-scene-combat-enter" : "brave-scene-shift", 220);
        }
        var braveAudio = getBraveAudio();
        if (braveAudio && typeof braveAudio.setReactiveState === "function") {
            braveAudio.setReactiveState(state || {});
        }
    };

    var clearReactiveState = function () {
        var braveAudio = getBraveAudio();
        setBodyState("scene", "system");
        setBodyState("world-tone", "neutral");
        setBodyState("danger", "");
        setBodyState("boss", "");
        setBodyState("view", "");
        document.body.classList.remove("brave-tone-shift", "brave-scene-shift", "brave-scene-combat-enter", "brave-combat-transition-active");
        document.body.classList.remove("brave-combat-return-active");
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
            pendingCombatTransitionTimeout = null;
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        pendingCombatTransitionViewData = null;
        pendingCombatTransitionMode = "";
        combatViewTransitionActive = false;
        clearRegionTransitionState();
        clearCombatTransitionOverlay();
        clearCombatFxOverlay();
        clearRoomVoiceBubbles();
        if (braveAudio && typeof braveAudio.clearReactiveState === "function") {
            braveAudio.clearReactiveState();
        }
    };

    var clearStickyView = function () {
        var mwin = $("#messagewindow");
        if (!mwin.length) {
            clearCombatFxOverlay();
            setStickyViewMode(false);
            return;
        }
        mwin.children(".brave-sticky-view").remove();
        mwin.children(".brave-combat-log").remove();
        clearCombatFxOverlay();
        setStickyViewMode(false);
    };

    var teardownCombatUiState = function () {
        clearDeferredCombatViewRender();
        pendingCombatPanelData = null;
        combatViewTransitionActive = false;
        clearStickyView();
        clearReactiveState();
        currentViewData = null;
    };

    var classifyRoomActivity = function (text, cls, meta) {
        var explicit = meta && typeof meta.category === "string" ? meta.category.trim().toLowerCase() : "";
        if (explicit) {
            return explicit.replace(/[^a-z0-9_-]+/g, "-");
        }
        var raw = String(text || "").trim();
        var lowered = raw.toLowerCase();
        if (!raw) {
            return "ambient";
        }
        if (/\b(says?|asks?|exclaims?|whispers?|shouts?|yells?)\b/.test(lowered) || /".+"/.test(raw)) {
            return "speech";
        }
        if (/\b(arrives?|enters?|moves into|comes into|steps into|appears|joins)\b/.test(lowered)) {
            if (/\b(hostile|enemy|enemies|goblin|bandit|wolf|rat|warren|blackreed|miretooth|greymaw|weir|undead)\b/.test(lowered)) {
                return "threat";
            }
            return "arrival";
        }
        if (/\b(leaves?|departs?|heads|moves on|moves away|slips away|walks away)\b/.test(lowered)) {
            return "departure";
        }
        if (/\b(emotes?|smiles?|nods?|waves?|shrugs?|laughs?|frowns?|bows?)\b/.test(lowered)) {
            return "emote";
        }
        if (/\b(picks up|drops|takes|receives|gains|loses)\b/.test(lowered)) {
            return "loot";
        }
        return "ambient";
    };

    var getRoomActivityIcon = function (category) {
        return {
            speech: "forum",
            emote: "waving_hand",
            arrival: "login",
            departure: "logout",
            threat: "warning",
            loot: "inventory_2",
            quest: "menu_book",
            system: "info",
            crafting: "construction",
            combat: "swords",
            ambient: "timeline"
        }[category || "ambient"] || "timeline";
    };

    var shouldToastActivity = function (entry) {
        if (!entry) {
            return false;
        }
        if (
            currentPickerData
            || isCombatUiActive()
            || currentMobileUtilityTab
            || (document.body && document.body.classList.contains("brave-notice-active"))
            || document.getElementById("brave-activity-overlay")
            || document.getElementById("brave-fishing-minigame")
            || document.getElementById("brave-arcade-overlay")
        ) {
            return false;
        }
        if (entry.category === "threat") {
            return false;
        }
        if (!isMobileViewport() || currentMobileUtilityTab === "activity") {
            return false;
        }
        return entry.category === "speech" || entry.category === "arrival";
    };

    var getActivityToastTitle = function (entry) {
        if (!entry) {
            return "Activity";
        }
        if (entry.category === "speech") {
            return "Voices";
        }
        if (entry.category === "threat") {
            return "Danger";
        }
        if (entry.category === "arrival") {
            return "Arrival";
        }
        return "Activity";
    };

    var renderActivityToast = function (entry) {
        if (!shouldToastActivity(entry)) {
            return;
        }
        renderBrowserNotice({
            title: getActivityToastTitle(entry),
            lines: [entry.text],
            tone: entry.category === "threat" ? "warn" : "muted",
            icon: getRoomActivityIcon(entry.category),
            duration_ms: entry.category === "threat" ? 3600 : 2800
        });
    };

    var renderRoomFeedEntryMarkup = function (entry) {
        if (!entry || !entry.text) {
            return "";
        }
        var cls = entry.cls || "out";
        var category = entry.category || classifyRoomActivity(entry.text, cls, entry);
        return "<div class='" + cls + " brave-room-log__entry brave-room-log__entry--" + escapeHtml(category) + "' data-brave-activity-category='" + escapeHtml(category) + "'>"
            + "<span class='brave-room-log__entry-text'>" + escapeHtml(entry.text) + "</span>"
            + "</div>";
    };

    var addRoomFeedEntry = function (cls, rawContent, meta) {
        if (typeof rawContent !== "string" || !rawContent.trim()) {
            return null;
        }
        var text = rawContent.replace(/\s+/g, " ").trim();
        if (!text) {
            return null;
        }
        var normalizedCls = cls || "out";
        var category = classifyRoomActivity(text, normalizedCls, meta);
        var lastEntry = currentRoomFeedEntries.length ? currentRoomFeedEntries[currentRoomFeedEntries.length - 1] : null;
        if (lastEntry && lastEntry.cls === normalizedCls && lastEntry.text === text) {
            return null;
        }
        var entry = { cls: normalizedCls, text: text, category: category };
        currentRoomFeedEntries.push(entry);
        if (currentRoomFeedEntries.length > 24) {
            currentRoomFeedEntries = currentRoomFeedEntries.slice(currentRoomFeedEntries.length - 24);
        }
        recordRoomVoiceBubble(text, category);
        return entry;
    };

    var isRoomActivityScrolledToBottom = function (body) {
        if (!body) {
            return true;
        }
        if (body.clientHeight <= 0) {
            return roomActivityRailPinnedToBottom;
        }
        return (body.scrollHeight - body.scrollTop - body.clientHeight) <= 16;
    };

    var updateRailActivityCue = function () {
        var panel = document.getElementById("scene-vicinity-panel");
        if (!panel) {
            return;
        }
        var cue = panel.querySelector("[data-brave-activity-scroll='rail']");
        if (!cue) {
            return;
        }
        var hasMissed = roomActivityRailMissedCount > 0;
        cue.textContent = roomActivityRailMissedCount > 99 ? "99+" : String(roomActivityRailMissedCount);
        cue.setAttribute(
            "aria-label",
            hasMissed
                ? "Scroll Activity to " + roomActivityRailMissedCount + " missed line" + (roomActivityRailMissedCount === 1 ? "" : "s")
                : "Activity is at the latest line"
        );
        cue.classList.toggle("brave-room-log__jump--visible", hasMissed);
        cue.disabled = !hasMissed;
    };

    var syncRailActivityScrollState = function (body) {
        if (!body) {
            return;
        }
        if (body.clientHeight <= 0) {
            updateRailActivityCue();
            return;
        }
        roomActivityRailPinnedToBottom = isRoomActivityScrolledToBottom(body);
        roomActivityRailScrollTop = body.scrollTop;
        if (roomActivityRailPinnedToBottom && roomActivityRailMissedCount) {
            roomActivityRailMissedCount = 0;
        }
        updateRailActivityCue();
    };

    var restoreRailActivityScroll = function (body, shouldStickToBottom) {
        if (!body) {
            return;
        }
        var applyScroll = function () {
            if (shouldStickToBottom) {
                body.scrollTop = body.scrollHeight;
                roomActivityRailPinnedToBottom = true;
                roomActivityRailScrollTop = body.scrollTop;
                if (roomActivityRailMissedCount) {
                    roomActivityRailMissedCount = 0;
                }
            } else {
                body.scrollTop = Math.min(roomActivityRailScrollTop, Math.max(0, body.scrollHeight - body.clientHeight));
            }
            syncRailActivityScrollState(body);
        };
        applyScroll();
        if (typeof window.requestAnimationFrame === "function") {
            window.requestAnimationFrame(applyScroll);
        }
    };

    var bindRailActivityScrollState = function (body) {
        if (!body || body.dataset.braveActivityScrollBound === "1") {
            return;
        }
        body.dataset.braveActivityScrollBound = "1";
        body.addEventListener("scroll", function () {
            syncRailActivityScrollState(body);
        }, { passive: true });
    };

    var noteRoomActivityEntriesAdded = function (count) {
        if (!count || isMobileViewport()) {
            return;
        }
        var railBody = document.querySelector(".brave-room-log__body--rail");
        if (railBody) {
            syncRailActivityScrollState(railBody);
        }
        if (!roomActivityRailPinnedToBottom) {
            roomActivityRailMissedCount += count;
        }
        updateRailActivityCue();
    };

    var scrollRailActivityToBottom = function () {
        var body = document.querySelector(".brave-room-log__body--rail");
        if (!body) {
            return;
        }
        roomActivityRailPinnedToBottom = true;
        roomActivityRailMissedCount = 0;
        restoreRailActivityScroll(body, true);
        updateRailActivityCue();
    };

    var syncRoomActivityLog = function (body) {
        var shouldStickToBottom = true;
        if (body) {
            shouldStickToBottom = isRoomActivityScrolledToBottom(body);
            body.innerHTML = currentRoomFeedEntries.map(renderRoomFeedEntryMarkup).join("");
            if (shouldStickToBottom) {
                body.scrollTop = body.scrollHeight;
            }
        }
        syncRailActivityLog();
        syncRoomActivityCardSurface(document.getElementById("scene-vicinity-panel"), getCurrentRoomView(), { mobile: false });
        syncRoomActivityCardSurface(document.getElementById("mobile-utility-sheet"), getCurrentRoomView(), { mobile: true });
        return $(body);
    };

    var isCombatLogScrolledToBottom = function (body) {
        if (!body) {
            return true;
        }
        if (body.clientHeight <= 0) {
            return combatLogPinnedToBottom;
        }
        return (body.scrollHeight - body.scrollTop - body.clientHeight) <= 16;
    };

    var syncCombatLogScrollState = function (body) {
        if (!body) {
            return;
        }
        if (body.clientHeight <= 0) {
            return;
        }
        combatLogPinnedToBottom = isCombatLogScrolledToBottom(body);
        combatLogScrollTop = body.scrollTop;
    };

    var restoreCombatLogScroll = function (body, shouldStickToBottom) {
        if (!body) {
            return;
        }
        var applyScroll = function () {
            if (shouldStickToBottom) {
                body.scrollTop = body.scrollHeight;
                combatLogPinnedToBottom = true;
                combatLogScrollTop = body.scrollTop;
            } else {
                body.scrollTop = Math.min(combatLogScrollTop, Math.max(0, body.scrollHeight - body.clientHeight));
            }
            syncCombatLogScrollState(body);
        };
        applyScroll();
        if (typeof window.requestAnimationFrame === "function") {
            window.requestAnimationFrame(applyScroll);
        }
    };

    var updateCombatLogCue = function () {
        var cue = document.querySelector(".brave-combat-log [data-brave-combat-scroll='latest']");
        if (!cue) {
            return;
        }
        var hasMissed = !combatLogPinnedToBottom;
        cue.classList.toggle("brave-room-log__jump--visible", hasMissed);
        cue.disabled = !hasMissed;
        cue.setAttribute(
            "aria-label",
            hasMissed ? "Jump battle feed to the latest line" : "Battle feed is at the latest line"
        );
    };

    var scrollCombatLogToBottom = function () {
        var body = document.querySelector(".brave-combat-log__body");
        if (!body) {
            return;
        }
        combatLogPinnedToBottom = true;
        combatLogScrollTop = body.scrollTop;
        restoreCombatLogScroll(body, true);
        updateCombatLogCue();
    };

    var bindCombatLogScrollState = function (body) {
        if (!body || body.dataset.braveCombatScrollBound === "1") {
            return;
        }
        body.dataset.braveCombatScrollBound = "1";
        body.addEventListener("scroll", function () {
            syncCombatLogScrollState(body);
            updateCombatLogCue();
        }, { passive: true });
    };

    var syncRailActivityLog = function () {
        var panel = document.getElementById("scene-vicinity-panel");
        if (!panel) {
            return null;
        }
        var body = panel.querySelector(".brave-room-log__body--rail");
        if (!body) {
            return null;
        }
        if (body.dataset.braveActivityScrollBound === "1") {
            syncRailActivityScrollState(body);
        }
        var shouldStickToBottom = roomActivityRailPinnedToBottom;
        body.innerHTML = currentRoomFeedEntries.map(renderRoomFeedEntryMarkup).join("");
        bindRailActivityScrollState(body);
        restoreRailActivityScroll(body, shouldStickToBottom);
        syncRoomActivityCardSurface(panel, getCurrentRoomView(), { mobile: false });
        return $(body);
    };

    var claimRoomActivityEntries = function () {
        var mwin = $("#messagewindow");
        var claimedCount = 0;
        if (!mwin.length || isCombatUiActive()) {
            return claimedCount;
        }

        var strayEntries = mwin.children(".out, .msg, .err, .sys, .inp");
        if (!strayEntries.length) {
            return claimedCount;
        }

        strayEntries.each(function () {
            if (shouldLogRoomActivity(this.textContent || "", this.className || "out", null)) {
                if (addRoomFeedEntry(this.className || "out", this.textContent || "")) {
                    claimedCount += 1;
                }
            }
        });
        strayEntries.remove();
        return claimedCount;
    };

    var syncMobileRoomActivityLog = function () {
        var host = document.getElementById("mobile-utility-sheet");
        if (!host) {
            return null;
        }
        var body = host.querySelector(".brave-room-log__body--mobile");
        if (!body) {
            return null;
        }
        syncRoomActivityCardSurface(host, getCurrentRoomView(), { mobile: true });
        return syncRoomActivityLog(body);
    };

    var ensureRoomActivityLog = function () {
        var mwin = $("#messagewindow");
        if (!mwin.length || isCombatUiActive()) {
            return null;
        }

        var claimedCount = claimRoomActivityEntries();
        if (claimedCount && isMobileViewport()) {
            if (currentMobileUtilityTab === "activity") {
                mobileRoomActivityUnreadCount = 0;
            } else {
                mobileRoomActivityUnreadCount += claimedCount;
                renderMobileNavDock();
            }
        } else if (claimedCount) {
            noteRoomActivityEntriesAdded(claimedCount);
        }

        var mobileBody = syncMobileRoomActivityLog();
        if (isMobileViewport()) {
            return mobileBody;
        }

        var railBody = syncRailActivityLog();

        var sticky = mwin.children(".brave-sticky-view");
        var roomView = sticky.find(".brave-view--room").first();
        if (!roomView.length) {
            roomView = mwin.children(".brave-view--room").first();
        }

        if (!roomView.length) {
            return railBody || mobileBody;
        }

        var section = roomView.find(".brave-view__section--activitylog").first();
        if (!section.length) {
            return railBody || mobileBody;
        }

        var log = section.children(".brave-room-log");
        if (!log.length) {
            log = $("<div class='brave-room-log'><div class='brave-room-log__body' role='log' aria-live='polite' aria-relevant='additions text'></div></div>");
            section.append(log);
        }

        var body = log.children(".brave-room-log__body");
        if (!body.length) {
            body = $("<div class='brave-room-log__body' role='log' aria-live='polite' aria-relevant='additions text'></div>");
            log.append(body);
        }

        syncRoomActivityLog(body.get(0));
        return railBody || mobileBody || body;
    };

    var pushRoomFeedEntry = function (cls, rawText, meta) {
        if (isCombatUiActive()) {
            return;
        }
        var added = addRoomFeedEntry(cls, rawText, meta);
        if (added) {
            noteRoomActivityEntriesAdded(1);
        }
        syncRoomActivityLog();
        if (added && isMobileViewport()) {
            if (currentMobileUtilityTab === "activity") {
                mobileRoomActivityUnreadCount = 0;
                renderMobileUtilitySheet();
            } else {
                mobileRoomActivityUnreadCount += 1;
                renderMobileNavDock();
            }
            renderActivityToast(added);
        }
    };

    var clearRoomActivityLog = function () {
        currentRoomFeedEntries = [];
        roomActivityRailPinnedToBottom = true;
        roomActivityRailScrollTop = 0;
        roomActivityRailMissedCount = 0;
        clearRoomVoiceBubbles();
        syncRoomActivityLog();
    };

    var ensureCombatLog = function () {
        var mwin = $("#messagewindow");
        if (!mwin.length) {
            return null;
        }

        var sticky = mwin.children(".brave-sticky-view");
        var inlineSectionParent = sticky.find(".brave-view--combat .brave-view__sections").first();
        var useInlineStickyLog = sticky.length
            && document.body.getAttribute("data-brave-scene") === "combat";
        var preferredParent = useInlineStickyLog && inlineSectionParent.length ? inlineSectionParent : (useInlineStickyLog ? sticky : mwin);
        var fallbackParent = useInlineStickyLog ? inlineSectionParent.add(sticky).add(mwin) : sticky;

        var log = preferredParent.children(".brave-combat-log");
        if (!log.length && fallbackParent && fallbackParent.length) {
            log = fallbackParent.children(".brave-combat-log");
            if (log.length) {
                preferredParent.append(log);
            }
        }
        if (!log.length) {
            log = $(
                "<div class='brave-combat-log'>"
                + "<div class='brave-combat-log__head'>Battle Feed"
                + "<button type='button' class='brave-room-log__jump brave-combat-log__jump' data-brave-combat-scroll='latest' aria-label='Battle feed is at the latest line' disabled>Latest</button>"
                + "</div>"
                + "<div class='brave-combat-log__body' role='log' aria-live='polite' aria-relevant='additions text'></div>"
                + "</div>"
            );
            preferredParent.append(log);
        }

        var logBody = log.children(".brave-combat-log__body");
        if (!logBody.length) {
            logBody = $("<div class='brave-combat-log__body' role='log' aria-live='polite' aria-relevant='additions text'></div>");
            var existingEntries = log.children(".out, .msg, .err");
            if (!log.children(".brave-combat-log__head").length) {
                log.prepend(
                    "<div class='brave-combat-log__head'>Battle Feed"
                    + "<button type='button' class='brave-room-log__jump brave-combat-log__jump' data-brave-combat-scroll='latest' aria-label='Battle feed is at the latest line' disabled>Latest</button>"
                    + "</div>"
                );
            } else if (!log.children("[data-brave-combat-scroll='latest']").length) {
                log.children(".brave-combat-log__head").first().append(
                    "<button type='button' class='brave-room-log__jump brave-combat-log__jump' data-brave-combat-scroll='latest' aria-label='Battle feed is at the latest line' disabled>Latest</button>"
                );
            }
            log.append(logBody);
            if (existingEntries.length) {
                logBody.append(existingEntries);
            }
        }

        var strayEntries = mwin.children(".out, .msg, .err");
        if (strayEntries.length) {
            logBody.append(strayEntries);
        }

        var logBodyNode = logBody.get(0);
        bindCombatLogScrollState(logBodyNode);
        restoreCombatLogScroll(logBodyNode, combatLogPinnedToBottom);
        updateCombatLogCue();

        return logBody;
    };

    var clearSceneCard = function () {
        var card = document.getElementById("scene-card");
        if (card) {
            card.innerHTML = "";
            card.removeAttribute("data-brave-command");
            card.removeAttribute("data-brave-confirm");
            card.removeAttribute("title");
            card.removeAttribute("role");
            card.removeAttribute("tabindex");
            card.classList.remove("scene-card--clickable", "scene-card--scrollable", "brave-click");
        }
        currentSceneData = null;
        syncSceneRailLayout();
        syncMobileShell();
    };

    var clearSceneRail = function () {
        currentMapText = "";
        currentMapGrid = null;
        clearMicromap();
        clearPackPanel();
        clearVicinityPanel();
        clearSceneCard();
        syncSceneRailLayout();
        syncMobileShell();
    };

    var resetAllScrollPositions = function () {
        var mwin = $("#messagewindow");
        var targets = [];
        var pushTarget = function (node) {
            if (node && targets.indexOf(node) === -1) {
                targets.push(node);
            }
        };

        pushTarget(document.scrollingElement);
        pushTarget(document.documentElement);
        pushTarget(document.body);

        if (mwin.length) {
            pushTarget(mwin[0]);
            if (mwin.parent().length) {
                pushTarget(mwin.parent()[0]);
            }
            if (mwin.parent().parent().length) {
                pushTarget(mwin.parent().parent()[0]);
            }
        }

        var apply = function () {
            window.scrollTo(0, 0);
            targets.forEach(function (node) {
                try {
                    node.scrollTop = 0;
                    node.scrollLeft = 0;
                } catch (err) {
                    // Ignore non-scrollable targets.
                }
            });
        };

        apply();
        if (window.requestAnimationFrame) {
            window.requestAnimationFrame(apply);
        }
        window.setTimeout(apply, 0);
        window.setTimeout(apply, 80);
    };

    var captureMainScrollPositions = function () {
        var mwin = $("#messagewindow");
        var selectors = [
            "html",
            "body",
            "#main-sub",
            ".brave-gl-main-item",
            ".brave-gl-main-item > .lm_content",
            ".brave-gl-main-item > .lm_content > div",
            ".content",
            "#messagewindow",
            "#messagewindow > .brave-view",
            "#messagewindow > .brave-view--room",
            "#messagewindow .brave-view--room",
            "#messagewindow .brave-view--room .brave-view__sections",
            "#messagewindow .brave-view--room .brave-view__section--vicinity",
            "#messagewindow .brave-view--room .brave-view__section--activitylog",
            "#messagewindow .brave-view--room .brave-view__section--list",
        ];
        var snapshots = [];
        var seen = [];
        var pushSelector = function (selector) {
            if (!selector || seen.indexOf(selector) !== -1) {
                return;
            }
            seen.push(selector);
            var node = document.querySelector(selector);
            if (!node) {
                return;
            }
            snapshots.push({
                selector: selector,
                top: node.scrollTop || 0,
                left: node.scrollLeft || 0,
            });
        };

        selectors.forEach(pushSelector);

        if (mwin.length) {
            if (mwin.parent().length) {
                snapshots.push({
                    selector: null,
                    node: mwin.parent()[0],
                    top: mwin.parent()[0].scrollTop || 0,
                    left: mwin.parent()[0].scrollLeft || 0,
                });
            }
            if (mwin.parent().parent().length) {
                snapshots.push({
                    selector: null,
                    node: mwin.parent().parent()[0],
                    top: mwin.parent().parent()[0].scrollTop || 0,
                    left: mwin.parent().parent()[0].scrollLeft || 0,
                });
            }
        }

        return snapshots;
    };

    var restoreMainScrollPositions = function (snapshots) {
        var entries = Array.isArray(snapshots) ? snapshots.slice() : [];
        var apply = function () {
            entries.forEach(function (entry) {
                if (!entry) {
                    return;
                }
                var node = entry.selector ? document.querySelector(entry.selector) : entry.node;
                if (!node) {
                    return;
                }
                try {
                    node.scrollTop = entry.top || 0;
                    node.scrollLeft = entry.left || 0;
                } catch (err) {
                    // Ignore non-scrollable targets.
                }
            });
        };

        apply();
        if (window.requestAnimationFrame) {
            window.requestAnimationFrame(apply);
        }
        window.setTimeout(apply, 0);
        window.setTimeout(apply, 80);
        window.setTimeout(apply, 220);
        window.setTimeout(apply, 500);
        window.setTimeout(apply, 1000);
    };

    var resetStructuredPanel = function (panel) {
        if (!panel) {
            return;
        }
        panel.removeAttribute("data-brave-command");
        panel.removeAttribute("data-brave-confirm");
        panel.removeAttribute("title");
        panel.removeAttribute("role");
        panel.removeAttribute("tabindex");
        panel.classList.remove("scene-card--clickable", "scene-card--scrollable", "brave-click");
    };

    var renderStructuredPanel = function (panel, panelData) {
        if (!panel) {
            return;
        }

        resetStructuredPanel(panel);

        if (!panelData || typeof panelData !== "object") {
            panel.innerHTML = "";
            return;
        }

        var chips = Array.isArray(panelData.chips) ? panelData.chips : [];
        var sections = Array.isArray(panelData.sections) ? panelData.sections : [];

        var renderChip = function (entry) {
            var tone = entry && entry.tone ? "scene-card__chip--" + escapeHtml(entry.tone) : "";
            return chip(entry && entry.label ? entry.label : "", entry && entry.icon ? entry.icon : "label", tone);
        };

        var renderPanelItem = function (entry) {
            var lead = "";
            if (entry && entry.badge) {
                lead = "<span class='scene-card__dir'><span>" + escapeHtml(entry.badge) + "</span></span>";
            } else if (entry && entry.icon) {
                lead = "<span class='scene-card__dir scene-card__dir--icon'>" + icon(entry.icon, "scene-card__dir-icon") + "</span>";
            } else {
                lead = "<span class='scene-card__dir scene-card__dir--icon'>" + icon("chevron_right", "scene-card__dir-icon") + "</span>";
            }
            var meterMarkup = "";
            if (entry && entry.meter) {
                var meterToneClass = entry.meter.tone ? " scene-card__meter--" + escapeHtml(entry.meter.tone) : "";
                var meterPercent = typeof entry.meter.percent === "number" ? entry.meter.percent : 0;
                meterPercent = Math.max(0, Math.min(100, meterPercent));
                meterMarkup =
                    "<div class='scene-card__meter" + meterToneClass + "'>"
                    + "<div class='scene-card__meter-track'><span class='scene-card__meter-fill' style='width: " + meterPercent + "%;'></span></div>"
                    + "<div class='scene-card__meter-value'>" + escapeHtml(entry.meter.value || "") + "</div>"
                    + "</div>";
            }
            var itemBody =
                lead
                + "<span class='scene-card__item-body'>"
                + "<span class='scene-card__text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
                + (entry && entry.meta ? "<span class='scene-card__item-meta'>" + escapeHtml(entry.meta) + "</span>" : "")
                + meterMarkup
                + "</span>";
            var inlineActions = renderInlineActions(entry && entry.actions);
            if (hasBrowserInteraction(entry)) {
                return (
                    "<li class='scene-card__item scene-card__item--interactive'>"
                    + "<div class='scene-card__item-row'>"
                    + "<button type='button' class='scene-card__item-button brave-click'"
                        + commandAttrs(entry, false)
                        + ">"
                        + itemBody
                        + "</button>"
                        + inlineActions
                    + "</div>"
                    + "</li>"
                );
            }
            return (
                "<li class='scene-card__item'>"
                + itemBody
                + inlineActions
                + "</li>"
            );
        };

        var renderListSection = function (label, iconName, items, formatter) {
            if (!Array.isArray(items) || !items.length) {
                return "";
            }
            var heading = label
                ? "<div class='scene-card__label'>"
                    + icon(iconName, "scene-card__section-icon")
                    + "<span>" + escapeHtml(label) + "</span>"
                    + "</div>"
                : "";
            return (
                "<section class='scene-card__section'>"
                + heading
                + "<ul class='scene-card__list'>"
                + items.map(formatter).join("")
                + "</ul>"
                + "</section>"
            );
        };

        var renderedSections = sections
            .map(function (section) {
                return renderListSection(
                    section && section.label ? section.label : "",
                    section && section.icon ? section.icon : "label",
                    section && Array.isArray(section.items) ? section.items : [],
                    renderPanelItem
                );
            })
            .filter(Boolean);

        if (!renderedSections.length && !panelData.hide_empty_state) {
            renderedSections.push(
                "<section class='scene-card__section'>"
                + "<div class='scene-card__empty'>"
                + icon("info", "scene-card__empty-icon")
                + "<span>No immediate points of interest.</span>"
                + "</div>"
                + "</section>"
            );
        }

        panel.innerHTML =
            "<div class='scene-card__eyebrow'>"
            + icon(panelData.eyebrow_icon || "label", "scene-card__eyebrow-icon")
            + "<span>" + escapeHtml(panelData.eyebrow || "") + "</span>"
            + "</div>"
            + ((panelData.title_icon || panelData.title)
                ? "<div class='scene-card__title'>"
                    + icon(panelData.title_icon || "home_pin", "scene-card__title-icon")
                    + "<span>" + escapeHtml(panelData.title || "") + "</span>"
                    + "</div>"
                : "")
            + (panelData.subtitle ? "<div class='scene-card__subtitle'>" + escapeHtml(panelData.subtitle) + "</div>" : "")
            + (chips.length ? "<div class='scene-card__meta'>" + chips.map(renderChip).join("") + "</div>" : "")
            + renderedSections.join("");
    };

    var renderStructuredCard = function (card, panelData) {
        if (!card) {
            return;
        }
        if (!panelData || typeof panelData !== "object") {
            clearSceneCard();
            return;
        }
        renderStructuredPanel(card, panelData);
    };

    var buildRoomActionRailMarkup = function (roomView) {
        if (!roomView || !Array.isArray(roomView.room_actions) || !roomView.room_actions.length) {
            return "";
        }
        var orderedActions = [];
        var chatAction = null;
        var emoteAction = null;
        roomView.room_actions.forEach(function (action) {
            var label = String(action && (action.label || action.text) || "").trim().toLowerCase();
            if (label === "chat") {
                if (!chatAction) {
                    chatAction = {
                        label: action.label || action.text || "Chat",
                        icon: action.icon && action.icon !== "chat" ? action.icon : "forum",
                        detail: action.detail || action.tooltip || "Open nearby chat.",
                        overlay: "chat",
                        aria_label: action.aria_label || "Open nearby chat",
                    };
                }
                return;
            }
            if (label === "emote") {
                if (!emoteAction) {
                    emoteAction = action;
                }
                return;
            }
            orderedActions.push(action);
        });
        if (!chatAction) {
            chatAction = {
                label: "Chat",
                icon: "forum",
                detail: "Open nearby chat.",
                overlay: "chat",
                aria_label: "Open nearby chat",
            };
        }
        if (emoteAction) {
            orderedActions.push(emoteAction);
        }
        orderedActions.push(chatAction);
        return (
            "<div class='brave-room-actions' aria-label='Room actions'>"
            + orderedActions.map(function (action) {
                if (!action || (!action.command && !action.picker && action.overlay !== "chat")) {
                    return "";
                }
                var ariaLabel = action.aria_label || action.label || action.text || "Action";
                var title = action.tooltip || action.detail || action.label || action.text || "";
                var text = action.label || action.text || "";
                var iconName = action.icon || "bolt";
                var buttonClass = "brave-room-actions__button brave-click";
                if (text.toLowerCase() === "emote") {
                    buttonClass += " brave-room-actions__button--emote";
                }
                return (
                    "<button type='button' class='" + buttonClass + "'"
                    + (action.command ? " data-brave-command='" + escapeHtml(action.command) + "'" : "")
                    + (action.picker ? " data-brave-picker='" + escapeHtml(JSON.stringify(action.picker)) + "'" : "")
                    + (action.overlay === "chat" ? " data-brave-chat-open='1'" : "")
                    + (title ? " title='" + escapeHtml(title) + "'" : "")
                    + " aria-label='" + escapeHtml(ariaLabel) + "'>"
                    + icon(iconName, "brave-room-actions__button-icon")
                    + "<span class='brave-room-actions__button-label'>" + escapeHtml(text) + "</span>"
                    + "</button>"
                );
            }).join("")
            + "</div>"
        );
    };

    var buildRoomVicinityPanelData = function (roomView) {
        if (!isRoomLikeView(roomView) || !Array.isArray(roomView.sections)) {
            return null;
        }
        var vicinitySection = null;
        for (var i = 0; i < roomView.sections.length; i += 1) {
            var section = roomView.sections[i];
            if (section && section.kind === "list" && section.variant === "vicinity") {
                vicinitySection = section;
                break;
            }
        }
        if (!vicinitySection) {
            return null;
        }
        var items = Array.isArray(vicinitySection.items) ? vicinitySection.items : [];
        return {
            eyebrow: "The Vicinity",
            eyebrow_icon: vicinitySection.icon || "visibility",
            title: "",
            hide_empty_state: true,
            sections: [
                {
                    label: "",
                    icon: vicinitySection.icon || "visibility",
                    items: items.map(function (entry) {
                        return {
                            text: entry && (entry.text || entry.label) ? (entry.text || entry.label) : "",
                            meta: entry && entry.meta ? entry.meta : "",
                            badge: entry && entry.badge ? entry.badge : "",
                            icon: entry && entry.icon ? entry.icon : "chevron_right",
                            command: entry && entry.command ? entry.command : "",
                            prefill: entry && entry.prefill ? entry.prefill : "",
                            picker: entry && entry.picker ? entry.picker : null,
                            on_open_command: entry && entry.on_open_command ? entry.on_open_command : "",
                            dismiss_bubble_speaker: entry && entry.dismiss_bubble_speaker ? entry.dismiss_bubble_speaker : "",
                            connection_screen: entry && entry.connection_screen ? entry.connection_screen : "",
                            tooltip: entry && entry.tooltip ? entry.tooltip : "",
                            confirm: entry && entry.confirm ? entry.confirm : "",
                        };
                    }),
                }
            ],
        };
    };

    var renderRailActivityPanel = function (panel) {
        if (!panel) {
            return;
        }
        var body = panel.querySelector(".brave-room-log__body--rail");
        if (!body) {
            panel.innerHTML =
                "<div class='brave-room-activity-shell'>"
                + "<div class='brave-room-actions-shell'></div>"
                + "<div class='brave-room-activity-card'>"
                + "<div class='scene-card__eyebrow scene-pack-panel__title'>"
                + icon("forum", "scene-card__eyebrow-icon scene-pack-panel__title-icon")
                + "<div class='brave-room-activity-card__tabs' data-brave-room-tabs-host='1'></div>"
                + "<button type='button' class='brave-room-log__jump' data-brave-activity-scroll='rail' aria-label='Activity is at the latest line' disabled>0</button>"
                + "</div>"
                + "<div class='brave-room-activity-pane brave-room-activity-pane--activity' data-brave-room-pane='activity'>"
                + "<div class='brave-room-log brave-room-log--rail'>"
                + "<div class='brave-room-log__body brave-room-log__body--rail' role='log' aria-live='polite' aria-relevant='additions text'></div>"
                + "</div>"
                + "</div>"
                + "<div class='brave-room-activity-pane brave-room-activity-pane--nearby brave-room-activity-pane--hidden' data-brave-room-pane='nearby'>"
                + "<div class='brave-room-nearby-host' data-brave-room-nearby='1'></div>"
                + "</div>"
                + "</div>"
                + "</div>";
            body = panel.querySelector(".brave-room-log__body--rail");
        } else if (!panel.querySelector("[data-brave-activity-scroll='rail']")) {
            var title = panel.querySelector(".scene-pack-panel__title");
            if (title) {
                title.insertAdjacentHTML(
                    "beforeend",
                    "<button type='button' class='brave-room-log__jump' data-brave-activity-scroll='rail' aria-label='Activity is at the latest line' disabled>0</button>"
                );
            }
        }
        var shell = panel.querySelector(".brave-room-actions-shell");
        if (shell) {
            shell.innerHTML = buildRoomActionRailMarkup(currentViewData);
            shell.classList.toggle("brave-room-actions-shell--empty", !shell.innerHTML.trim());
        }
        panel.removeAttribute("data-brave-command");
        panel.removeAttribute("title");
        panel.removeAttribute("role");
        panel.removeAttribute("tabindex");
        panel.classList.remove("brave-click");
        syncRailActivityLog();
        syncRoomActivityCardSurface(panel, currentViewData, { mobile: false });
        syncRoomVoiceBubbleHosts();
        updateRailActivityCue();
    };

    var renderVicinityPanel = function (roomView) {
        var panel = document.getElementById("scene-vicinity-panel");
        if (!panel) {
            return;
        }

        if (isCombatUiActive() && !isRoomLikeView(roomView)) {
            clearVicinityPanel();
            syncSceneRailLayout();
            return;
        }

        if (!isMobileViewport() && isRoomLikeView(roomView)) {
            renderRailActivityPanel(panel);
            syncSceneRailLayout();
            return;
        }

        var panelData = !isMobileViewport() ? buildRoomVicinityPanelData(roomView) : null;
        renderStructuredPanel(panel, panelData);
        syncSceneRailLayout();
    };

    var renderPackPanel = function () {
        var panel = document.getElementById("scene-pack-panel");
        if (!panel) {
            return;
        }

        if (combatViewTransitionActive) {
            clearPackPanel();
            syncSceneRailLayout();
            return;
        }

        var roomView = getCurrentRoomView();
        var pack = roomView && roomView.mobile_pack ? roomView.mobile_pack : null;
        if (!pack) {
            clearPackPanel();
            syncSceneRailLayout();
            return;
        }

        var silver = typeof pack.silver === "number" ? pack.silver : 0;
        var items = Array.isArray(pack.items) ? pack.items.slice(0, 60) : [];
        var overflow = typeof pack.overflow === "number" ? pack.overflow : 0;

        panel.innerHTML =
            "<div class='scene-pack-panel__head'>"
            + "<div class='scene-card__eyebrow scene-pack-panel__title'>" + icon("backpack", "scene-card__eyebrow-icon scene-pack-panel__title-icon") + "<span>Pack</span></div>"
            + "<div class='scene-pack-panel__silver'><span class='scene-pack-panel__silver-label'>Silver</span><span class='scene-pack-panel__silver-value'>" + escapeHtml(String(silver)) + "</span></div>"
            + "</div>"
            + (items.length
                ? "<div class='scene-pack-panel__items'>"
                    + items.map(function (entry) {
                        var quantity = typeof entry.quantity === "number" ? entry.quantity : 0;
                        return (
                            "<div class='scene-pack-panel__item'>"
                            + "<span class='scene-pack-panel__item-icon'>" + icon(entry && entry.icon ? entry.icon : "backpack") + "</span>"
                            + "<span class='scene-pack-panel__item-label'>" + escapeHtml(entry && entry.label ? entry.label : "") + "</span>"
                            + (quantity > 1 ? "<span class='scene-pack-panel__item-qty'>x" + escapeHtml(String(quantity)) + "</span>" : "")
                            + "</div>"
                        );
                    }).join("")
                    + (overflow > 0 ? "<div class='scene-pack-panel__overflow'>+" + escapeHtml(String(overflow)) + " more</div>" : "")
                    + "</div>"
                : "<div class='scene-pack-panel__empty'>Pack is empty.</div>");
        panel.setAttribute("data-brave-command", "pack");
        panel.setAttribute("title", "pack");
        panel.setAttribute("role", "button");
        panel.setAttribute("tabindex", "0");
        panel.classList.add("brave-click");
        syncSceneRailLayout();
    };

    var renderPanelCard = function (panelData) {
        var card = document.getElementById("scene-card");
        if (!card) {
            return;
        }

        renderStructuredCard(card, panelData);
        syncSceneRailLayout();
    };

    var renderSceneCard = function (sceneData) {
        currentRoomSceneData = (sceneData && typeof sceneData === "object") ? sceneData : {};
        if (!canRenderSceneRailNow()) {
            clearSceneCard();
            return;
        }
        setMainViewMode(false);
        if (!sceneData || typeof sceneData !== "object" || !sceneData.tracked_quest) {
            clearSceneCard();
            return;
        }

        currentSceneData = sceneData;

        var tracked = sceneData.tracked_quest || {};
        var objectiveItems = Array.isArray(tracked.objectives)
            ? tracked.objectives.map(function (entry) {
                if (entry && typeof entry === "object") {
                    return {
                        text: entry.text || "",
                        icon: entry.completed ? "check_box" : "check_box_outline_blank",
                    };
                }
                return { text: entry, icon: "check_box_outline_blank" };
            })
            : [];

        renderPanelCard({
            eyebrow: "Tracked Quest",
            eyebrow_icon: "flag",
            title: tracked.title || "",
            title_icon: "assignment",
            subtitle: tracked.giver || "",
            hide_empty_state: true,
            sections: objectiveItems.length ? [{
                label: "Objectives",
                items: objectiveItems,
            }] : [],
        });

        var card = document.getElementById("scene-card");
        if (card) {
            card.setAttribute("data-brave-command", "quests");
            card.setAttribute("title", "quests");
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", "0");
            card.classList.add("scene-card--clickable", "scene-card--scrollable", "brave-click");
        }
        syncMobileShell();
    };

    var renderMainView = function (viewData, options) {
        options = options || {};
        var mwin = $("#messagewindow");
        if (!mwin.length) {
            return;
        }
        var hasArcadeSection = !!(
            viewData
            && Array.isArray(viewData.sections)
            && viewData.sections.some(function (section) {
                return section && section.kind === "arcade";
            })
        );
        if (!hasArcadeSection) {
            teardownArcadeMode();
        }

        if (!viewData || typeof viewData !== "object") {
            clearCombatTransitionState();
            clearTextOutput();
            clearSceneCard();
            return;
        }
        if (
            !options.skipRoomPreserve
            && !(pendingArcadeRoomRestore && isRoomLikeView(viewData))
            && shouldPreserveCurrentViewOnRoomRefresh(viewData)
        ) {
            currentRoomViewData = viewData;
            if (currentMobileUtilityTab && isMobileViewport()) {
                renderMobileNavDock();
                renderMobileUtilitySheet();
            }
            return;
        }
        if (pendingArcadeRoomRestore && isRoomLikeView(viewData)) {
            pendingArcadeRoomRestore = false;
        }
        allowNextRoomRefreshNavigationUntil = 0;
        if (!options.skipCombatTransition && pendingCombatTransitionViewData) {
            if (
                (pendingCombatTransitionMode === "enter" && viewData.variant === "combat")
                || (pendingCombatTransitionMode === "return" && isRoomLikeView(viewData))
            ) {
                pendingCombatTransitionViewData = viewData;
                return;
            }
            clearCombatTransitionState();
        }
        if (shouldQueueCombatResultView(viewData)) {
            clearDeferredCombatViewRender();
            pendingCombatResultViewData = viewData;
            pendingCombatPanelData = null;
            scheduleCombatResultFallback();
            scheduleCombatFxFlush(0);
            return;
        }
        if (shouldDeferCombatViewRender(viewData)) {
            deferCombatViewRender(viewData);
            scheduleCombatFxFlush(0);
            return;
        }
        if (viewData.variant !== "combat-result" && !isRoomLikeView(viewData)) {
            pendingCombatResultReturnTransition = false;
        }
        if (viewData.variant !== "combat") {
            clearDeferredCombatViewRender();
            pendingCombatResultViewData = null;
            pendingCombatPanelData = null;
        }
        syncInputContextForView(viewData);
        var preservePickerOnRefresh = shouldPreservePickerOnViewRefresh(viewData);
        var preserveMobileSheetOnRefresh = !!(isRoomLikeView(viewData) && currentMobileUtilityTab);
        if (!preservePickerOnRefresh) {
            clearPickerSheet();
        }

        var preserveRail = !!(viewData.layout === "explore" || viewData.preserve_rail);
        var stickyView = !!viewData.sticky;
        var isCombatView = viewData.variant === "combat";
        var previousRoomViewForRefresh = isRoomLikeView(currentViewData)
            ? currentViewData
            : (isRoomLikeView(currentRoomViewData) ? currentRoomViewData : null);
        var isSameRoomReactiveRefresh = !!(
            isRoomLikeView(viewData)
            && previousRoomViewForRefresh
            && getReactiveSourceId(viewData)
            && getReactiveSourceId(viewData) === getReactiveSourceId(previousRoomViewForRefresh)
            && String(viewData.room_id || "") === String(previousRoomViewForRefresh.room_id || "")
        );
        var enteringCombat = !!(isCombatView && (!currentViewData || currentViewData.variant !== "combat"));
        var hasCombatResultContext = !!(
            pendingCombatResultReturnTransition
            || (currentViewData && currentViewData.variant === "combat-result")
            || document.querySelector("#messagewindow .brave-view--combat-result")
            || (document.body && document.body.getAttribute("data-brave-scene") === "victory")
        );
        var leavingCombatResult = !!(
            !isCombatView
            && hasCombatResultContext
            && isRoomLikeView(viewData)
        );
        var variantClass = viewData.variant ? " brave-view--" + escapeHtml(viewData.variant) : "";
        var toneClass = viewData.tone ? " brave-view--tone-" + escapeHtml(viewData.tone) : "";
        if (!options.skipCombatTransition && enteringCombat) {
            blurActiveUiControl();
            suppressMobileNonInputFocus(1200);
            if (startCombatTransition(viewData, "enter")) {
                return;
            }
        }
        if (isCombatView) {
            combatViewTransitionActive = true;
        }
        applyReactiveState(viewData.reactive || {});
        renderObjectives(viewData);
        var previousRoomSceneMeta = lastRenderedRoomSceneMeta || getRenderedRoomSceneMeta();
        var nextRoomSceneMeta = getRoomSceneMeta(viewData);
        var shouldAnimateRegionSceneCard = !!(
            nextRoomSceneMeta
            && previousRoomSceneMeta
            && previousRoomSceneMeta.roomId
            && nextRoomSceneMeta.roomId
            && previousRoomSceneMeta.roomId !== nextRoomSceneMeta.roomId
            && previousRoomSceneMeta.regionKey
            && nextRoomSceneMeta.regionKey
            && previousRoomSceneMeta.regionKey !== nextRoomSceneMeta.regionKey
        );
        var shouldAnimateFirstRegionDiscoverySceneCard = !!(
            shouldAnimateRegionSceneCard
            && viewData
            && viewData.first_region_discovery
        );
        var shouldAnimateRoomSceneCard = !!(
            !options.skipRoomCardTransition
            && previousRoomSceneMeta
            && nextRoomSceneMeta
            && previousRoomSceneMeta.roomId
            && nextRoomSceneMeta.roomId
            && previousRoomSceneMeta.roomId !== nextRoomSceneMeta.roomId
            && previousRoomSceneMeta.regionKey === nextRoomSceneMeta.regionKey
        );
        var shouldApplyRoomSceneEnterClass = !!(
            isRoomLikeView(viewData)
            && !options.skipRoomCardTransition
            && !shouldAnimateRegionSceneCard
            && !shouldAnimateFirstRegionDiscoverySceneCard
            && (
                !previousRoomSceneMeta
                || !previousRoomSceneMeta.roomId
                || (nextRoomSceneMeta && previousRoomSceneMeta.roomId !== nextRoomSceneMeta.roomId)
            )
        );

        var renderChip = function (entry) {
            var tone = entry && entry.tone ? "scene-card__chip--" + escapeHtml(entry.tone) : "";
            return chip(entry && entry.label ? entry.label : "", entry && entry.icon ? entry.icon : "label", tone);
        };

        var renderPairs = function (items) {
            return (
                "<div class='brave-view__pairs'>"
                + (items || []).map(function (entry) {
                    return (
                        "<div class='brave-view__pair'>"
                        + "<div class='brave-view__pair-label'>"
                        + (entry && entry.icon ? icon(entry.icon, "brave-view__pair-icon") : "")
                        + "<span>" + escapeHtml(entry && entry.label ? entry.label : "") + "</span>"
                        + "</div>"
                        + "<div class='brave-view__pair-value'>" + escapeHtml(entry && entry.value ? entry.value : "") + "</div>"
                        + "</div>"
                    );
                }).join("")
                + "</div>"
            );
        };

        var renderMeters = function (meters) {
            if (!Array.isArray(meters) || !meters.length) {
                return "";
            }
            return (
                "<div class='brave-view__meters'>"
                + meters.map(function (meter) {
                    var toneClass = meter && meter.tone ? " brave-view__meter--" + escapeHtml(meter.tone) : "";
                    var percent = meter && typeof meter.percent === "number" ? meter.percent : 0;
                    percent = Math.max(0, Math.min(100, percent));
                    var meterMeta = meter && meter.meta && typeof meter.meta === "object" ? meter.meta : null;
                    var meterAttrs = "";
                    if (meterMeta && meterMeta.kind === "atb") {
                        meterAttrs += " data-meter-kind='atb'";
                        meterAttrs += " data-atb-phase='" + escapeHtml(meterMeta.phase || "charging") + "'";
                        meterAttrs += " data-atb-gauge='" + escapeHtml(meterMeta.gauge || 0) + "'";
                        meterAttrs += " data-atb-phase-start-gauge='" + escapeHtml(meterMeta.phase_start_gauge || 0) + "'";
                        meterAttrs += " data-atb-phase-started-at='" + escapeHtml(meterMeta.phase_started_at_ms || 0) + "'";
                        meterAttrs += " data-atb-phase-duration='" + escapeHtml(meterMeta.phase_duration_ms || 0) + "'";
                        meterAttrs += " data-atb-phase-remaining='" + escapeHtml(meterMeta.phase_remaining_ms || 0) + "'";
                        meterAttrs += " data-atb-ready='" + escapeHtml(meterMeta.ready_gauge || 400) + "'";
                        meterAttrs += " data-atb-fill-rate='" + escapeHtml(meterMeta.fill_rate || 100) + "'";
                        meterAttrs += " data-atb-tick-ms='" + escapeHtml(meterMeta.tick_ms || 1000) + "'";
                    }
                    var hideValue = !!(meterMeta && meterMeta.hide_value);
                    var fillStyle = "width: " + percent + "%;";
                    return (
                        "<div class='brave-view__meter" + toneClass + "'" + meterAttrs + ">"
                        + "<div class='brave-view__meter-head'>"
                        + "<span class='brave-view__meter-label'>" + escapeHtml(meter && meter.label ? meter.label : "") + "</span>"
                        + (hideValue ? "" : "<span class='brave-view__meter-value'>" + escapeHtml(meter && meter.value ? meter.value : "") + "</span>")
                        + "</div>"
                        + "<div class='brave-view__meter-track'><span class='brave-view__meter-fill' style='" + fillStyle + "'></span></div>"
                        + "</div>"
                    );
                }).join("")
                + "</div>"
            );
        };

        var renderList = function (items) {
            return (
                "<ul class='brave-view__list'>"
                + (items || []).map(function (entry) {
                    var lead = "";
                    var marker = "";
                    if (entry && entry.badge) {
                        lead = "<span class='brave-view__badge'>" + escapeHtml(entry.badge) + "</span>";
                    } else {
                        lead = "<span class='brave-view__bullet'>"
                            + icon(entry && entry.icon ? entry.icon : "chevron_right", "brave-view__bullet-icon")
                            + "</span>";
                    }
                    if (entry && entry.marker_icon) {
                        marker = "<span class='brave-view__list-marker'>"
                            + icon(entry.marker_icon, "brave-view__list-marker-icon")
                            + "</span>";
                    }
                    var textBody = "<span class='brave-view__list-copy'>"
                        + "<span class='brave-view__list-text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
                        + ((entry && entry.detail)
                            ? "<span class='brave-view__list-detail'>" + escapeHtml(entry.detail) + "</span>"
                            : "")
                        + "</span>";
                    var rowClass = "brave-view__list-item";
                    var speakerAttr = (entry && entry.text) ? " data-brave-speaker='" + escapeHtml(entry.text) + "'" : "";
                    var interactive = hasBrowserInteraction(entry);
                    if (interactive) {
                        rowClass += " brave-click brave-click--row";
                    }
                    var hasInlineActions = !!(entry && Array.isArray(entry.actions) && entry.actions.length);
                    if (interactive && hasInlineActions) {
                        rowClass += " brave-view__list-item--with-actions";
                        return (
                            "<li class='brave-view__list-row'" + speakerAttr + ">"
                            + "<div class='" + rowClass + "'>"
                            + "<button type='button' class='brave-view__list-primary brave-click brave-click--row'"
                            + commandAttrs(entry, false)
                            + ">"
                            + "<div class='brave-view__list-main'>"
                            + lead
                            + textBody
                            + marker
                            + "</div>"
                            + "</button>"
                            + renderInlineActions(entry && entry.actions)
                            + "</div>"
                            + "</li>"
                        );
                    }
                    if (interactive) {
                        return (
                            "<li class='brave-view__list-row'" + speakerAttr + ">"
                            + "<button type='button' class='" + rowClass + "'"
                            + commandAttrs(entry, false)
                            + ">"
                            + "<div class='brave-view__list-main'>"
                            + lead
                            + textBody
                            + marker
                            + "</div>"
                            + "</button>"
                            + "</li>"
                        );
                    }
                    return (
                        "<li class='" + rowClass + "'" + speakerAttr + ">"
                        + "<div class='brave-view__list-main'>"
                        + lead
                        + textBody
                        + marker
                        + "</div>"
                        + renderInlineActions(entry && entry.actions)
                        + "</li>"
                    );
                }).join("")
                + "</ul>"
            );
        };

        var renderLines = function (section) {
            var variantClass = section && section.variant ? " brave-view__lines--" + escapeHtml(section.variant) : "";
            return (
                "<div class='brave-view__lines" + variantClass + "'>"
                + ((section && section.lines) || []).map(function (line) {
                    var lineClass = "brave-view__line" + (section && section.variant ? " brave-view__line--" + escapeHtml(section.variant) : "");
                    return "<div class='" + lineClass + "'>" + escapeHtml(line) + "</div>";
                }).join("")
                + "</div>"
            );
        };

        var renderForm = function (section) {
            var submitMode = section && section.submit_mode ? section.submit_mode : "command";
            var submitLabel = section && section.submit_label ? section.submit_label : "Submit";
            var submitToneClass = section && section.submit_tone ? " brave-view__action--" + escapeHtml(section.submit_tone) : "";
            var fields = Array.isArray(section && section.fields) && section.fields.length
                ? section.fields
                : [section || {}];

            var fieldMarkup = fields.map(function (field, index) {
                var fieldName = field && field.field_name ? field.field_name : (index === 0 ? "value" : "value_" + index);
                var fieldId = "brave-form-" + escapeHtml(fieldName).replace(/[^a-zA-Z0-9_-]/g, "-") + "-" + index;
                var inputType = field && field.input_type ? field.input_type : "text";
                var attrs = "";
                if (field && field.maxlength) {
                    attrs += " maxlength='" + escapeHtml(String(field.maxlength)) + "'";
                }
                if (field && field.minlength) {
                    attrs += " minlength='" + escapeHtml(String(field.minlength)) + "'";
                }
                if (field && field.placeholder) {
                    attrs += " placeholder='" + escapeHtml(field.placeholder) + "'";
                }
                if (field && field.autocomplete) {
                    attrs += " autocomplete='" + escapeHtml(field.autocomplete) + "'";
                }
                if (field && field.autocapitalize) {
                    attrs += " autocapitalize='" + escapeHtml(field.autocapitalize) + "'";
                }
                if (field && field.enterkeyhint) {
                    attrs += " enterkeyhint='" + escapeHtml(field.enterkeyhint) + "'";
                }
                if (field && field.spellcheck === false) {
                    attrs += " spellcheck='false'";
                }
                if (field && field.autofocus) {
                    attrs += " data-brave-autofocus='1'";
                }

                return (
                    "<div class='brave-view__field'>"
                    + (field && field.field_label
                        ? "<label class='brave-view__field-label' for='" + fieldId + "'>" + escapeHtml(field.field_label) + "</label>"
                        : "")
                    + "<input class='brave-view__field-input'"
                    + " type='" + escapeHtml(inputType) + "'"
                    + " id='" + fieldId + "'"
                    + " name='" + escapeHtml(fieldName) + "'"
                    + " value='" + escapeHtml(field && field.value ? field.value : "") + "'"
                    + attrs
                    + ">"
                    + "</div>"
                );
            }).join("");

            return (
                "<form class='brave-view__form' data-brave-form='1'"
                + " data-brave-submit-mode='" + escapeHtml(submitMode) + "'"
                + (section && section.submit_command ? " data-brave-submit-command='" + escapeHtml(section.submit_command) + "'" : "")
                + (section && section.submit_prefix ? " data-brave-submit-prefix='" + escapeHtml(section.submit_prefix) + "'" : "")
                + (section && section.submit_template ? " data-brave-submit-template='" + escapeHtml(section.submit_template) + "'" : "")
                + ">"
                + fieldMarkup
                + "<button type='submit' class='brave-view__action brave-view__form-submit" + submitToneClass + "'>"
                + icon(section && section.submit_icon ? section.submit_icon : "arrow_forward", "brave-view__action-icon")
                + "<span>" + escapeHtml(submitLabel) + "</span>"
                + "</button>"
                + "</form>"
            );
        };

        var renderMapGridCell = function (cell, showMarkers) {
            var tile = cell && typeof cell === "object" ? cell : {};
            var kind = tile.kind || "empty";
            var classes = "brave-view__map-cell brave-view__map-cell--" + escapeHtml(kind);
            var body = "";
            var title = tile.title ? " title='" + escapeHtml(tile.title) + "'" : "";

            if (kind === "room") {
                if (tile.tone) {
                    classes += " brave-view__map-cell--" + escapeHtml(tile.tone);
                }
                if (tile.primary_marker) {
                    classes += " brave-view__map-cell--marker-" + escapeHtml(tile.primary_marker);
                }
                var markers = showMarkers && Array.isArray(tile.markers) ? tile.markers : [];
                var badges = markers.slice(1);
                var visibleBadges = badges.slice(0, 3);
                var overflow = badges.length - visibleBadges.length;
                var badgeMarkup = "";
                if (visibleBadges.length || overflow > 0) {
                    badgeMarkup = "<span class='brave-view__map-badges'>"
                        + visibleBadges.map(function (marker) {
                            var toneClass = marker && marker.tone ? " brave-view__map-badge--" + escapeHtml(marker.tone) : "";
                            var markerTitle = marker && marker.label ? " title='" + escapeHtml(marker.label) + "'" : "";
                            return "<span class='brave-view__map-badge" + toneClass + "'" + markerTitle + ">"
                                + icon(marker && marker.icon ? marker.icon : "guarded-tower", "brave-view__map-badge-icon")
                                + "</span>";
                        }).join("")
                        + (overflow > 0
                            ? "<span class='brave-view__map-badge brave-view__map-badge--overflow'>+" + escapeHtml(String(overflow)) + "</span>"
                            : "")
                        + "</span>";
                }
                body = "<span class='brave-view__map-room-primary'>"
                    + icon(tile.symbol || "guarded-tower", "brave-view__map-room-icon")
                    + "</span>"
                    + badgeMarkup;
            } else if (kind === "connector") {
                var axis = tile.axis === "vertical" ? "vertical" : "horizontal";
                classes += " brave-view__map-cell--connector-" + escapeHtml(axis);
                body = "<span class='brave-view__map-connector brave-view__map-connector--" + escapeHtml(axis) + "'></span>";
            }

            return "<span class='" + classes + "'" + title + ">" + body + "</span>";
        };

        var renderMapGrid = function (grid, extraClass) {
            if (!grid || !Array.isArray(grid.rows) || !grid.rows.length) {
                return "";
            }
            var columns = grid.columns || (Array.isArray(grid.rows[0]) ? grid.rows[0].length : 0);
            if (!columns) {
                return "";
            }
            var gridClass = "brave-view__map-grid" + (extraClass ? " " + extraClass : "");
            var showMarkers = gridClass.indexOf("brave-view__map-grid--micro") === -1
                && gridClass.indexOf("brave-view__map-grid--compact") === -1;
            var cells = [];
            grid.rows.forEach(function (row) {
                (Array.isArray(row) ? row : []).forEach(function (cell) {
                    cells.push(renderMapGridCell(cell, showMarkers));
                });
            });
            return "<div class='" + gridClass + "' style='--brave-map-columns: " + columns + ";'>" + cells.join("") + "</div>";
        };

        var renderPre = function (section) {
            var toneClass = section && section.tone ? " brave-view__pre--" + escapeHtml(section.tone) : "";
            var text = escapeHtml(section && section.text ? section.text : "");
            if (section && section.tone === "map" && section.grid) {
                return "<div class='brave-view__pre" + toneClass + " brave-view__pre--mapgrid'>" + renderMapGrid(section.grid) + "</div>";
            }
            if (section && section.tone === "map") {
                return "<pre class='brave-view__pre" + toneClass + "'><span class='brave-view__pre-inner brave-view__pre-inner--map'>" + text + "</span></pre>";
            }
            return "<pre class='brave-view__pre" + toneClass + "'>" + text + "</pre>";
        };

        var renderNavPad = function (section, options) {
            options = options || {};
            var mobileMode = !!options.mobile;
            var entryMap = {};
            (section && section.items ? section.items : []).forEach(function (entry) {
                if (entry && entry.direction) {
                    entryMap[entry.direction] = entry;
                }
            });

            var renderNavCell = function (entry, positionClass) {
                if (!entry || !entry.command) {
                    return "<div class='brave-view__navslot " + positionClass.replace("navcard", "navslot") + "'></div>";
                }
                var classes = "brave-view__navcard brave-click " + positionClass;
                var content =
                    "<span class='brave-view__navcard-badge'>" + escapeHtml(entry.badge || "") + "</span>"
                    + "<span class='brave-view__navcard-label'>" + escapeHtml(entry.label || "") + "</span>";
                return (
                    "<button type='button' class='" + classes + "'"
                    + commandAttrs(entry, false)
                    + ">"
                    + content
                    + "</button>"
                );
            };

            var renderVerticalCenter = function (items) {
                var centerClass = "brave-view__navcenter";
                if (!Array.isArray(items) || !items.length) {
                    return "<div class='" + centerClass + "'></div>";
                }
                var visibleItems = items.slice(0, 2);
                var stackClass = "brave-view__nav-centerstack";
                if (visibleItems.length === 1) {
                    stackClass += " brave-view__nav-centerstack--single";
                }
                return (
                    "<div class='" + centerClass + "'>"
                    + "<div class='" + stackClass + "'>"
                    + visibleItems.map(function (entry) {
                        return (
                            "<button type='button' class='brave-view__nav-centercard brave-click'"
                            + commandAttrs(entry, false)
                            + ">"
                            + "<span class='brave-view__nav-chip-badge'>" + escapeHtml(entry.badge || "") + "</span>"
                            + "<span class='brave-view__nav-centercard-label'>" + escapeHtml(entry.label || "") + "</span>"
                            + "</button>"
                        );
                    }).join("")
                    + "</div>"
                    + "</div>"
                );
            };

            var renderMobileSwipeSurface = function () {
                var directions = [
                    { axis: "up", cue: "N", entry: entryMap.north },
                    { axis: "left", cue: "W", entry: entryMap.west },
                    { axis: "right", cue: "E", entry: entryMap.east },
                    { axis: "down", cue: "S", entry: entryMap.south },
                ];
                var available = directions.filter(function (item) {
                    return !!(item.entry && item.entry.command);
                });
                if (!available.length) {
                    return "";
                }

                var swipeAttrs = " data-brave-swipe-surface='1'";
                available.forEach(function (item) {
                    swipeAttrs += " data-brave-swipe-" + item.axis + "='" + escapeHtml(item.entry.command) + "'";
                });

                return (
                    "<div class='brave-view__swipe-surface'" + swipeAttrs + ">"
                    + "<div class='brave-view__swipe-title'>Swipe To Move</div>"
                    + "<div class='brave-view__swipe-copy'>Cardinal travel is gesture-based on mobile.</div>"
                    + directions.map(function (item) {
                        var cueClass = "brave-view__swipe-cue brave-view__swipe-cue--" + item.axis;
                        if (!(item.entry && item.entry.command)) {
                            cueClass += " brave-view__swipe-cue--disabled";
                            return "<span class='" + cueClass + "'>" + escapeHtml(item.cue) + "</span>";
                        }
                        return (
                            "<button type='button' class='" + cueClass + " brave-click'"
                            + " data-brave-command='" + escapeHtml(item.entry.command) + "'"
                            + " aria-label='Move " + escapeHtml(item.axis) + "'>"
                            + escapeHtml(item.cue)
                            + "</button>"
                        );
                    }).join("")
                    + "</div>"
                );
            };

            var renderMobileVerticalRoutes = function (items) {
                if (!Array.isArray(items) || !items.length) {
                    return "";
                }
                var visibleItems = items.slice(0, 2);
                var wrapClass = "brave-view__nav-vertical";
                if (visibleItems.length === 1) {
                    wrapClass += " brave-view__nav-vertical--single";
                }
                return (
                    "<div class='" + wrapClass + "'>"
                    + visibleItems.map(function (entry) {
                        return (
                            "<button type='button' class='brave-view__nav-centercard brave-click'"
                            + commandAttrs(entry, false)
                            + ">"
                            + "<span class='brave-view__nav-chip-badge'>" + escapeHtml(entry.badge || "") + "</span>"
                            + "<span class='brave-view__nav-centercard-label'>" + escapeHtml(entry.label || "") + "</span>"
                            + "</button>"
                        );
                    }).join("")
                    + "</div>"
                );
            };

            var renderOtherRoutes = function (items) {
                if (!Array.isArray(items) || !items.length) {
                    return "";
                }
                if (mobileMode) {
                    return (
                        "<div class='brave-view__nav-extra brave-view__nav-extra--routes'>"
                        + items.map(function (entry) {
                            return (
                                "<button type='button' class='brave-view__nav-chip brave-click'"
                                + commandAttrs(entry, false)
                                + ">"
                                + icon(entry && entry.icon ? entry.icon : "route", "brave-view__nav-chip-icon")
                                + "<span class='brave-view__nav-chip-label'>" + escapeHtml(entry && entry.text ? entry.text : entry && entry.label ? entry.label : "") + "</span>"
                                + "</button>"
                            );
                        }).join("")
                        + "</div>"
                    );
                }
                return (
                    "<div class='brave-view__nav-other'>"
                    + "<div class='brave-view__nav-other-label'>Other Routes</div>"
                    + renderList(items)
                    + "</div>"
                );
            };

            if (mobileMode) {
                return renderMobileNavPad(section);
            }

            return (
                "<div class='brave-view__navpad" + (mobileMode ? " brave-view__navpad--mobile" : "") + "'>"
                + "<div class='brave-view__navgrid" + (mobileMode ? " brave-view__navgrid--mobile" : "") + "'>"
                + renderNavCell(entryMap.north, "brave-view__navcard--north")
                + renderNavCell(entryMap.west, "brave-view__navcard--west")
                + renderVerticalCenter(section && section.vertical_items)
                + renderNavCell(entryMap.east, "brave-view__navcard--east")
                + renderNavCell(entryMap.south, "brave-view__navcard--south")
                + "</div>"
                + renderOtherRoutes(section && section.extra_items)
                + "</div>"
            );
        };

        var renderMobileRoomUtility = function () {
            return "";
        };

        var renderThemePreview = function (preview) {
            if (!preview || !preview.theme_key) {
                return "";
            }
            return (
                "<div class='brave-theme-preview' data-brave-theme-preview='" + escapeHtml(preview.theme_key) + "'>"
                + "<div class='brave-theme-preview__window'>"
                + "<div class='brave-theme-preview__eyebrow'>Brambleford</div>"
                + "<div class='brave-theme-preview__title'>Town Green</div>"
                + "<div class='brave-theme-preview__line'>Lanterns catch on brass and wet cobbles.</div>"
                + "<div class='brave-theme-preview__line'>A short look at the interface mood for this theme.</div>"
                + "</div>"
                + "</div>"
            );
        };

        var renderEntries = function (items) {
            var disableMobileCombatEntryFocus = !!(isMobileViewport() && viewData && viewData.variant === "combat");
            var renderEntryBodyLines = function (entry) {
                var lines = [];
                if (entry && Array.isArray(entry.lines)) {
                    lines = lines.concat(entry.lines);
                }
                if (entry && entry.summary) {
                    lines.push(entry.summary);
                }
                return lines.length
                    ? "<div class='brave-view__entry-body'>"
                        + lines.map(function (line) {
                            if (line && typeof line === "object") {
                                return (
                                    "<div class='brave-view__entry-line brave-view__entry-line--icon'>"
                                    + (line.icon ? icon(line.icon, "brave-view__entry-line-icon") : "")
                                    + "<span class='brave-view__entry-line-text'>" + escapeHtml(line.text || "") + "</span>"
                                    + "</div>"
                                );
                            }
                            return "<div class='brave-view__entry-line'>" + escapeHtml(line) + "</div>";
                        }).join("")
                        + "</div>"
                    : "";
            };

            var renderEntrySidecar = function (entry) {
                var backgroundIcon = entry && entry.background_icon ? entry.background_icon : "";
                var rowClass = "brave-view__entry brave-view__entry-sidecar";
                if (backgroundIcon) {
                    rowClass += " brave-view__entry--ornamented";
                }
                if (entry && entry.selected) {
                    rowClass += " brave-view__entry--selected";
                }
                var combatStateAttr = "";
                if (entry && Array.isArray(entry.combat_state) && entry.combat_state.length) {
                    combatStateAttr = " data-combat-state='" + escapeHtml(entry.combat_state.join(" ")) + "'";
                }
                var combatRefAttr = "";
                if (entry && entry.entry_ref) {
                    combatRefAttr = " data-entry-ref='" + escapeHtml(entry.entry_ref) + "'";
                }
                return (
                    "<div class='" + rowClass + "'" + combatStateAttr + combatRefAttr + commandAttrs(entry, !disableMobileCombatEntryFocus) + ">"
                    + (backgroundIcon ? icon(backgroundIcon, "brave-view__entry-ornament") : "")
                    + "<div class='brave-view__entry-head'>"
                    + ((entry && entry.badge)
                        ? "<span class='brave-view__entry-badge'>" + escapeHtml(entry.badge) + "</span>"
                        : (!backgroundIcon && !(entry && entry.hide_icon))
                            ? "<span class='brave-view__entry-icon-wrap'>" + icon(entry && entry.icon ? entry.icon : "pets", "brave-view__entry-icon") + "</span>"
                            : "")
                    + "<div class='brave-view__entry-heading'>"
                    + "<div class='brave-view__entry-title'>" + escapeHtml(entry && entry.title ? entry.title : "") + "</div>"
                    + (entry && entry.meta ? "<div class='brave-view__entry-meta'>" + escapeHtml(entry.meta) + "</div>" : "")
                    + "</div>"
                    + "</div>"
                    + renderMeters(entry && entry.meters)
                    + (entry && Array.isArray(entry.chips) && entry.chips.length
                        ? "<div class='brave-view__entry-chips'>" + entry.chips.map(renderChip).join("") + "</div>"
                        : "")
                    + renderEntryBodyLines(entry)
                    + "</div>"
                );
            };

            return (
                "<div class='brave-view__entries'>"
                + (items || []).map(function (entry) {
                    var lead = "";
                    var backgroundIcon = entry && entry.background_icon ? entry.background_icon : "";
                    if (entry && entry.badge) {
                        lead = "<span class='brave-view__entry-badge'>" + escapeHtml(entry.badge) + "</span>";
                    } else if (!backgroundIcon && !(entry && entry.hide_icon)) {
                        lead = "<span class='brave-view__entry-icon-wrap'>"
                            + icon(entry && entry.icon ? entry.icon : "inventory_2", "brave-view__entry-icon")
                            + "</span>";
                    }
                    var rowClass = "brave-view__entry";
                    if (backgroundIcon) {
                        rowClass += " brave-view__entry--ornamented";
                    }
                    if (entry && entry.size_class) {
                        rowClass += " brave-view__entry--size-" + String(entry.size_class);
                    }
                    if (hasBrowserInteraction(entry)) {
                        rowClass += " brave-click brave-click--row";
                    }
                    if (entry && entry.selected) {
                        rowClass += " brave-view__entry--selected";
                    }
                    if (entry && Array.isArray(entry.sidecars) && entry.sidecars.length) {
                        rowClass += " brave-view__entry--has-sidecars";
                    }
                    var combatStateAttr = "";
                    if (entry && Array.isArray(entry.combat_state) && entry.combat_state.length) {
                        combatStateAttr = " data-combat-state='" + escapeHtml(entry.combat_state.join(" ")) + "'";
                    }
                    var combatRefAttr = "";
                    if (entry && entry.entry_ref) {
                        combatRefAttr = " data-entry-ref='" + escapeHtml(entry.entry_ref) + "'";
                    }
                    var hasInlineActions = !!(entry && Array.isArray(entry.actions) && entry.actions.length);
                    var useButtonRoot = hasBrowserInteraction(entry) && !hasInlineActions && !disableMobileCombatEntryFocus;
                    var tagName = useButtonRoot ? "button" : "article";
                    var extraAttrs = useButtonRoot ? " type='button'" : "";
                    if (useButtonRoot) {
                        rowClass += " brave-view__entry--button";
                    }
                    var entryMarkup = (
                        "<" + tagName + " class='" + rowClass + "'"
                        + extraAttrs
                        + combatStateAttr
                        + combatRefAttr
                        + commandAttrs(entry, useButtonRoot)
                        + ">"
                        + (backgroundIcon ? icon(backgroundIcon, "brave-view__entry-ornament") : "")
                        + "<div class='brave-view__entry-head'>"
                        + lead
                        + "<div class='brave-view__entry-heading'>"
                        + "<div class='brave-view__entry-title'>" + escapeHtml(entry && entry.title ? entry.title : "") + "</div>"
                        + (entry && entry.meta ? "<div class='brave-view__entry-meta'>" + escapeHtml(entry.meta) + "</div>" : "")
                        + "</div>"
                        + "</div>"
                        + renderMeters(entry && entry.meters)
                        + renderThemePreview(entry && entry.preview)
                        + (entry && Array.isArray(entry.chips) && entry.chips.length
                            ? "<div class='brave-view__entry-chips'>" + entry.chips.map(renderChip).join("") + "</div>"
                            : "")
                        + renderEntryBodyLines(entry)
                        + renderInlineActions(entry && entry.actions)
                        + "</" + tagName + ">"
                    );
                    if (!(entry && Array.isArray(entry.sidecars) && entry.sidecars.length)) {
                        return entryMarkup;
                    }
                    return (
                        "<div class='brave-view__entry-cluster' data-combat-cluster-ref='" + escapeHtml(entry.cluster_ref || entry.entry_ref || "") + "'>"
                        + entryMarkup
                        + "<div class='brave-view__entry-sidecars'>"
                        + entry.sidecars.map(renderEntrySidecar).join("")
                        + "</div>"
                        + "</div>"
                    );
                }).join("")
                + "</div>"
            );
        };

        var renderSection = function (section) {
            if (!section || typeof section !== "object") {
                return "";
            }

            var body = "";
            var kind = section.kind || "lines";
            if (kind === "pairs") {
                body = renderPairs(section.items || []);
            } else if (kind === "entries") {
                body = renderEntries(section.items || []);
            } else if (kind === "list") {
                body = renderList(section.items || []);
            } else if (kind === "actions") {
                body = renderActions(section.items || []);
            } else if (kind === "form") {
                body = renderForm(section);
            } else if (kind === "arcade") {
                body = renderArcadeSurface(section);
            } else if (kind === "navpad") {
                body = renderNavPad(section);
            } else if (kind === "pre") {
                body = renderPre(section);
            } else if (kind === "activitylog") {
                body = "<div class='brave-room-log'><div class='brave-room-log__body' role='log' aria-live='polite' aria-relevant='additions text'></div></div>";
            } else {
                body = renderLines(section);
            }

            var sectionClass =
                "brave-view__section brave-view__section--" + escapeHtml(kind)
                + (section && section.span ? " brave-view__section--" + escapeHtml(section.span) : "")
                + (section && section.variant ? " brave-view__section--" + escapeHtml(section.variant) : "");

            return (
                "<section class='" + sectionClass + "'>"
                + (!(section && section.hide_label)
                    ? "<div class='brave-view__section-label'>"
                        + icon(section.icon || "label", "brave-view__section-icon")
                        + "<span>" + escapeHtml(section.label || "") + "</span>"
                        + "</div>"
                    : "")
                + body
                + "</section>"
            );
        };

        var renderActions = function (items) {
            return (
                "<div class='brave-view__actions'>"
                + (items || []).map(function (entry) {
                    var toneClass = entry && entry.tone ? " brave-view__action--" + escapeHtml(entry.tone) : "";
                    var iconOnlyClass = entry && entry.icon_only ? " brave-view__action--icon-only" : "";
                    var noIcon = !!(entry && entry.no_icon);
                    var aria = entry && (entry.aria_label || entry.label)
                        ? " aria-label='" + escapeHtml(entry.aria_label || entry.label) + "'"
                        : "";
                    return (
                        "<button type='button' class='brave-view__action brave-click" + toneClass + iconOnlyClass + "'"
                        + commandAttrs(entry, false)
                        + aria
                        + ">"
                        + (noIcon ? "" : icon(entry && entry.icon ? entry.icon : "chevron_right", "brave-view__action-icon"))
                        + (entry && entry.icon_only ? "" : "<span>" + escapeHtml(entry && entry.text ? entry.text : entry && entry.label ? entry.label : "") + "</span>")
                        + "</button>"
                    );
                }).join("")
                + "</div>"
            );
        };

        var renderBackAction = function (entry) {
            if (!entry) {
                return "";
            }
            var toneClass = entry && entry.tone ? " brave-view__action--" + escapeHtml(entry.tone) : "";
            var aria = entry && (entry.aria_label || entry.label)
                ? " aria-label='" + escapeHtml(entry.aria_label || entry.label) + "'"
                : "";
            return (
                "<button type='button' class='brave-view__action brave-view__back brave-click" + toneClass + "'"
                + commandAttrs(entry, false)
                + aria
                + ">"
                + icon(entry && entry.icon ? entry.icon : "arrow_back", "brave-view__action-icon brave-view__action-icon--back")
                + "<span>" + escapeHtml(entry && entry.text ? entry.text : entry && entry.label ? entry.label : "Back") + "</span>"
                + "</button>"
            );
        };

        var renderDesktopMenuAction = function () {
            if (isMobileViewport() || !isRoomLikeView(viewData)) {
                return "";
            }
            return (
                "<button type='button' class='brave-view__menu-button brave-click'"
                + " data-brave-picker='" + escapeHtml(JSON.stringify(buildDesktopMenuPicker())) + "'"
                + " aria-label='Open menu'"
                + " title='menu'>"
                + "<span>MENU</span>"
                + "</button>"
            );
        };

        var renderRoomMicromap = function () {
            if (!isRoomLikeView(viewData)) {
                return "";
            }
            var mapMarkup = viewData.micromap ? renderRoomCardMicromap(viewData.micromap) : "";
            return (
                "<div class='brave-view__micromap brave-click' data-brave-command='map' title='Open map' role='button' tabindex='0' aria-label='Open map'>"
                + mapMarkup
                + "</div>"
            );
        };

        var heroSceneMarkup =
            (((viewData.eyebrow_icon || viewData.eyebrow) || (!isMobileViewport() && isRoomLikeView(viewData)))
                ? "<div class='brave-view__hero-topbar'>"
                    + ((viewData.eyebrow_icon || viewData.eyebrow)
                        ? "<div class='brave-view__eyebrow"
                            + (shouldAnimateRegionSceneCard ? " brave-view__eyebrow--region-change" : "")
                            + (shouldAnimateFirstRegionDiscoverySceneCard ? " brave-view__eyebrow--first-region-discovery" : "")
                            + "'>"
                            + (viewData.eyebrow_icon ? icon(viewData.eyebrow_icon, "brave-view__eyebrow-icon") : "")
                            + (viewData.eyebrow ? "<span>" + escapeHtml(viewData.eyebrow) + "</span>" : "")
                            + "</div>"
                        : "")
                    + renderDesktopMenuAction()
                    + "</div>"
                : "")
            + renderRoomMicromap()
            + ((viewData.title_icon || viewData.title || viewData.back_action)
                ? "<div class='brave-view__titlebar'>"
                    + ((viewData.title_icon || viewData.title)
                        ? "<div class='brave-view__title'>"
                            + (viewData.title_icon ? icon(viewData.title_icon, "brave-view__title-icon") : "")
                            + (viewData.title ? "<span>" + escapeHtml(viewData.title) + "</span>" : "")
                            + "</div>"
                        : "")
                    + renderBackAction(viewData.back_action)
                    + "</div>"
                : "")
            + (viewData.subtitle ? "<div class='brave-view__subtitle'>" + escapeHtml(viewData.subtitle) + "</div>" : "");

        var viewMarkup =
            "<div class='brave-view" + variantClass + toneClass + "'>"
            + "<div class='brave-view__hero'>"
            + (viewData.wordmark ? "<div class='brave-view__wordmark' aria-label='" + escapeHtml(viewData.wordmark) + "'><span class='brave-view__wordmark-text'>" + escapeHtml(viewData.wordmark) + "</span></div>" : "")
            + (isRoomLikeView(viewData)
                ? "<div class='brave-view__room-scene-card"
                    + (shouldApplyRoomSceneEnterClass ? " brave-view__room-scene-card--enter" : "")
                    + (shouldAnimateRegionSceneCard ? " brave-view__room-scene-card--region-change" : "")
                    + (shouldAnimateFirstRegionDiscoverySceneCard ? " brave-view__room-scene-card--first-region-discovery" : "")
                    + "' data-brave-room-id='" + escapeHtml((nextRoomSceneMeta && nextRoomSceneMeta.roomId) || "") + "' data-brave-region='" + escapeHtml((nextRoomSceneMeta && nextRoomSceneMeta.regionName) || "") + "'>" + heroSceneMarkup + "</div>"
                : heroSceneMarkup)
            + renderMobileRoomUtility()
            + (Array.isArray(viewData.chips) && viewData.chips.length
                ? "<div class='brave-view__chips'>" + viewData.chips.map(renderChip).join("") + "</div>"
                : "")
            + (Array.isArray(viewData.actions) && viewData.actions.length
                ? renderActions(viewData.actions)
                : "")
            + "</div>"
            + "<div class='brave-view__sections'>"
            + (Array.isArray(viewData.sections)
                ? viewData.sections.map(renderSection).join("")
                : "")
            + "</div>"
            + "</div>";

        if (
            pendingCombatSwapTimeout
            && stickyView
            && viewData.variant === "combat"
            && currentViewData
            && currentViewData.variant === "combat"
        ) {
            deferCombatViewRender(viewData);
            return;
        }
        if (pendingCombatSwapTimeout) {
            window.clearTimeout(pendingCombatSwapTimeout);
            pendingCombatSwapTimeout = null;
        }

        if (
            stickyView
            && viewData.variant === "combat"
            && (!currentViewData || currentViewData.variant !== "combat")
        ) {
            clearTextOutput({ preserveCombatTransition: !!options.skipCombatTransition });
        }

        if (stickyView) {
            var previousCombatSnapshots = [];
            var nextCombatRefs = {};
            var shouldDelayCombatSwap = false;
            var patchCombatInPlace = !!(viewData.variant === "combat" && currentViewData && currentViewData.variant === "combat");
            if (viewData.variant === "combat" && currentViewData && currentViewData.variant === "combat") {
                previousCombatSnapshots = getCombatEntryNodes().map(captureCombatEntrySnapshot).filter(Boolean);
                nextCombatRefs = collectCombatEntryRefsFromMarkup(viewMarkup);
                shouldDelayCombatSwap = previousCombatSnapshots.some(function (snapshot) {
                    return snapshot && snapshot.ref && !nextCombatRefs[snapshot.ref];
                });
            }
            if (!preserveRail) {
                clearSceneRail();
            }
            setMainViewMode(!preserveRail);
            setStickyViewMode(true);
            suppressNextLookText = false;

            var applyStickyMarkup = function () {
                currentViewData = viewData;
                if (isRoomLikeView(viewData)) {
                    currentRoomViewData = viewData;
                }
                setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

                var stickyContainer = mwin.children(".brave-sticky-view");
                var preservedCombatLog = null;
                if (viewData.variant === "combat" && stickyContainer.length) {
                    preservedCombatLog = stickyContainer.find(".brave-combat-log").first().detach();
                }
                if (
                    stickyContainer.length
                    && patchCombatInPlace
                    && patchCombatStickyView(stickyContainer.get(0), viewMarkup)
                ) {
                    // patched in place
                } else if (stickyContainer.length) {
                    stickyContainer.html(viewMarkup);
                } else {
                    mwin.prepend("<div class='brave-sticky-view'>" + viewMarkup + "</div>");
                }
                if (preservedCombatLog && preservedCombatLog.length && viewData.variant === "combat") {
                    var combatSections = mwin.children(".brave-sticky-view").find(".brave-view--combat .brave-view__sections").first();
                    if (combatSections.length && !combatSections.children(".brave-combat-log").length) {
                        combatSections.append(preservedCombatLog);
                    }
                }
                if (viewData.variant === "combat" && previousCombatSnapshots.length) {
                    restoreCombatAtbContinuity(previousCombatSnapshots);
                }
                if (viewData.micromap || currentMapGrid || currentMapText) {
                    renderMap(viewData.micromap || (currentMapGrid ? { map_text: currentMapText, map_tiles: currentMapGrid } : currentMapText));
                }
                if (viewData.variant === "combat") {
                    ensureCombatLog();
                    claimCombatLogEntries();
                }
                if (isRoomLikeView(viewData)) {
                    ensureRoomActivityLog();
                    renderVicinityPanel(viewData);
                    if (currentRoomSceneData) {
                        renderSceneCard(currentRoomSceneData);
                    }
                } else {
                    clearVicinityPanel();
                }
                renderPackPanel();
                if (viewData.variant === "combat" && pendingCombatPanelData) {
                    renderPanelCard(pendingCombatPanelData);
                    pendingCombatPanelData = null;
                }
                renderDesktopToolbar();
                syncMobileShell();
                if (viewData.variant === "combat") {
                    applySuppressedCombatEntries();
                } else {
                    clearSuppressedCombatEntryRefs();
                }
                syncAnimatedAtbMeters();
                scheduleCombatFxFlush(0);
                syncOpenCombatPickerFromDom();
                combatViewTransitionActive = false;
                pendingCombatResultReturnTransition = viewData.variant === "combat-result";
                if (shouldAnimateRoomSceneCard) {
                    triggerRoomSceneCardTransition();
                }
                if (isRoomLikeView(viewData)) {
                    rememberRenderedRoomSceneMeta(getRenderedRoomSceneMeta() || nextRoomSceneMeta);
                }
            };

            if (shouldDelayCombatSwap) {
                previousCombatSnapshots.forEach(function (snapshot) {
                    var ref = snapshot && snapshot.ref;
                    if (!ref || nextCombatRefs[ref] || suppressedCombatEntryRefs[ref]) {
                        return;
                    }
                    if (snapshot) {
                        animateCombatDefeat(snapshot);
                    }
                });
                pendingCombatSwapTimeout = window.setTimeout(function () {
                    pendingCombatSwapTimeout = null;
                    applyStickyMarkup();
                    flushDeferredCombatViewRender(false);
                }, 920);
            } else {
                applyStickyMarkup();
            }
            focusViewAutofocusField();
            return;
        }

        var applyStandardMarkup = function () {
            var preservedScroll = isSameRoomReactiveRefresh
                ? (pendingMainScrollRestore || captureMainScrollPositions())
                : null;
            pendingMainScrollRestore = null;
            if (!isSameRoomReactiveRefresh) {
                blurActiveUiControl();
                clearTextOutput({
                    preserveCombatTransition: !!options.skipCombatTransition,
                    preservePicker: preservePickerOnRefresh,
                    preserveMobileSheet: preserveMobileSheetOnRefresh
                });
            }
            if (!preserveRail) {
                clearSceneRail();
            }
            setMainViewMode(!preserveRail);
            setStickyViewMode(false);
            suppressNextLookText = !!(viewData.variant === "room" || viewData.layout === "explore");
            currentViewData = viewData;
            if (isRoomLikeView(viewData)) {
                currentRoomViewData = viewData;
            }
            setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

            var patchedRoomInPlace = false;
            if (isSameRoomReactiveRefresh) {
                var currentRoomNode = mwin.children(".brave-view--room").first();
                if (currentRoomNode.length) {
                    patchedRoomInPlace = patchRoomViewInPlace(currentRoomNode.get(0), viewMarkup);
                }
            }
            if (!patchedRoomInPlace) {
                mwin.html(viewMarkup);
            }
            if (!braveGameLoaded && isRoomLikeView(viewData)) {
                braveGameLoaded = true;
                window.setTimeout(finishGameIntroVeil, 400);
            }
            if (isRoomLikeView(viewData)) {
                ensureRoomActivityLog();
                claimRoomActivityEntries();
                renderVicinityPanel(viewData);
                if (currentRoomSceneData) {
                    renderSceneCard(currentRoomSceneData);
                }
            } else {
                clearVicinityPanel();
            }
            if (viewData.micromap || currentMapGrid || currentMapText) {
                renderMap(viewData.micromap || (currentMapGrid ? { map_text: currentMapText, map_tiles: currentMapGrid } : currentMapText));
            }
            renderPackPanel();
            renderDesktopToolbar();
            syncMobileShell();
            if (viewData.variant === "combat") {
                applySuppressedCombatEntries();
            } else {
                clearSuppressedCombatEntryRefs();
            }
            syncAnimatedAtbMeters();
            scheduleCombatFxFlush(0);
            syncOpenCombatPickerFromDom();
            combatViewTransitionActive = false;
            pendingCombatResultReturnTransition = viewData.variant === "combat-result";
            if (shouldAnimateRoomSceneCard) {
                triggerRoomSceneCardTransition();
            }
            if (isRoomLikeView(viewData)) {
                rememberRenderedRoomSceneMeta(getRenderedRoomSceneMeta() || nextRoomSceneMeta);
            }
            if (isSameRoomReactiveRefresh) {
                restoreMainScrollPositions(preservedScroll);
            } else {
                focusViewAutofocusField();
                resetAllScrollPositions();
            }
            if (!options.skipCombatTransition && leavingCombatResult) {
                startCombatReturnOverlay(viewData);
            }
        };

        applyStandardMarkup();
    };

    var clearMobileNavDock = function (options) {
        options = options || {};
        var dock = document.getElementById("mobile-nav-dock");
        if (dock) {
            dock.innerHTML = "";
        }
        if (document.body) {
            document.body.style.removeProperty("--brave-mobile-dock-clearance");
        }
        document.body.classList.remove("brave-mobile-nav-active");
        document.body.classList.remove("brave-mobile-command-dock-active");
        if (!options.preserveMobileSheet) {
            clearMobileUtilitySheet();
        }
    };

    var updateMobileDockClearance = function () {
        var body = document.body;
        var dock = document.getElementById("mobile-nav-dock");
        if (!body || !dock || !dock.innerHTML.trim()) {
            if (body) {
                body.style.removeProperty("--brave-mobile-dock-clearance");
            }
            return;
        }
        var dockHeight = Math.ceil(dock.getBoundingClientRect().height || 0);
        if (!dockHeight) {
            body.style.removeProperty("--brave-mobile-dock-clearance");
            return;
        }
        body.style.setProperty("--brave-mobile-dock-clearance", (dockHeight + 20) + "px");
    };

    var renderMobileSceneUtility = function () {
        var host = document.querySelector(".brave-view__mobile-utility-host");
        if (!host) {
            return;
        }
        host.innerHTML = buildMobileRoomUtilityMarkup();
    };

    var renderMobileNavDock = function () {
        var dock = document.getElementById("mobile-nav-dock");
        if (!dock) {
            return;
        }
        if (!isMobileViewport()) {
            clearMobileNavDock();
            return;
        }

        if (combatViewTransitionActive || (currentViewData && currentViewData.variant === "combat")) {
            dock.innerHTML = "";
            document.body.classList.remove("brave-mobile-nav-active");
            document.body.classList.remove("brave-mobile-command-dock-active");
            clearMobileUtilitySheet();
            return;
        }

        var roomView = getCurrentRoomView();
        var navSection = findSectionByKind(roomView, "navpad");
        if (!roomView) {
            dock.innerHTML = "";
            document.body.classList.remove("brave-mobile-nav-active");
            document.body.classList.remove("brave-mobile-command-dock-active");
            clearMobileUtilitySheet();
            renderMobileUtilitySheet();
            return;
        }

        document.body.classList.remove("brave-mobile-command-dock-active");

        dock.innerHTML =
            "<div class='brave-mobile-nav-dock__inner'>"
            + buildMobileDockToolsMarkup()
            + (navSection ? renderMobileNavPad(navSection) : "")
            + "</div>";
        document.body.classList.add("brave-mobile-nav-active");
        updateMobileDockClearance();
    };

    var syncCombatActionTray = function () {
        var combatView = document.querySelector(".brave-view--combat");
        if (!combatView || !isMobileViewport()) {
            return;
        }

        var sectionsHost = combatView.querySelector(".brave-view__sections");
        var abilitiesSection = combatView.querySelector(".brave-view__section--abilities");
        var itemsSection = combatView.querySelector(".brave-view__section--items");
        if (!sectionsHost || !abilitiesSection || !itemsSection) {
            return;
        }

        var tabs = combatView.querySelector(".brave-combat-tray-tabs");
        if (!tabs) {
            tabs = document.createElement("div");
            tabs.className = "brave-combat-tray-tabs";
            tabs.setAttribute("role", "tablist");
            tabs.innerHTML =
                "<button type='button' class='brave-combat-tray-tabs__tab' data-brave-combat-tab='abilities' role='tab'><span class='brave-combat-tray-tabs__label'>Skills</span><span class='brave-combat-tray-tabs__count' data-brave-combat-tab-count='abilities'>0</span></button>"
                + "<button type='button' class='brave-combat-tray-tabs__tab' data-brave-combat-tab='items' role='tab'><span class='brave-combat-tray-tabs__label'>Kit</span><span class='brave-combat-tray-tabs__count' data-brave-combat-tab-count='items'>0</span></button>";
            sectionsHost.insertBefore(tabs, abilitiesSection);
        }

        var abilityCount = abilitiesSection.querySelectorAll(".brave-view__list-item").length;
        var itemCount = itemsSection.querySelectorAll(".brave-view__list-item").length;
        var preferredTab = currentCombatActionTab;
        if (!abilityCount && itemCount) {
            preferredTab = "items";
        } else if (!itemCount && abilityCount) {
            preferredTab = "abilities";
        }
        currentCombatActionTab = preferredTab;
        combatView.setAttribute("data-brave-combat-tab", preferredTab);

        Array.prototype.forEach.call(tabs.querySelectorAll("[data-brave-combat-tab]"), function (button) {
            var tab = button.getAttribute("data-brave-combat-tab");
            var active = tab === preferredTab;
            var countNode = button.querySelector("[data-brave-combat-tab-count]");
            var count = tab === "abilities" ? abilityCount : itemCount;
            button.classList.toggle("brave-combat-tray-tabs__tab--active", active);
            button.setAttribute("aria-selected", active ? "true" : "false");
            button.setAttribute("tabindex", active ? "0" : "-1");
            if (countNode) {
                countNode.textContent = String(count);
            }
            if (tab === "abilities") {
                button.classList.toggle("brave-combat-tray-tabs__tab--empty", !abilityCount);
                button.disabled = !abilityCount;
            }
            if (tab === "items") {
                button.classList.toggle("brave-combat-tray-tabs__tab--empty", !itemCount);
                button.disabled = !itemCount;
            }
        });
    };

    var syncMobileShell = function () {
        renderMobileSceneUtility();
        renderMobileNavDock();
        renderMobileUtilitySheet();
        syncCombatActionTray();
    };

    var sendBrowserCommand = function (command, confirmText) {
        if (!command || !plugin_handler || !plugin_handler.onSend) {
            return;
        }
        var normalizedCommand = String(command || "").trim().toLowerCase();
        var braveAudio = getBraveAudio();
        if (confirmText && !window.confirm(confirmText)) {
            return;
        }
        blurActiveUiControl();
        suppressMobileNonInputFocus(1200);
        if (isRoomNavigationCommand(normalizedCommand)) {
            suppressMobileRoomNavScroll(900);
            resetAllScrollPositions();
        }
        if (normalizedCommand.indexOf("play ") === 0 || normalizedCommand === "finish play") {
            startGameIntroVeil();
        }
        clearPickerSheet();
        clearBrowserNotice();
        if (isMobileViewport()) {
            if (currentMobileUtilityTab) {
                currentMobileUtilityTab = null;
                renderMobileUtilitySheet();
                renderMobileNavDock();
            }
            closeMobileCommandTray();
        }
        if (
            isPreservedSystemViewActive()
            && (
                normalizedCommand === "look"
                || (
                    currentViewData
                    && currentViewData.back_action
                    && currentViewData.back_action.command
                    && normalizedCommand === String(currentViewData.back_action.command).trim().toLowerCase()
                )
            )
        ) {
            allowNextRoomRefreshNavigationUntil = Date.now() + 1500;
        }
        if (braveAudio && typeof braveAudio.handleUiAction === "function") {
            braveAudio.handleUiAction("click");
        }
        plugin_handler.onSend(command);
    };

    var clearActivityOverlay = function (options) {
        options = options || {};
        var root = document.getElementById("brave-activity-overlay");
        var shouldRestoreArcadeRoom = !!(
            root
            && root.classList
            && root.classList.contains("brave-activity-overlay--arcade-result")
            && !options.suppressArcadeRestore
        );
        if (root && root.parentNode) {
            root.parentNode.removeChild(root);
        }
        if (document.body) {
            document.body.classList.remove("brave-activity-active");
        }
        if (shouldRestoreArcadeRoom) {
            restoreArcadeRoomView();
        }
    };

    var stripActivityMarkup = function (value) {
        return String(value == null ? "" : value).replace(/\|\|/g, "|").replace(/\|[A-Za-z]/g, "");
    };

    var compactActivityLines = function (lines) {
        return (Array.isArray(lines) ? lines : []).filter(function (line) {
            return line !== undefined && line !== null && String(line).trim();
        }).map(function (line) {
            return String(line);
        });
    };

    var buildActivityStats = function (stats) {
        stats = Array.isArray(stats) ? stats : [];
        if (!stats.length) {
            return "";
        }
        return "<div class='brave-activity-overlay__stats'>"
            + stats.map(function (stat) {
                return "<div class='brave-activity-overlay__stat'>"
                    + "<span>" + escapeHtml(stat.label || "") + "</span>"
                    + "<strong>" + escapeHtml(stat.value == null ? "" : stat.value) + "</strong>"
                    + "</div>";
            }).join("")
            + "</div>";
    };

    var buildActivityCard = function (entry) {
        entry = entry || {};
        var lines = compactActivityLines(entry.lines);
        var toneClass = entry.tone ? " brave-activity-card--" + escapeHtml(entry.tone) : "";
        var disabled = !!entry.disabled || !entry.command;
        var actionLabel = entry.action_label || "";
        var actionIcon = entry.action_icon || "chevron_right";
        var badge = entry.badge || entry.status || "";
        var badgeToneClass = entry.badge_tone ? " brave-activity-card__badge--" + escapeHtml(entry.badge_tone) : "";
        var action = actionLabel
            ? "<button type='button' class='brave-activity-card__action' data-brave-activity-command='" + escapeHtml(entry.command || "") + "'"
                + (entry.confirm ? " data-brave-activity-confirm='" + escapeHtml(entry.confirm) + "'" : "")
                + (disabled ? " disabled" : "")
                + ">"
                + icon(actionIcon, "brave-activity-card__action-icon")
                + "<span>" + escapeHtml(actionLabel) + "</span>"
                + "</button>"
            : "";
        return "<article class='brave-activity-card" + toneClass + "'>"
            + "<div class='brave-activity-card__head'>"
            + "<div class='brave-activity-card__title'>" + escapeHtml(entry.title || entry.name || "") + "</div>"
            + (badge ? "<div class='brave-activity-card__badge" + badgeToneClass + "'>" + escapeHtml(badge) + "</div>" : "")
            + "</div>"
            + (entry.result ? "<div class='brave-activity-card__result'>" + escapeHtml(entry.result) + "</div>" : "")
            + (entry.summary ? "<div class='brave-activity-card__summary'>" + escapeHtml(entry.summary) + "</div>" : "")
            + (lines.length ? "<div class='brave-activity-card__lines'>"
                + lines.map(function (line) {
                    return "<div class='brave-activity-card__line'>" + escapeHtml(line) + "</div>";
                }).join("")
                + "</div>" : "")
            + (action ? "<div class='brave-activity-card__actions'>" + action + "</div>" : "")
            + "</article>";
    };

    var buildActivitySection = function (section) {
        section = section || {};
        var items = Array.isArray(section.items) ? section.items : [];
        return "<section class='brave-activity-overlay__section'>"
            + "<div class='brave-activity-overlay__section-head'>"
            + "<span>" + escapeHtml(section.label || "") + "</span>"
            + "<strong>" + escapeHtml(String(items.length)) + "</strong>"
            + "</div>"
            + (items.length
                ? "<div class='brave-activity-overlay__cards'>" + items.map(buildActivityCard).join("") + "</div>"
                : "<div class='brave-activity-overlay__empty'>" + escapeHtml(section.empty || "Nothing to show.") + "</div>")
            + "</section>";
    };

    var buildActivityBodyCopy = function (lines) {
        lines = compactActivityLines(lines);
        if (!lines.length) {
            return "";
        }
        return "<div class='brave-activity-overlay__bodycopy'>"
            + lines.map(function (line) {
                return "<div class='brave-activity-overlay__bodyline'>" + escapeHtml(line) + "</div>";
            }).join("")
            + "</div>";
    };

    var normalizeArcadeResultNotes = function (notes, fallbackLines) {
        var normalized = [];
        if (Array.isArray(notes)) {
            notes.forEach(function (note) {
                if (note === undefined || note === null) {
                    return;
                }
                if (typeof note === "string") {
                    if (note.trim()) {
                        normalized.push({ tone: "muted", text: note });
                    }
                    return;
                }
                var text = String(note.text == null ? "" : note.text).trim();
                if (!text) {
                    return;
                }
                normalized.push({
                    tone: note.tone || "muted",
                    text: text,
                });
            });
        }
        if (normalized.length) {
            return normalized;
        }
        return compactActivityLines(fallbackLines).map(function (line) {
            return { tone: "muted", text: String(line) };
        });
    };

    var buildArcadeResultSummary = function (stats) {
        stats = Array.isArray(stats) ? stats : [];
        if (!stats.length) {
            return "";
        }
        return "<div class='brave-arcade-result__summary'>"
            + stats.map(function (stat) {
                var accentClass = stat && stat.accent ? " brave-arcade-result__summary-card--" + escapeHtml(stat.accent) : "";
                return "<div class='brave-arcade-result__summary-card" + accentClass + "'>"
                    + "<span>" + escapeHtml(stat.label || "") + "</span>"
                    + "<strong>" + escapeHtml(stat.value == null ? "" : String(stat.value)) + "</strong>"
                    + "</div>";
            }).join("")
            + "</div>";
    };

    var buildArcadeResultRow = function (row, options) {
        row = row || {};
        options = options || {};
        var classes = ["brave-arcade-result__row"];
        if (row.is_current) {
            classes.push("brave-arcade-result__row--current");
        }
        if (row.is_top) {
            classes.push("brave-arcade-result__row--top");
        }
        if (row.placeholder) {
            classes.push("brave-arcade-result__row--empty");
        }
        if (options.standing) {
            classes.push("brave-arcade-result__row--standing");
        }
        return "<div class='" + classes.join(" ") + "'>"
            + "<span class='brave-arcade-result__rank'>" + escapeHtml("#" + String(row.rank || "")) + "</span>"
            + "<span class='brave-arcade-result__name'>"
                + "<span class='brave-arcade-result__name-text'>" + escapeHtml(row.placeholder ? "---" : (row.name || "Unknown")) + "</span>"
                + (row.is_current ? "<span class='brave-arcade-result__tag'>YOU</span>" : "")
            + "</span>"
            + "<span class='brave-arcade-result__score'>" + escapeHtml(row.placeholder ? "0" : (row.score || "0")) + "</span>"
            + "</div>";
    };

    var buildArcadeResultBoard = function (payload, leaderboard, playerRow) {
        leaderboard = Array.isArray(leaderboard) ? leaderboard : [];
        var limit = Math.max(1, parseInt(payload.limit, 10) || leaderboard.length || 5);
        var rowsByRank = {};
        leaderboard.forEach(function (row) {
            var rank = parseInt(row && row.rank, 10);
            if (rank > 0 && !rowsByRank[rank]) {
                rowsByRank[rank] = row;
            }
        });
        var rows = [];
        for (var rank = 1; rank <= limit; rank += 1) {
            rows.push(rowsByRank[rank] || {
                rank: rank,
                placeholder: true,
                score: "0",
            });
        }
        return "<section class='brave-arcade-result__board'>"
            + "<div class='brave-arcade-result__board-head'>"
            + "<span class='brave-arcade-result__board-icon'>" + icon("leaderboard") + "</span>"
            + "<div class='brave-arcade-result__board-title'>" + escapeHtml(payload.leaderboard_title || "Local Leaderboard") + "</div>"
            + "</div>"
            + "<div class='brave-arcade-result__table-head'>"
            + "<span>Rank</span>"
            + "<span>Character</span>"
            + "<span>Score</span>"
            + "</div>"
            + "<div class='brave-arcade-result__table'>"
            + rows.map(function (row) {
                return buildArcadeResultRow(row);
            }).join("")
            + "</div>"
            + (
                playerRow && parseInt(playerRow.rank, 10) > limit
                    ? "<div class='brave-arcade-result__standing'>"
                        + "<div class='brave-arcade-result__standing-label'>Your Standing</div>"
                        + buildArcadeResultRow(playerRow, { standing: true })
                        + "</div>"
                    : ""
            )
            + "</section>";
    };

    var buildArcadeResultNotes = function (notes) {
        notes = Array.isArray(notes) ? notes : [];
        if (!notes.length) {
            return "";
        }
        return "<div class='brave-arcade-result__notes'>"
            + notes.map(function (note) {
                var toneClass = note && note.tone ? " brave-arcade-result__note--" + escapeHtml(note.tone) : "";
                return "<div class='brave-arcade-result__note" + toneClass + "'>" + escapeHtml(note.text || "") + "</div>";
            }).join("")
            + "</div>";
    };

    var bindActivityOverlayControls = function (root) {
        root.addEventListener("click", function (event) {
            var closeTarget = event.target.closest("[data-brave-activity-close]");
            if (closeTarget) {
                event.preventDefault();
                event.stopPropagation();
                clearActivityOverlay();
                return;
            }
            var commandTarget = event.target.closest("[data-brave-activity-command]");
            if (commandTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (!commandTarget.disabled) {
                    sendBrowserCommand(
                        commandTarget.getAttribute("data-brave-activity-command"),
                        commandTarget.getAttribute("data-brave-activity-confirm")
                    );
                }
            }
        }, true);
    };

    var renderActivityOverlay = function (kind, payload, options) {
        payload = payload || {};
        options = options || {};
        clearActivityOverlay({ suppressArcadeRestore: true });
        if (typeof clearFishingMinigame === "function") {
            clearFishingMinigame();
        }
        var root = document.createElement("div");
        root.id = "brave-activity-overlay";
        root.className = "brave-activity-overlay brave-activity-overlay--" + String(kind || "default");
        root.setAttribute("aria-hidden", "false");
        var message = stripActivityMarkup(payload.message || "");
        var messageTone = payload.message_tone || "muted";
        var footerAction = options.footer_action || null;
        var bodyMarkup = buildActivityBodyCopy(options.body_lines)
            + (Array.isArray(options.sections) ? options.sections.map(buildActivitySection).join("") : "");
        root.innerHTML =
            "<div class='brave-activity-overlay__backdrop' data-brave-activity-close='1'></div>"
            + "<section class='brave-activity-overlay__panel' role='dialog' aria-modal='true' tabindex='0'>"
            + "<div class='brave-activity-overlay__head'>"
            + "<div class='brave-activity-overlay__titlebar'>"
            + "<span class='brave-activity-overlay__icon'>" + icon(options.icon || "widgets") + "</span>"
            + "<div class='brave-activity-overlay__titles'>"
            + "<div class='brave-activity-overlay__eyebrow'>" + escapeHtml(options.eyebrow || "") + "</div>"
            + "<div class='brave-activity-overlay__title'>" + escapeHtml(options.title || payload.title || "Activity") + "</div>"
            + "</div>"
            + "<button type='button' class='brave-activity-overlay__close brave-view__action brave-view__action--muted brave-view__back' data-brave-activity-close='1' aria-label='Close'>"
            + icon("close")
            + "</button>"
            + "</div>"
            + buildActivityStats(options.stats)
            + (message ? "<div class='brave-activity-overlay__message brave-activity-overlay__message--" + escapeHtml(messageTone) + "'>" + escapeHtml(message) + "</div>" : "")
            + "</div>"
            + "<div class='brave-activity-overlay__body'>"
            + bodyMarkup
            + "</div>"
            + (footerAction
                ? "<div class='brave-activity-overlay__footer'>"
                    + "<button type='button' class='brave-activity-overlay__footer-action' data-brave-activity-command='" + escapeHtml(footerAction.command || "") + "'"
                    + (footerAction.confirm ? " data-brave-activity-confirm='" + escapeHtml(footerAction.confirm) + "'" : "")
                    + (footerAction.disabled ? " disabled" : "")
                    + ">"
                    + icon(footerAction.icon || "restart_alt", "brave-activity-overlay__footer-icon")
                    + "<span>" + escapeHtml(footerAction.label || "Action") + "</span>"
                    + "</button>"
                    + "</div>"
                : "")
            + "</section>";
        document.body.appendChild(root);
        document.body.classList.add("brave-activity-active");
        bindActivityOverlayControls(root);
        var panel = root.querySelector(".brave-activity-overlay__panel");
        if (panel && typeof panel.focus === "function") {
            panel.focus();
        }
    };

    var renderArcadeResultOverlay = function (payload) {
        payload = payload || {};
        var summaryStats = Array.isArray(payload.summary_stats) && payload.summary_stats.length
            ? payload.summary_stats
            : (Array.isArray(payload.stats) ? payload.stats : []);
        var notes = normalizeArcadeResultNotes(payload.notes, payload.lines);
        clearActivityOverlay({ suppressArcadeRestore: true });
        if (typeof clearFishingMinigame === "function") {
            clearFishingMinigame();
        }
        var root = document.createElement("div");
        root.id = "brave-activity-overlay";
        root.className = "brave-activity-overlay brave-activity-overlay--arcade-result";
        root.setAttribute("aria-hidden", "false");
        root.innerHTML =
            "<div class='brave-activity-overlay__backdrop' data-brave-activity-close='1'></div>"
            + "<section class='brave-activity-overlay__panel' role='dialog' aria-modal='true' tabindex='0'>"
            + "<div class='brave-activity-overlay__head'>"
            + "<div class='brave-activity-overlay__titlebar'>"
            + "<span class='brave-activity-overlay__icon'>" + icon("sports_esports") + "</span>"
            + "<div class='brave-activity-overlay__titles'>"
            + "<div class='brave-activity-overlay__eyebrow'>" + escapeHtml(payload.cabinet || "Arcade Cabinet") + "</div>"
            + "<div class='brave-activity-overlay__title'>" + escapeHtml(payload.title || "Run Complete") + "</div>"
            + "</div>"
            + "<button type='button' class='brave-activity-overlay__close brave-view__action brave-view__action--muted brave-view__back' data-brave-activity-close='1' aria-label='Close'>"
            + icon("close")
            + "</button>"
            + "</div>"
            + "<div class='brave-arcade-result__headline'>"
            + "<span>" + escapeHtml(payload.headline || "RUN COMPLETE") + "</span>"
            + "</div>"
            + buildArcadeResultSummary(summaryStats)
            + "</div>"
            + "<div class='brave-activity-overlay__body brave-arcade-result__body'>"
            + buildArcadeResultBoard(payload, payload.leaderboard, payload.player_row)
            + buildArcadeResultNotes(notes)
            + "</div>"
            + "</section>";
        document.body.appendChild(root);
        document.body.classList.add("brave-activity-active");
        bindActivityOverlayControls(root);
        var panel = root.querySelector(".brave-activity-overlay__panel");
        if (panel && typeof panel.focus === "function") {
            panel.focus();
        }
    };

    var restoreArcadeRoomView = function () {
        if (isRoomLikeView(currentRoomViewData)) {
            pendingArcadeRoomRestore = false;
            renderMainView(currentRoomViewData, {
                skipCombatTransition: true,
                skipRoomPreserve: true,
            });
            if (currentRoomSceneData !== null) {
                renderSceneCard(currentRoomSceneData);
            }
            return true;
        }
        pendingArcadeRoomRestore = true;
        return false;
    };

    var cookingRecipeCard = function (entry, label, iconName) {
        entry = entry || {};
        return {
            title: entry.name || "Recipe",
            badge: entry.ready ? "Ready" : (entry.known ? "Missing" : "Locked"),
            badge_tone: entry.ready ? "ready" : (entry.known ? "muted" : "locked"),
            result: entry.result_name ? "Makes " + entry.result_name : "",
            summary: entry.summary || entry.result_summary || "",
            lines: [
                entry.ingredient_text ? "Ingredients: " + entry.ingredient_text : "",
                entry.restore_text ? "Restores: " + entry.restore_text : "",
                entry.bonus_text ? "Meal: " + entry.bonus_text : ""
            ],
            command: entry.command || "",
            action_label: entry.command ? label : "",
            action_icon: iconName || "restaurant",
            tone: entry.ready ? "ready" : (entry.known ? "known" : "locked"),
        };
    };

    var cookingMealCard = function (entry) {
        entry = entry || {};
        return {
            title: (entry.name || "Meal") + (entry.quantity > 1 ? " x" + String(entry.quantity) : ""),
            badge: "In pack",
            badge_tone: "muted",
            summary: entry.summary || "",
            lines: [
                entry.restore_text ? "Restores: " + entry.restore_text : "",
                entry.bonus_text ? "Meal: " + entry.bonus_text : ""
            ],
            command: entry.command || "",
            action_label: entry.command ? "Eat" : "",
            action_icon: "local_dining",
            tone: "known",
        };
    };

    var renderCookingOverlay = function (payload) {
        payload = payload || {};
        renderActivityOverlay("cooking", payload, {
            icon: "restaurant",
            eyebrow: payload.spot || "Kitchen Hearth",
            title: "Cooking",
            stats: [
                { label: "Ready", value: String(payload.ready_count || 0) },
                { label: "Meals", value: String(payload.meal_count || 0) },
                { label: "Recipes", value: String(payload.total_count || 0) }
            ],
            sections: [
                {
                    label: "Ready Tonight",
                    items: (payload.ready || []).map(function (entry) {
                        return cookingRecipeCard(entry, "Cook", "skillet");
                    }),
                    empty: "Nothing is ready from your current pantry."
                },
                {
                    label: "Meals In Pack",
                    items: (payload.meals || []).map(cookingMealCard),
                    empty: "No prepared meals in your pack."
                },
                {
                    label: "Known Recipes",
                    items: (payload.known || []).map(function (entry) {
                        return cookingRecipeCard(entry, "", "restaurant");
                    }),
                    empty: "No other known recipes are close to ready."
                },
                {
                    label: "Locked Recipes",
                    items: (payload.locked || []).map(function (entry) {
                        return cookingRecipeCard(entry, "", "lock");
                    }),
                    empty: "No locked recipes right now."
                }
            ]
        });
    };

    var tinkeringRecipeCard = function (entry, label) {
        entry = entry || {};
        var components = Array.isArray(entry.components) ? entry.components : [];
        var parts = components.map(function (row) {
            return (row.name || row.template_id || "Part") + " " + String(row.owned || 0) + "/" + String(row.required || 0);
        }).join(", ");
        return {
            title: entry.name || "Design",
            badge: entry.ready ? "Ready" : (entry.known ? "Missing" : "Locked"),
            badge_tone: entry.ready ? "ready" : (entry.known ? "muted" : "locked"),
            result: entry.result_name ? "Builds " + entry.result_name + (entry.result_quantity > 1 ? " x" + String(entry.result_quantity) : "") : "",
            summary: entry.summary || entry.result_summary || "",
            lines: [
                entry.base_name ? "Base: " + entry.base_name + " " + String(entry.base_owned || 0) + "/1" : "",
                parts ? "Parts: " + parts : "",
                entry.silver_cost ? "Silver: " + String(entry.silver_have || 0) + "/" + String(entry.silver_cost) : "",
                entry.result_bonuses ? "Result: " + entry.result_bonuses : ""
            ],
            command: entry.command || "",
            confirm: entry.confirm || "",
            action_label: entry.command ? label : "",
            action_icon: "construction",
            tone: entry.ready ? "ready" : (entry.known ? "known" : "locked"),
        };
    };

    var renderTinkeringOverlay = function (payload) {
        payload = payload || {};
        renderActivityOverlay("tinkering", payload, {
            icon: "construction",
            eyebrow: "Workbench",
            title: "Tinkering",
            stats: [
                { label: "Silver", value: String(payload.silver || 0) },
                { label: "Ready", value: String(payload.ready_count || 0) },
                { label: "Designs", value: String(payload.total_count || 0) }
            ],
            sections: [
                {
                    label: "Ready Now",
                    items: (payload.ready || []).map(function (entry) {
                        return tinkeringRecipeCard(entry, "Build");
                    }),
                    empty: "Nothing is ready from your current pack."
                },
                {
                    label: "Known Designs",
                    items: (payload.known || []).map(function (entry) {
                        return tinkeringRecipeCard(entry, "");
                    }),
                    empty: "No other known designs are close to completion."
                },
                {
                    label: "Locked Designs",
                    items: (payload.locked || []).map(function (entry) {
                        return tinkeringRecipeCard(entry, "");
                    }),
                    empty: "No locked tinkering designs yet."
                }
            ]
        });
    };

    var masteryCard = function (entry) {
        entry = entry || {};
        return {
            title: entry.display_name || entry.name || "Technique",
            badge: entry.can_train ? "Ready" : (entry.rank_label || ""),
            badge_tone: entry.can_train ? "ready" : "muted",
            result: entry.role || "",
            summary: entry.summary || "",
            lines: [
                entry.current_bonus ? "Current: " + entry.current_bonus : "Current: Rank " + String(entry.rank || 1),
                entry.next_text || "",
                entry.next_bonus ? "Next: " + entry.next_bonus : "",
                entry.can_train ? "" : (entry.status || "")
            ],
            command: entry.command || "",
            confirm: entry.confirm || "",
            action_label: entry.command ? "Train" : "",
            action_icon: "workspace_premium",
            tone: entry.can_train ? "ready" : (entry.rank >= 3 ? "known" : "locked"),
        };
    };

    var renderMasteryOverlay = function (payload) {
        payload = payload || {};
        var respecCommand = payload.respec_command || "";
        renderActivityOverlay("mastery", payload, {
            icon: "workspace_premium",
            eyebrow: payload.in_mastery_room ? "Mastery Hall" : "Training Review",
            title: "Ability Mastery",
            stats: [
                { label: "Available", value: String(payload.available || 0) },
                { label: "Spent", value: String(payload.spent || 0) + "/" + String(payload.earned || 0) },
                { label: "Silver", value: String(payload.silver || 0) }
            ],
            sections: [
                {
                    label: "Techniques",
                    items: (payload.techniques || []).map(masteryCard),
                    empty: "No trainable combat techniques unlocked yet."
                }
            ],
            footer_action: respecCommand
                ? {
                    label: "Respec",
                    command: respecCommand,
                    confirm: "Reset all mastery for " + String(payload.respec_cost || 0) + " silver?",
                    disabled: !payload.can_respec,
                    icon: "restart_alt"
                }
                : null
        });
    };

    var clampFishingValue = function (value, min, max) {
        return Math.max(min, Math.min(max, value));
    };

    var clearFishingMinigame = function () {
        if (currentFishingAnimationFrame) {
            window.cancelAnimationFrame(currentFishingAnimationFrame);
            currentFishingAnimationFrame = null;
        }
        currentFishingGame = null;
        var root = document.getElementById("brave-fishing-minigame");
        if (root && root.parentNode) {
            root.parentNode.removeChild(root);
        }
        if (document.body) {
            document.body.classList.remove("brave-fishing-active");
        }
    };

    var getFishingRoot = function () {
        return document.getElementById("brave-fishing-minigame");
    };

    var getFishingNumber = function (value, fallback) {
        var parsed = parseFloat(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };

    var stripFishingMarkup = function (value) {
        return String(value == null ? "" : value).replace(/\|\|/g, "|").replace(/\|[A-Za-z]/g, "");
    };

    var buildFishingSetupOption = function (item, type) {
        item = item || {};
        var available = item.available !== false;
        var selected = !!item.selected;
        var command = type === "rod" ? "fish rod " : "fish lure ";
        command += item.key || item.name || "";
        var iconName = type === "rod" ? "straighten" : "tune";
        var meta = [];
        if (type === "rod") {
            meta.push("Power " + String(item.power || 0));
            meta.push("Stability " + String(item.stability || 0));
        } else {
            meta.push("Rarity +" + String(item.rarity_bonus || 0));
            if (item.zone_bonus) {
                meta.push("Water +" + String(item.zone_bonus));
            }
        }
        var favored = Array.isArray(item.favored) ? item.favored.join(", ") : "";
        var summary = available ? (item.summary || "") : (item.unlock_text || "Locked.");
        var classes = [
            "brave-fishing-minigame__gear-option",
            selected ? "brave-fishing-minigame__gear-option--selected" : "",
            available ? "" : "brave-fishing-minigame__gear-option--locked"
        ].join(" ");
        var disabled = selected || !available || !command.trim() ? " disabled" : "";
        var badge = selected ? "Selected" : (!available ? "Locked" : "");
        var badgeToneClass = selected ? " brave-fishing-minigame__gear-badge--selected" : (!available ? " brave-fishing-minigame__gear-badge--locked" : "");
        return ""
            + "<button type='button' class='" + classes + "' data-brave-fishing-command='" + escapeHtml(command) + "'" + disabled + ">"
            + "<span class='brave-fishing-minigame__gear-icon'>" + icon(iconName) + "</span>"
            + "<span class='brave-fishing-minigame__gear-copy'>"
            + "<span class='brave-fishing-minigame__gear-head'>"
            + "<span class='brave-fishing-minigame__gear-name'>" + escapeHtml(item.name || "Tackle") + "</span>"
            + (badge ? "<span class='brave-fishing-minigame__gear-badge" + badgeToneClass + "'>" + escapeHtml(badge) + "</span>" : "")
            + "</span>"
            + "<span class='brave-fishing-minigame__gear-meta'>" + escapeHtml(meta.join(" / ")) + "</span>"
            + (favored ? "<span class='brave-fishing-minigame__gear-meta'>" + escapeHtml("Favored: " + favored) + "</span>" : "")
            + (summary ? "<span class='brave-fishing-minigame__gear-summary'>" + escapeHtml(summary) + "</span>" : "")
            + "</span>"
            + "</button>";
    };

    var buildFishingSetupList = function (items, type) {
        items = Array.isArray(items) ? items : [];
        if (!items.length) {
            return "<div class='brave-fishing-minigame__empty'>No " + (type === "rod" ? "rods" : "lures") + " available.</div>";
        }
        return items.map(function (item) {
            return buildFishingSetupOption(item, type);
        }).join("");
    };

    var renderFishingSetupOverlay = function (payload) {
        if (typeof clearActivityOverlay === "function") {
            clearActivityOverlay({ suppressArcadeRestore: true });
        }
        clearFishingMinigame();
        var data = payload || {};
        var root = document.createElement("div");
        root.id = "brave-fishing-minigame";
        root.className = "brave-fishing-minigame brave-fishing-minigame--setup";
        root.setAttribute("aria-hidden", "false");
        root.setAttribute("data-fishing-phase", "setup");
        root.setAttribute("data-fishing-band", "neutral");
        var rod = data.rod || {};
        var lure = data.lure || {};
        var message = stripFishingMarkup(data.message || "");
        var canCast = data.can_cast !== false;
        root.innerHTML =
            "<div class='brave-fishing-minigame__backdrop'></div>"
            + "<section class='brave-fishing-minigame__panel brave-fishing-minigame__panel--setup' role='dialog' aria-modal='true' tabindex='0'>"
            + "<div class='brave-fishing-minigame__head'>"
            + "<div class='brave-fishing-minigame__titlebar'>"
            + "<span class='brave-fishing-minigame__icon'>" + icon("phishing") + "</span>"
            + "<div class='brave-fishing-minigame__titles'>"
            + "<div class='brave-fishing-minigame__eyebrow'>" + escapeHtml(data.spot || "Fishing Water") + "</div>"
            + "<div class='brave-fishing-minigame__title'>Fishing</div>"
            + "</div>"
            + "<button type='button' class='brave-fishing-minigame__close brave-view__action brave-view__action--muted brave-view__back' data-brave-fishing-close='1' aria-label='Close fishing'>" + icon("close") + "</button>"
            + "</div>"
            + "<div class='brave-fishing-minigame__loadout'>"
            + "<span>" + escapeHtml(rod.name || "Rod") + "</span>"
            + "<span>" + escapeHtml(lure.name || "Lure") + "</span>"
            + "</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__setup'>"
            + "<div class='brave-fishing-minigame__setup-summary'>"
            + "<div class='brave-fishing-minigame__setup-label'>Water</div>"
            + "<div class='brave-fishing-minigame__setup-title'>" + escapeHtml(data.spot || "Fishing Water") + "</div>"
            + "<div class='brave-fishing-minigame__setup-text'>" + escapeHtml(stripFishingMarkup(data.cast_text || "The water looks workable.")) + "</div>"
            + (message ? "<div class='brave-fishing-minigame__setup-message brave-fishing-minigame__setup-message--" + escapeHtml(data.message_tone || "muted") + "'>" + escapeHtml(message) + "</div>" : "")
            + "<div class='brave-fishing-minigame__active-tackle'>"
            + "<div><span>Rod</span><strong>" + escapeHtml(rod.name || "None") + "</strong></div>"
            + "<div><span>Lure</span><strong>" + escapeHtml(lure.name || "None") + "</strong></div>"
            + "</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__gear'>"
            + "<section class='brave-fishing-minigame__gear-column'>"
            + "<div class='brave-fishing-minigame__setup-label'>Rods</div>"
            + buildFishingSetupList(data.rods, "rod")
            + "</section>"
            + "<section class='brave-fishing-minigame__gear-column'>"
            + "<div class='brave-fishing-minigame__setup-label'>Lures</div>"
            + buildFishingSetupList(data.lures, "lure")
            + "</section>"
            + "</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__controls'>"
            + "<button type='button' class='brave-fishing-minigame__reel' data-brave-fishing-command='fish cast'" + (canCast ? "" : " disabled") + ">Cast Line</button>"
            + (data.can_borrow ? "<button type='button' class='brave-fishing-minigame__secondary' data-brave-fishing-command='fish borrow kit'>Borrow Kit</button>" : "<button type='button' class='brave-fishing-minigame__secondary' data-brave-fishing-close='1'>Close</button>")
            + "</div>"
            + "</section>";
        document.body.appendChild(root);
        document.body.classList.add("brave-fishing-active");
        bindFishingMinigameControls(root);
        currentFishingGame = {
            data: data,
            phase: "setup",
            position: 0.5,
            resolving: false,
        };
        var panel = root.querySelector(".brave-fishing-minigame__panel");
        if (panel && typeof panel.focus === "function") {
            panel.focus();
        }
    };

    var fishingOutcomeCommand = function (outcome) {
        if (!currentFishingGame || currentFishingGame.resolving) {
            return;
        }
        currentFishingGame.resolving = true;
        currentFishingGame.phase = "resolving";
        updateFishingMinigameUi();
        sendBrowserCommand(
            "fish resolve "
            + String(currentFishingGame.data.encounter_id || "")
            + " "
            + String(outcome || "fail")
        );
    };

    var fishingPullForFrame = function (game, elapsedSeconds, now) {
        var behavior = game.data.behavior || {};
        var rod = game.data.rod || {};
        var pattern = String(behavior.pattern || "sine").toLowerCase();
        var basePull = getFishingNumber(behavior.base_pull, 0.3);
        var burstPull = getFishingNumber(behavior.burst_pull, 0.08);
        var stability = Math.max(0.45, getFishingNumber(rod.stability, 1));
        var pull = basePull / stability;
        if (pattern === "sine") {
            pull += Math.sin(elapsedSeconds * 4.2) * 0.07;
        } else if (pattern === "linear") {
            pull += 0.04;
        } else if (pattern === "drag") {
            pull += Math.min(0.14, elapsedSeconds * 0.018);
        } else if (pattern === "snag") {
            pull += Math.sin(elapsedSeconds * 7.4) > 0.82 ? burstPull * 0.65 : 0;
        } else if (pattern === "dart") {
            pull += Math.max(0, Math.sin(elapsedSeconds * 8.2)) * burstPull * 0.55;
        } else if (pattern === "burst") {
            if (!game.nextBurstAt || now >= game.nextBurstAt) {
                game.burstUntil = now + 280 + Math.random() * 260;
                game.nextBurstAt = now + 1050 + Math.random() * 1500;
            }
            if (game.burstUntil && now <= game.burstUntil) {
                pull += burstPull;
            }
        }
        return Math.max(0.05, pull) * 0.22;
    };

    var startFishingReeling = function () {
        if (!currentFishingGame || currentFishingGame.phase !== "hook") {
            return;
        }
        var now = performance.now();
        currentFishingGame.phase = "reeling";
        currentFishingGame.phaseStartedAt = now;
        currentFishingGame.lastFrameAt = now;
        currentFishingGame.position = 0.5;
        currentFishingGame.safeMs = 0;
        currentFishingGame.strain = 0;
        currentFishingGame.controlBand = "safe";
        updateFishingMinigameUi();
    };

    var handleFishingReelStart = function () {
        if (!currentFishingGame || currentFishingGame.resolving) {
            return;
        }
        if (currentFishingGame.phase === "hook") {
            startFishingReeling();
            return;
        }
        if (currentFishingGame.phase !== "reeling") {
            return;
        }
        var rod = currentFishingGame.data.rod || {};
        var power = Math.max(1, getFishingNumber(rod.power, 1));
        currentFishingGame.reeling = true;
        currentFishingGame.inputImpulse = Math.min(
            0.1,
            (currentFishingGame.inputImpulse || 0) + 0.018 + power * 0.004
        );
    };

    var handleFishingReelEnd = function () {
        if (currentFishingGame) {
            currentFishingGame.reeling = false;
        }
    };

    var updateFishingMinigameUi = function () {
        var game = currentFishingGame;
        var root = getFishingRoot();
        if (!game || !root) {
            return;
        }
        var phase = game.phase || "waiting";
        root.setAttribute("data-fishing-phase", phase);
        var status = root.querySelector("[data-fishing-status]");
        var reelButton = root.querySelector("[data-brave-fishing-reel]");
        var marker = root.querySelector("[data-fishing-marker]");
        var progress = root.querySelector("[data-fishing-progress]");
        var timer = root.querySelector("[data-fishing-timer]");
        var fishName = root.querySelector("[data-fishing-fish]");
        var result = root.querySelector("[data-fishing-result]");
        var resultActions = root.querySelector("[data-fishing-result-actions]");
        root.setAttribute("data-fishing-band", phase === "reeling" ? (game.controlBand || "safe") : "neutral");
        var position = clampFishingValue(typeof game.position === "number" ? game.position : 0.5, 0, 1);
        if (marker) {
            marker.style.top = (position * 100) + "%";
        }
        if (progress) {
            var duration = Math.max(1, game.durationMs || 1);
            var safeProgress = phase === "result" && game.resultSuccess ? 1 : clampFishingValue((game.safeMs || 0) / duration, 0, 1);
            progress.style.height = (safeProgress * 100) + "%";
        }
        if (fishName) {
            fishName.textContent = phase === "waiting" ? "Line cast" : (game.data.fish && game.data.fish.name ? game.data.fish.name : "Fish");
        }
        if (status) {
            if (phase === "waiting") {
                status.textContent = "Waiting for a bite";
            } else if (phase === "hook") {
                status.textContent = "Bite";
            } else if (phase === "reeling") {
                status.textContent = "Hold Center";
            } else if (phase === "resolving") {
                status.textContent = "Resolving";
            } else if (phase === "result") {
                status.textContent = game.resultSuccess ? "Caught" : "Lost";
            }
        }
        if (timer) {
            timer.textContent = game.timerText || "";
        }
        if (reelButton) {
            reelButton.disabled = phase === "waiting" || phase === "resolving" || phase === "result";
            reelButton.textContent = phase === "hook" ? "Set Hook" : "Pull";
        }
        if (result) {
            result.textContent = game.resultMessage || "";
        }
        if (resultActions) {
            resultActions.hidden = phase !== "result";
        }
    };

    var tickFishingMinigame = function (now) {
        var game = currentFishingGame;
        if (!game) {
            return;
        }
        var phaseElapsed = now - game.phaseStartedAt;
        if (game.phase === "waiting") {
            game.timerText = Math.max(0, Math.ceil((game.waitMs - phaseElapsed) / 1000)) + "s";
            if (phaseElapsed >= game.waitMs) {
                game.phase = "hook";
                game.phaseStartedAt = now;
                game.timerText = "";
            }
        } else if (game.phase === "hook") {
            var hookRemaining = Math.max(0, game.hookMs - phaseElapsed);
            game.timerText = (hookRemaining / 1000).toFixed(1) + "s";
            if (hookRemaining <= 0) {
                fishingOutcomeCommand("fail");
                return;
            }
        } else if (game.phase === "reeling") {
            var dt = game.lastFrameAt ? Math.min(0.05, (now - game.lastFrameAt) / 1000) : 0.016;
            game.lastFrameAt = now;
            var elapsedSeconds = (now - game.phaseStartedAt) / 1000;
            var rod = game.data.rod || {};
            var power = Math.max(1, getFishingNumber(rod.power, 1));
            var duration = Math.max(1, game.durationMs || 14000);
            var elapsedMs = now - game.phaseStartedAt;
            var fatigue = clampFishingValue(1 - (elapsedMs / duration) * 0.32, 0.58, 1);
            var fishPull = fishingPullForFrame(game, elapsedSeconds, now) * fatigue;
            var playerPull = game.reeling ? (0.072 + power * 0.018) : 0;
            var impulse = game.inputImpulse || 0;
            game.inputImpulse = Math.max(0, impulse - dt * 0.38);
            game.position = clampFishingValue((typeof game.position === "number" ? game.position : 0.5) - fishPull * dt + playerPull * dt + impulse, 0, 1);
            var safeLow = getFishingNumber(game.safeLow, 0.38);
            var safeHigh = getFishingNumber(game.safeHigh, 0.66);
            var edgeLow = getFishingNumber(game.edgeLow, 0.04);
            var edgeHigh = getFishingNumber(game.edgeHigh, 0.96);
            var inControl = game.position >= safeLow && game.position <= safeHigh;
            if (inControl) {
                game.safeMs = (game.safeMs || 0) + dt * 1000;
                game.strain = Math.max(0, (game.strain || 0) - dt * 0.55);
            } else {
                var distance = game.position < safeLow ? safeLow - game.position : game.position - safeHigh;
                game.strain = Math.min(1.15, (game.strain || 0) + dt * (0.3 + distance * 2.2));
            }
            game.controlBand = inControl ? "safe" : "danger";
            game.timerText = Math.max(0, Math.ceil((duration - elapsedMs) / 1000)) + "s / strain " + Math.round((game.strain || 0) * 100) + "%";
            if (game.position <= edgeLow || game.position >= edgeHigh || game.strain >= 1) {
                fishingOutcomeCommand("fail");
                return;
            }
            if (elapsedMs >= duration) {
                var safeRatio = (game.safeMs || 0) / duration;
                if (safeRatio < 0.72 || (game.strain || 0) > 0.72) {
                    fishingOutcomeCommand("fail");
                    return;
                }
                var result = safeRatio >= 0.92 && (game.strain || 0) <= 0.18 ? "perfect" : "success";
                fishingOutcomeCommand(result);
                return;
            }
        }
        updateFishingMinigameUi();
        currentFishingAnimationFrame = window.requestAnimationFrame(tickFishingMinigame);
    };

    var bindFishingMinigameControls = function (root) {
        root.addEventListener("click", function (event) {
            var closeTarget = event.target.closest("[data-brave-fishing-close]");
            if (closeTarget) {
                event.preventDefault();
                event.stopPropagation();
                clearFishingMinigame();
                return;
            }
            var commandTarget = event.target.closest("[data-brave-fishing-command]");
            if (commandTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (!commandTarget.disabled) {
                    sendBrowserCommand(commandTarget.getAttribute("data-brave-fishing-command"));
                }
                return;
            }
            var giveUpTarget = event.target.closest("[data-brave-fishing-giveup]");
            if (giveUpTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (currentFishingGame && currentFishingGame.phase === "result") {
                    clearFishingMinigame();
                } else {
                    fishingOutcomeCommand("fail");
                }
                return;
            }
            var castAgainTarget = event.target.closest("[data-brave-fishing-cast-again]");
            if (castAgainTarget) {
                event.preventDefault();
                event.stopPropagation();
                sendBrowserCommand("fish cast");
            }
        }, true);
        root.addEventListener("pointerdown", function (event) {
            if (!event.target.closest("[data-brave-fishing-reel], [data-brave-fishing-lane]")) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            handleFishingReelStart();
        }, true);
        root.addEventListener("pointerup", handleFishingReelEnd, true);
        root.addEventListener("pointercancel", handleFishingReelEnd, true);
        root.addEventListener("pointerleave", handleFishingReelEnd, true);
        root.addEventListener("keydown", function (event) {
            if (event.key !== " " && event.key !== "Enter") {
                return;
            }
            if (!currentFishingGame || (currentFishingGame.phase !== "hook" && currentFishingGame.phase !== "reeling")) {
                return;
            }
            event.preventDefault();
            handleFishingReelStart();
        }, true);
        root.addEventListener("keyup", function (event) {
            if (event.key === " " || event.key === "Enter") {
                handleFishingReelEnd();
            }
        }, true);
    };

    var startFishingMinigame = function (payload) {
        if (typeof clearActivityOverlay === "function") {
            clearActivityOverlay({ suppressArcadeRestore: true });
        }
        clearFishingMinigame();
        var data = payload || {};
        var root = document.createElement("div");
        root.id = "brave-fishing-minigame";
        root.className = "brave-fishing-minigame";
        root.setAttribute("aria-hidden", "false");
        var fish = data.fish || {};
        var rod = data.rod || {};
        var lure = data.lure || {};
        root.innerHTML =
            "<div class='brave-fishing-minigame__backdrop'></div>"
            + "<section class='brave-fishing-minigame__panel' role='dialog' aria-modal='true' tabindex='0'>"
            + "<div class='brave-fishing-minigame__head'>"
            + "<div class='brave-fishing-minigame__titlebar'>"
            + "<span class='brave-fishing-minigame__icon'>" + icon("phishing") + "</span>"
            + "<div class='brave-fishing-minigame__titles'>"
            + "<div class='brave-fishing-minigame__eyebrow'>" + escapeHtml(data.spot || "Fishing Water") + "</div>"
            + "<div class='brave-fishing-minigame__title'>Fishing</div>"
            + "</div>"
            + "<button type='button' class='brave-fishing-minigame__close brave-view__action brave-view__action--muted brave-view__back' data-brave-fishing-close='1' aria-label='Close fishing'>" + icon("close") + "</button>"
            + "</div>"
            + "<div class='brave-fishing-minigame__loadout'>"
            + "<span>" + escapeHtml(rod.name || "Rod") + "</span>"
            + "<span>" + escapeHtml(lure.name || "Lure") + "</span>"
            + "<span>" + escapeHtml(fish.rarity || "Common") + "</span>"
            + "</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__stage'>"
            + "<div class='brave-fishing-minigame__lane' data-brave-fishing-lane='1'>"
            + "<div class='brave-fishing-minigame__zone brave-fishing-minigame__zone--escape'>Slip</div>"
            + "<div class='brave-fishing-minigame__water'></div>"
            + "<div class='brave-fishing-minigame__progress' data-fishing-progress></div>"
            + "<div class='brave-fishing-minigame__marker' data-fishing-marker>" + icon("set_meal") + "</div>"
            + "<div class='brave-fishing-minigame__zone brave-fishing-minigame__zone--hold'>Hold</div>"
            + "<div class='brave-fishing-minigame__zone brave-fishing-minigame__zone--catch'>Snap</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__readout'>"
            + "<div class='brave-fishing-minigame__status' data-fishing-status>Waiting</div>"
            + "<div class='brave-fishing-minigame__fish' data-fishing-fish>" + escapeHtml(fish.name || "Fish") + "</div>"
            + "<div class='brave-fishing-minigame__timer' data-fishing-timer></div>"
            + "<div class='brave-fishing-minigame__result' data-fishing-result></div>"
            + "</div>"
            + "</div>"
            + "<div class='brave-fishing-minigame__controls'>"
            + "<button type='button' class='brave-fishing-minigame__reel' data-brave-fishing-reel='1'>Reel</button>"
            + "<button type='button' class='brave-fishing-minigame__secondary' data-brave-fishing-giveup='1'>Give Up</button>"
            + "</div>"
            + "<div class='brave-fishing-minigame__result-actions' data-fishing-result-actions hidden>"
            + "<button type='button' class='brave-fishing-minigame__secondary' data-brave-fishing-cast-again='1'>Cast Again</button>"
            + "<button type='button' class='brave-fishing-minigame__secondary' data-brave-fishing-command='fish'>Back to Fishing</button>"
            + "</div>"
            + "</section>";
        document.body.appendChild(root);
        document.body.classList.add("brave-fishing-active");
        bindFishingMinigameControls(root);
        currentFishingGame = {
            data: data,
            phase: "waiting",
            position: 0.5,
            waitMs: Math.max(700, parseInt(data.wait_ms || 1600, 10) || 1600),
            hookMs: Math.max(700, parseInt(data.hook_ms || 1500, 10) || 1500),
            durationMs: Math.max(6000, parseInt(data.duration_ms || 14000, 10) || 14000),
            safeLow: 0.38,
            safeHigh: 0.66,
            edgeLow: 0.04,
            edgeHigh: 0.96,
            phaseStartedAt: performance.now(),
            lastFrameAt: null,
            inputImpulse: 0,
            safeMs: 0,
            strain: 0,
            controlBand: "safe",
            reeling: false,
            resolving: false,
        };
        updateFishingMinigameUi();
        var panel = root.querySelector(".brave-fishing-minigame__panel");
        if (panel && typeof panel.focus === "function") {
            panel.focus();
        }
        currentFishingAnimationFrame = window.requestAnimationFrame(tickFishingMinigame);
    };

    var showFishingResult = function (payload) {
        var root = getFishingRoot();
        if (!root || !root.querySelector("[data-fishing-status]")) {
            startFishingMinigame({ fish: {}, rod: {}, lure: {}, wait_ms: 999999, hook_ms: 999999 });
        }
        if (currentFishingAnimationFrame) {
            window.cancelAnimationFrame(currentFishingAnimationFrame);
            currentFishingAnimationFrame = null;
        }
        if (!currentFishingGame) {
            currentFishingGame = { data: {}, position: 0.5 };
        }
        currentFishingGame.phase = "result";
        currentFishingGame.resultSuccess = !!(payload && payload.success);
        currentFishingGame.resultMessage = payload && payload.message ? String(payload.message).replace(/\|[A-Za-z]/g, "") : "";
        updateFishingMinigameUi();
    };

    var handleFishingPayload = function (payload) {
        payload = payload || {};
        if (payload.phase === "setup") {
            renderFishingSetupOverlay(payload);
            return;
        }
        if (payload.phase === "result") {
            showFishingResult(payload);
            return;
        }
        startFishingMinigame(payload);
    };

    var focusViewAutofocusField = function () {
        var field = document.querySelector(".brave-view [data-brave-autofocus='1']");
        if (!field || typeof field.focus !== "function") {
            return;
        }
        window.setTimeout(function () {
            focusWithoutScroll(field);
            if (typeof field.setSelectionRange === "function") {
                var length = String(field.value || "").length;
                field.setSelectionRange(length, length);
            }
        }, 0);
    };

    var startMobileSwipe = function (surface, x, y, identifier, mode, options) {
        options = options || {};
        if (!surface && !hasAnySwipeCommands(options.commands)) {
            currentMobileSwipe = null;
            return;
        }
        currentMobileSwipe = {
            id: identifier,
            mode: mode || "pointer",
            x: x,
            y: y,
            surface: surface,
            commands: options.commands || null,
            flashSurface: options.flashSurface || surface || null,
        };
    };

    var cancelMobileSwipe = function (mode, identifier) {
        if (!currentMobileSwipe) {
            return;
        }
        if (mode && currentMobileSwipe.mode !== mode) {
            return;
        }
        if (identifier !== undefined && identifier !== null && currentMobileSwipe.id !== identifier) {
            return;
        }
        currentMobileSwipe = null;
    };

    var finishMobileSwipe = function (x, y, identifier, event, mode) {
        if (!currentMobileSwipe) {
            return false;
        }
        if (mode && currentMobileSwipe.mode !== mode) {
            return false;
        }
        if (identifier !== undefined && identifier !== null && currentMobileSwipe.id !== identifier) {
            return false;
        }

        var swipeSurface = currentMobileSwipe.surface;
        var swipeCommands = currentMobileSwipe.commands;
        var flashSurface = currentMobileSwipe.flashSurface || swipeSurface;
        var dx = x - currentMobileSwipe.x;
        var dy = y - currentMobileSwipe.y;
        currentMobileSwipe = null;

        var absX = Math.abs(dx);
        var absY = Math.abs(dy);
        if (Math.max(absX, absY) < 18 || (!swipeSurface && !swipeCommands)) {
            return false;
        }

        var direction = null;
        if (absX >= absY) {
            direction = dx > 0 ? "right" : "left";
        } else {
            direction = dy > 0 ? "down" : "up";
        }
        if (!direction) {
            return false;
        }

        var command = swipeSurface ? swipeSurface.getAttribute("data-brave-swipe-" + direction) : null;
        if (!command && swipeCommands) {
            command = swipeCommands[direction] || null;
        }
        if (!command) {
            return false;
        }

        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        suppressBrowserClickUntil = Date.now() + 280;
        if (flashSurface) {
            flashSurface.classList.remove("brave-view__swipe-surface--flash");
            void flashSurface.offsetWidth;
            flashSurface.classList.add("brave-view__swipe-surface--flash");
            window.setTimeout(function () {
                flashSurface.classList.remove("brave-view__swipe-surface--flash");
            }, 180);
        }
        sendBrowserCommand(command);
        return true;
    };

    var shouldPreventSwipeScroll = function (x, y) {
        if (!currentMobileSwipe) {
            return false;
        }
        return Math.max(Math.abs(x - currentMobileSwipe.x), Math.abs(y - currentMobileSwipe.y)) >= 10;
    };

    var submitBrowserForm = function (form) {
        if (!form) {
            return false;
        }
        var mode = form.getAttribute("data-brave-submit-mode") || "command";
        var command = "";
        var fields = Array.prototype.slice.call(form.querySelectorAll(".brave-view__field-input"));
        var firstEmptyField = null;
        var firstField = fields.length ? fields[0] : null;
        var formData = {};
        fields.forEach(function (field) {
            var fieldName = field.getAttribute("name") || "value";
            var rawValue = String(field.value || "");
            var value = rawValue.trim();
            formData[fieldName] = value;
            if (!firstEmptyField && !value) {
                firstEmptyField = field;
            }
        });
        if (firstEmptyField) {
            if (typeof firstEmptyField.focus === "function") {
                firstEmptyField.focus();
            }
            return false;
        }
        var singleValue = fields.length === 1 ? (formData[fields[0].getAttribute("name") || "value"] || "") : "";
        if (mode === "raw") {
            command = singleValue;
        } else if (form.hasAttribute("data-brave-submit-template")) {
            command = form.getAttribute("data-brave-submit-template").replace(/\{([a-zA-Z0-9_-]+)\}/g, function (_match, key) {
                return formData[key] || "";
            }).trim();
        } else if (form.hasAttribute("data-brave-submit-command")) {
            command = form.getAttribute("data-brave-submit-command") + " " + singleValue;
        } else if (form.hasAttribute("data-brave-submit-prefix")) {
            command = form.getAttribute("data-brave-submit-prefix") + " " + singleValue;
        } else {
            command = singleValue;
        }
        if (!command) {
            if (firstField && typeof firstField.focus === "function") {
                firstField.focus();
            }
            return false;
        }
        sendBrowserCommand(command);
        return true;
    };

    var bindBrowserInteractionHandlers = function () {
        if (browserInteractionHandlersBound) {
            return;
        }
        browserInteractionHandlersBound = true;

        document.addEventListener("pointerdown", function (event) {
            if (!isMobileViewport()) {
                return;
            }
            var navTarget = event.target.closest(
                "#mobile-nav-dock .brave-view__navcard, "
                + "#mobile-nav-dock .brave-view__nav-centercard, "
                + "#mobile-nav-dock .brave-view__nav-chip"
            );
            if (!navTarget) {
                return;
            }
            // Keep mobile nav taps from focusing dock controls and yanking the room scroller downward.
            // We set the suppression window but let the standard 'click' handler below take the command,
            // which is more compatible with how closest() works across different DOM depths on touch.
            suppressBrowserClickUntil = 0; // Ensure the following click actually lands
            event.preventDefault();
        }, true);

        document.addEventListener("scroll", function (event) {
            var target = event.target;
            if (!shouldSuppressMobileRoomNavScroll(target)) {
                return;
            }
            target.scrollTop = 0;
        }, true);

        document.addEventListener("click", function (event) {
            if (Date.now() < suppressBrowserClickUntil) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            var formSubmitTarget = event.target.closest(".brave-view__form-submit");
            if (formSubmitTarget) {
                var submitForm = formSubmitTarget.closest("form[data-brave-form='1']");
                if (submitForm) {
                    event.preventDefault();
                    event.stopPropagation();
                    submitBrowserForm(submitForm);
                    return;
                }
            }
            var pickerCloseTarget = event.target.closest("[data-brave-picker-close]");
            if (pickerCloseTarget) {
                event.preventDefault();
                event.stopPropagation();
                clearPickerSheet();
                return;
            }
            var noticeCloseTarget = event.target.closest("[data-brave-notice-close]");
            if (noticeCloseTarget) {
                event.preventDefault();
                event.stopPropagation();
                clearBrowserNotice();
                return;
            }
            var voiceBubbleTarget = event.target.closest("[data-brave-room-voice-id]");
            if (voiceBubbleTarget) {
                event.preventDefault();
                event.stopPropagation();
                dismissRoomVoiceBubble(Number(voiceBubbleTarget.getAttribute("data-brave-room-voice-id")));
                return;
            }
            var chatOpenTarget = event.target.closest("[data-brave-chat-open]");
            if (chatOpenTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (chatOpenTarget.hasAttribute("data-brave-prefill")) {
                    var inputPlugin = getDefaultInPlugin();
                    clearPickerSheet();
                    if (inputPlugin && typeof inputPlugin.openChatDraft === "function") {
                        inputPlugin.openChatDraft(
                            chatOpenTarget.getAttribute("data-brave-prefill"),
                            {
                                prompt: chatOpenTarget.getAttribute("data-brave-chat-prompt") || "",
                            }
                        );
                        return;
                    }
                    prefillBrowserInput(chatOpenTarget.getAttribute("data-brave-prefill"));
                    return;
                }
                focusCommandInput();
                return;
            }
            var activityTabTarget = event.target.closest("[data-brave-activity-tab]");
            if (activityTabTarget) {
                event.preventDefault();
                event.stopPropagation();
                setRoomActivityTab(activityTabTarget.getAttribute("data-brave-activity-tab"));
                return;
            }
            var welcomeNext = event.target.closest("[data-brave-welcome-next]");
            if (welcomeNext) {
                event.preventDefault();
                event.stopPropagation();
                currentWelcomePageIndex++;
                renderWelcomePage();
                return;
            }
            var welcomePrev = event.target.closest("[data-brave-welcome-prev]");
            if (welcomePrev) {
                event.preventDefault();
                event.stopPropagation();
                currentWelcomePageIndex--;
                renderWelcomePage();
                return;
            }
            var objectivesTarget = event.target.closest("[data-brave-objectives-toggle]");
            if (objectivesTarget) {
                event.preventDefault();
                event.stopPropagation();
                toggleObjectives();
                return;
            }
            var mobileTarget = event.target.closest("[data-brave-mobile-panel], [data-brave-mobile-action]");
            if (mobileTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (mobileTarget.hasAttribute("data-brave-mobile-panel")) {
                    toggleMobileUtilityTab(mobileTarget.getAttribute("data-brave-mobile-panel"));
                    return;
                }
                handleMobileUtilityAction(mobileTarget.getAttribute("data-brave-mobile-action"));
                return;
            }
            var activityScrollTarget = event.target.closest("[data-brave-activity-scroll='rail']");
            if (activityScrollTarget) {
                event.preventDefault();
                event.stopPropagation();
                scrollRailActivityToBottom();
                return;
            }
            var combatScrollTarget = event.target.closest("[data-brave-combat-scroll='latest']");
            if (combatScrollTarget) {
                event.preventDefault();
                event.stopPropagation();
                scrollCombatLogToBottom();
                return;
            }
            var combatTabTarget = event.target.closest("[data-brave-combat-tab]");
            if (combatTabTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (combatTabTarget.disabled) {
                    return;
                }
                currentCombatActionTab = combatTabTarget.getAttribute("data-brave-combat-tab") || "abilities";
                syncCombatActionTray();
                return;
            }
            if (handleVideoPickerInteraction(event.target) || handleAudioPickerInteraction(event.target)) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            var target = event.target.closest("[data-brave-command], [data-brave-prefill], [data-brave-picker], [data-brave-connection-screen]");
            if (!target) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (target.hasAttribute("data-brave-connection-screen")) {
                var braveAudioConnection = getBraveAudio();
                if (braveAudioConnection && typeof braveAudioConnection.handleUiAction === "function") {
                    braveAudioConnection.handleUiAction("click");
                }
                openConnectionScreen(target.getAttribute("data-brave-connection-screen"));
                return;
            }
            if (target.hasAttribute("data-brave-picker")) {
                var braveAudioPicker = getBraveAudio();
                if (braveAudioPicker && typeof braveAudioPicker.handleUiAction === "function") {
                    braveAudioPicker.handleUiAction("click");
                }
                if (isMobileViewport()) {
                    currentMobileUtilityTab = null;
                    clearMobileUtilitySheet();
                    renderMobileNavDock();
                }
                openPickerFromTarget(target);
                return;
            }
            if (target.hasAttribute("data-brave-prefill")) {
                clearPickerSheet();
                var braveAudioPrefill = getBraveAudio();
                if (braveAudioPrefill && typeof braveAudioPrefill.handleUiAction === "function") {
                    braveAudioPrefill.handleUiAction("click");
                }
                prefillBrowserInput(target.getAttribute("data-brave-prefill"));
                return;
            }
            sendBrowserCommand(target.getAttribute("data-brave-command"), target.getAttribute("data-brave-confirm"));
        }, true);

        document.addEventListener("submit", function (event) {
            var form = event.target.closest("[data-brave-form='1']");
            if (!form) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            submitBrowserForm(form);
        }, true);

        document.addEventListener("input", function (event) {
            var videoSettingTarget = event.target.closest("[data-brave-video-setting][data-brave-video-kind='range']");
            if (videoSettingTarget) {
                setVideoSetting(videoSettingTarget.getAttribute("data-brave-video-setting"), parseFloat(videoSettingTarget.value || "0"));
                var videoValueNode = videoSettingTarget.parentNode && videoSettingTarget.parentNode.querySelector(".brave-audio-settings__slider-value");
                if (videoValueNode) {
                    videoValueNode.textContent = formatScalePercent(videoSettingTarget.value || "1");
                }
                return;
            }
            var settingTarget = event.target.closest("[data-brave-audio-setting][data-brave-audio-kind='range']");
            if (!settingTarget) {
                return;
            }
            var braveAudio = getBraveAudio();
            if (!braveAudio || typeof braveAudio.setSetting !== "function") {
                return;
            }
            braveAudio.setSetting(settingTarget.getAttribute("data-brave-audio-setting"), parseFloat(settingTarget.value || "0"));
            var valueNode = settingTarget.parentNode && settingTarget.parentNode.querySelector(".brave-audio-settings__slider-value");
            if (valueNode) {
                valueNode.textContent = formatAudioPercent(settingTarget.value || "0");
            }
        }, true);

        document.addEventListener("change", function (event) {
            var toggleTarget = event.target.closest("[data-brave-audio-setting][data-brave-audio-kind='boolean']");
            if (!toggleTarget) {
                return;
            }
            var braveAudio = getBraveAudio();
            if (!braveAudio || typeof braveAudio.setSetting !== "function") {
                return;
            }
            braveAudio.setSetting(toggleTarget.getAttribute("data-brave-audio-setting"), !!toggleTarget.checked);
            renderPickerSheet();
        }, true);

        document.addEventListener("fullscreenchange", function () {
            if (currentPickerData && currentPickerData.picker_kind === "video-settings") {
                renderPickerSheet();
            }
        }, true);

        document.addEventListener("keydown", function (event) {
            if (handleDesktopMovementHotkey(event)) {
                return;
            }
        }, true);

        document.addEventListener("pointerdown", function (event) {
            if (handleVideoPickerInteraction(event.target) || handleAudioPickerInteraction(event.target)) {
                event.preventDefault();
                event.stopPropagation();
                suppressBrowserClickUntil = Date.now() + 320;
                return;
            }
            var directPrefillTarget = event.target.closest(
                ".brave-view__entry--button[data-brave-prefill], "
                + ".brave-view__list-item[data-brave-prefill], "
                + ".brave-view__list-primary[data-brave-prefill], "
                + ".brave-view__mini-action[data-brave-prefill]"
            );
            if (directPrefillTarget && (!event.pointerType || event.pointerType === "touch" || event.pointerType === "pen")) {
                event.preventDefault();
                event.stopPropagation();
                suppressBrowserClickUntil = Date.now() + 320;
                clearPickerSheet();
                prefillBrowserInput(directPrefillTarget.getAttribute("data-brave-prefill"));
                return;
            }
            var swipeSurface = event.target.closest("[data-brave-swipe-surface]");
            if (swipeSurface && (!event.pointerType || event.pointerType === "touch" || event.pointerType === "pen")) {
                startMobileSwipe(swipeSurface, event.clientX, event.clientY, event.pointerId, "pointer");
                if (typeof swipeSurface.setPointerCapture === "function") {
                    try {
                        swipeSurface.setPointerCapture(event.pointerId);
                    } catch (error) {
                        // Ignore pointer-capture failures; the gesture still works without it.
                    }
                }
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if ((!event.pointerType || event.pointerType === "touch" || event.pointerType === "pen") && canStartGlobalRoomSwipe(event.target)) {
                startMobileSwipe(
                    null,
                    event.clientX,
                    event.clientY,
                    event.pointerId,
                    "pointer",
                    {
                        commands: getRoomSwipeCommands(),
                        flashSurface: getMobileSwipeFlashSurface(),
                    }
                );
            }
            if (!currentArcadeState) {
                return;
            }
            var target = event.target.closest("[data-arcade-input], [data-arcade-action]");
            if (!target) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (target.hasAttribute("data-arcade-input")) {
                currentArcadeState.queueDirection(target.getAttribute("data-arcade-input"));
                return;
            }
            var action = target.getAttribute("data-arcade-action");
            if (action === "pause") {
                currentArcadeState.togglePause();
            } else if (action === "quit") {
                currentArcadeState.quit();
            }
        }, true);

        document.addEventListener("pointermove", function (event) {
            if (!currentMobileSwipe || currentMobileSwipe.mode !== "pointer" || event.pointerId !== currentMobileSwipe.id) {
                return;
            }
            if (shouldPreventSwipeScroll(event.clientX, event.clientY)) {
                event.preventDefault();
            }
        }, { capture: true, passive: false });

        document.addEventListener("pointerup", function (event) {
            if (finishMobileSwipe(event.clientX, event.clientY, event.pointerId, event, "pointer")) {
                return;
            }
            var directTarget = event.target.closest(
                ".brave-view__list-primary[data-brave-command], "
                + ".brave-view__list-primary[data-brave-prefill], "
                + ".brave-view__list-primary[data-brave-picker], "
                + ".brave-view__list-primary[data-brave-connection-screen], "
                + ".brave-view__list-item[data-brave-command], "
                + ".brave-view__list-item[data-brave-prefill], "
                + ".brave-view__list-item[data-brave-picker], "
                + ".brave-view__list-item[data-brave-connection-screen], "
                + ".brave-view__entry--button[data-brave-command], "
                + ".brave-view__entry--button[data-brave-prefill], "
                + ".brave-view__entry--button[data-brave-picker], "
                + ".brave-view__entry--button[data-brave-connection-screen], "
                + ".brave-view__mini-action[data-brave-command], "
                + ".brave-view__mini-action[data-brave-prefill], "
                + ".brave-view__mini-action[data-brave-picker], "
                + ".brave-view__mini-action[data-brave-connection-screen], "
                + ".scene-card__item-button[data-brave-command], "
                + ".scene-card__item-button[data-brave-prefill], "
                + ".scene-card__item-button[data-brave-picker], "
                + ".scene-card__item-button[data-brave-connection-screen]"
            );
            if (!directTarget || (event.pointerType && event.pointerType !== "touch" && event.pointerType !== "pen")) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            suppressBrowserClickUntil = Date.now() + 320;
            if (directTarget.hasAttribute("data-brave-connection-screen")) {
                openConnectionScreen(directTarget.getAttribute("data-brave-connection-screen"));
                return;
            }
            if (directTarget.hasAttribute("data-brave-picker")) {
                openPickerFromTarget(directTarget);
                return;
            }
            if (directTarget.hasAttribute("data-brave-prefill")) {
                clearPickerSheet();
                prefillBrowserInput(directTarget.getAttribute("data-brave-prefill"));
                return;
            }
            sendBrowserCommand(directTarget.getAttribute("data-brave-command"), directTarget.getAttribute("data-brave-confirm"));
        }, { capture: true, passive: false });

        document.addEventListener("pointercancel", function (event) {
            cancelMobileSwipe("pointer", event.pointerId);
        }, true);

        if (!window.PointerEvent) {
            document.addEventListener("touchstart", function (event) {
                var surface = event.target.closest("[data-brave-swipe-surface]");
                if (!event.touches || event.touches.length !== 1) {
                    cancelMobileSwipe("touch");
                    return;
                }
                var touch = event.touches[0];
                if (surface) {
                    startMobileSwipe(surface, touch.clientX, touch.clientY, touch.identifier, "touch");
                    return;
                }
                if (canStartGlobalRoomSwipe(event.target)) {
                    startMobileSwipe(
                        null,
                        touch.clientX,
                        touch.clientY,
                        touch.identifier,
                        "touch",
                        {
                            commands: getRoomSwipeCommands(),
                            flashSurface: getMobileSwipeFlashSurface(),
                        }
                    );
                    return;
                }
                cancelMobileSwipe("touch");
            }, { capture: true, passive: true });

            document.addEventListener("touchmove", function (event) {
                if (!currentMobileSwipe || currentMobileSwipe.mode !== "touch") {
                    return;
                }
                if (event.touches && event.touches.length) {
                    var touch = event.touches[0];
                    if (shouldPreventSwipeScroll(touch.clientX, touch.clientY)) {
                        event.preventDefault();
                    }
                }
            }, { capture: true, passive: false });

            document.addEventListener("touchend", function (event) {
                if (currentMobileSwipe && currentMobileSwipe.mode === "touch" && event.changedTouches && event.changedTouches.length) {
                    for (var i = 0; i < event.changedTouches.length; i += 1) {
                        if (finishMobileSwipe(event.changedTouches[i].clientX, event.changedTouches[i].clientY, event.changedTouches[i].identifier, event, "touch")) {
                            return;
                        }
                    }
                    cancelMobileSwipe("touch");
                }
                var directTarget = event.target.closest(
                    ".brave-view__list-primary[data-brave-command], "
                    + ".brave-view__list-primary[data-brave-prefill], "
                    + ".brave-view__list-primary[data-brave-picker], "
                    + ".brave-view__list-primary[data-brave-connection-screen], "
                    + ".brave-view__list-item[data-brave-command], "
                    + ".brave-view__list-item[data-brave-prefill], "
                    + ".brave-view__list-item[data-brave-picker], "
                    + ".brave-view__list-item[data-brave-connection-screen], "
                    + ".brave-view__entry[data-brave-command], "
                    + ".brave-view__entry[data-brave-prefill], "
                    + ".brave-view__entry[data-brave-picker], "
                    + ".brave-view__entry[data-brave-connection-screen], "
                    + ".brave-view__entry--button[data-brave-command], "
                    + ".brave-view__entry--button[data-brave-prefill], "
                    + ".brave-view__entry--button[data-brave-picker], "
                    + ".brave-view__entry--button[data-brave-connection-screen], "
                    + ".brave-view__mini-action[data-brave-command], "
                    + ".brave-view__mini-action[data-brave-prefill], "
                    + ".brave-view__mini-action[data-brave-picker], "
                    + ".brave-view__mini-action[data-brave-connection-screen]"
                );
                if (!directTarget) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                suppressBrowserClickUntil = Date.now() + 320;
                if (directTarget.hasAttribute("data-brave-connection-screen")) {
                    openConnectionScreen(directTarget.getAttribute("data-brave-connection-screen"));
                    return;
                }
                if (directTarget.hasAttribute("data-brave-picker")) {
                    openPickerFromTarget(directTarget);
                    return;
                }
                if (directTarget.hasAttribute("data-brave-prefill")) {
                    clearPickerSheet();
                    prefillBrowserInput(directTarget.getAttribute("data-brave-prefill"));
                    return;
                }
                sendBrowserCommand(directTarget.getAttribute("data-brave-command"), directTarget.getAttribute("data-brave-confirm"));
            }, { capture: true, passive: false });

            document.addEventListener("touchcancel", function (event) {
                if (!currentMobileSwipe || currentMobileSwipe.mode !== "touch") {
                    return;
                }
                if (!event.changedTouches || !event.changedTouches.length) {
                    cancelMobileSwipe("touch");
                    return;
                }
                for (var i = 0; i < event.changedTouches.length; i += 1) {
                    if (event.changedTouches[i].identifier === currentMobileSwipe.id) {
                        cancelMobileSwipe("touch", currentMobileSwipe.id);
                        break;
                    }
                }
            }, true);
        }

        document.addEventListener("keydown", function (event) {
            if (currentArcadeState && currentArcadeState.handleInput && currentArcadeState.handleInput(event.key)) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (event.key === "Escape" && handleEscapeKey()) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            var mobileTarget = event.target.closest("[data-brave-mobile-panel][role='button'], [data-brave-mobile-action][role='button']");
            if (mobileTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (mobileTarget.hasAttribute("data-brave-mobile-panel")) {
                    toggleMobileUtilityTab(mobileTarget.getAttribute("data-brave-mobile-panel"));
                    return;
                }
                handleMobileUtilityAction(mobileTarget.getAttribute("data-brave-mobile-action"));
                return;
            }
            var combatTabTarget = event.target.closest("[data-brave-combat-tab]");
            if (combatTabTarget) {
                event.preventDefault();
                event.stopPropagation();
                if (!combatTabTarget.disabled) {
                    currentCombatActionTab = combatTabTarget.getAttribute("data-brave-combat-tab") || "abilities";
                    syncCombatActionTray();
                }
                return;
            }
            var pickerCloseButton = event.target.closest("[data-brave-picker-close]");
            if (pickerCloseButton) {
                clearPickerSheet();
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            var noticeCloseButton = event.target.closest("[data-brave-notice-close]");
            if (noticeCloseButton) {
                clearBrowserNotice();
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            var formField = event.target.closest(".brave-view__field-input");
            if (formField && event.key === "Enter") {
                var activeForm = formField.closest("[data-brave-form='1']");
                if (activeForm) {
                    event.preventDefault();
                    event.stopPropagation();
                    submitBrowserForm(activeForm);
                    return;
                }
            }
            var target = event.target.closest("[data-brave-command][role='button'], [data-brave-prefill][role='button'], [data-brave-picker][role='button'], [data-brave-connection-screen][role='button']");
            if (!target) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (target.hasAttribute("data-brave-connection-screen")) {
                openConnectionScreen(target.getAttribute("data-brave-connection-screen"));
                return;
            }
            if (target.hasAttribute("data-brave-picker")) {
                openPickerFromTarget(target);
                return;
            }
            if (target.hasAttribute("data-brave-prefill")) {
                clearPickerSheet();
                prefillBrowserInput(target.getAttribute("data-brave-prefill"));
                return;
            }
            sendBrowserCommand(target.getAttribute("data-brave-command"), target.getAttribute("data-brave-confirm"));
        }, true);

        document.addEventListener("focusin", function (event) {
            var target = event.target;
            if (!shouldSuppressMobileNonInputFocus(target)) {
                return;
            }
            window.setTimeout(function () {
                if (target && typeof target.blur === "function" && shouldSuppressMobileNonInputFocus(target)) {
                    try {
                        target.blur();
                    } catch (err) {
                        // Ignore focus cleanup failures.
                    }
                }
                if (shouldSuppressMobileNonInputFocus(target)) {
                    resetAllScrollPositions();
                }
            }, 0);
        }, true);

        window.addEventListener("resize", function () {
            syncMobileShell();
            positionDesktopToolbar();
            if (window.requestAnimationFrame) {
                window.requestAnimationFrame(positionSceneRail);
            } else {
                positionSceneRail();
            }
            syncArcadeBodyState();
            if (currentArcadeState && currentArcadeState.fitScreen) {
                currentArcadeState.fitScreen();
            }
        });

        window.addEventListener("brave:mobile-input-state", function () {
            renderMobileNavDock();
        });
        window.addEventListener("brave:input-mode-change", function () {
            renderMobileNavDock();
        });
    };

    var applyTheme = function (themeKey, options) {
        var selected = normalizeThemeKey(themeKey);
        var preset = THEME_PRESETS[selected] || THEME_PRESETS.hearth;
        var selectedFont = options && typeof options.font === "string" ? options.font : preset.font;
        var sizeValue = options && options.size !== undefined ? options.size : preset.size;
        var parsed = parseFloat(sizeValue);
        var baseSize = Number.isFinite(parsed) && parsed >= 0.8 && parsed <= 1.6 ? parsed : parseFloat(preset.size || "1.0");
        var scaleMultiplier = getVideoSettings().ui_scale;
        var selectedSize = Math.max(0.8, Math.min(1.8, baseSize * scaleMultiplier)).toFixed(2);

        document.body.setAttribute("data-brave-theme", selected);
        document.body.setAttribute("data-brave-font", selectedFont);
        document.documentElement.style.setProperty("--brave-font-size-scale", selectedSize);
        if (!(options && options.skipPulse)) {
            pulseBodyClass("brave-theme-shift", 320);
        }
        if (window.localStorage && !(options && options.skipPersistTheme)) {
            window.localStorage.setItem(THEME_STORAGE_KEY, selected);
            window.localStorage.removeItem(LEGACY_FONT_STORAGE_KEY);
            window.localStorage.removeItem(LEGACY_SIZE_STORAGE_KEY);
        }
    };

    var clearTextOutput = function (options) {
        options = options || {};
        var preservedRoomViewData = null;
        var preservedScroll = options.preserveScroll ? captureMainScrollPositions() : null;
        if (options.preserveScroll && options.deferScrollRestore) {
            pendingMainScrollRestore = preservedScroll;
        } else if (!options.preserveScroll) {
            pendingMainScrollRestore = null;
        }
        if (options.preserveMobileSheet || options.preserveScroll) {
            if (isRoomLikeView(currentRoomViewData)) {
                preservedRoomViewData = currentRoomViewData;
            } else if (isRoomLikeView(currentViewData)) {
                preservedRoomViewData = currentViewData;
            }
        }
        teardownArcadeMode();
        if (currentAtbAnimationFrame && window.cancelAnimationFrame) {
            window.cancelAnimationFrame(currentAtbAnimationFrame);
            currentAtbAnimationFrame = null;
        }
        if (pendingCombatViewRenderTimeout) {
            window.clearTimeout(pendingCombatViewRenderTimeout);
            pendingCombatViewRenderTimeout = null;
        }
        pendingCombatViewData = null;
        if (pendingCombatResultFallbackTimeout) {
            window.clearTimeout(pendingCombatResultFallbackTimeout);
            pendingCombatResultFallbackTimeout = null;
        }
        pendingCombatResultViewData = null;
        if (!options.preserveCombatTransition) {
            clearCombatTransitionState();
        }
        clearSuppressedCombatEntryRefs();
        setMainViewMode(false);
        setStickyViewMode(false);
        suppressNextLookText = false;
        clearRoomVoiceBubbles();
        currentViewData = null;
        currentRoomViewData = preservedRoomViewData;
        syncInputContextForView(null);
        if (!options.preservePicker) {
            clearPickerSheet();
        }
        $("#messagewindow").empty();
        $(".prompt").empty().css({ height: "" });
        clearMobileNavDock({ preserveMobileSheet: !!options.preserveMobileSheet });
        if (options.preserveScroll && !options.deferScrollRestore) {
            restoreMainScrollPositions(preservedScroll);
            pendingMainScrollRestore = null;
        } else if (!options.preserveScroll) {
            resetAllScrollPositions();
        }
    };

    var shouldLogRoomActivity = function (rawText, cls, kwargs) {
        var text = typeof rawText === "string" ? rawText.trim() : "";
        var lowered = text.toLowerCase();
        var cssClass = typeof cls === "string" ? cls : "out";
        if (!text) {
            return false;
        }
        if (cssClass.indexOf("inp") !== -1) {
            return false;
        }
        if (kwargs && kwargs.type === "look") {
            return false;
        }
        if (
            lowered === "you join the fight."
            || lowered === "the room turns before you can set your feet."
            || lowered.indexOf(" joins the fight.") !== -1
            || lowered.indexOf(" joins the fight!") !== -1
            || lowered.indexOf(" breaks away and falls back to ") !== -1
            || lowered === "the last of them falls. the way is clear for now."
            || lowered === "the encounter is over. the road is clear for now."
            || lowered === "the line breaks and the party is driven back toward town."
            || lowered === "the fight breaks wrong, and the danger keeps the road."
            || lowered === "the fight ends with the road still dangerous."
            || lowered === "the party is driven back toward town."
        ) {
            return false;
        }
        return true;
    };

    var blurActiveUiControl = function () {
        var active = document.activeElement;
        var tagName;
        if (!active || active === document.body || active === document.documentElement) {
            return;
        }
        tagName = String(active.tagName || "").toUpperCase();
        if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
            return;
        }
        if (!active.blur || typeof active.blur !== "function") {
            return;
        }
        try {
            active.blur();
        } catch (err) {
            // Ignore focus cleanup failures.
        }
    };

    //
    // By default add all unclaimed onText messages to the #messagewindow <div> and scroll
    var onText = function (args, kwargs) {
        var mwin = $("#messagewindow");
        var cls = kwargs == null ? "out" : kwargs["cls"];
        var appendTarget = mwin;
        var rawText = Array.isArray(args) && typeof args[0] === "string" ? args[0] : "";
        if (Array.isArray(args) && typeof args[0] === "string" && isConnectionScreenText(args[0])) {
            if (!currentViewData || currentViewData.variant !== "connection") {
                currentConnectionScreen = "menu";
            }
            renderConnectionView();
            return true;
        }
        if (
            currentViewData
            && currentViewData.variant === "connection"
            && Array.isArray(args)
            && typeof args[0] === "string"
            && isConnectionScreenFragment(args[0])
        ) {
            renderConnectionView();
            return true;
        }
        if (currentViewData && currentViewData.variant === "chargen") {
            return true;
        }
        if (currentViewData && rawText.trim() === "") {
            return true;
        }
        if (
            isStructuredMenuViewActive()
            && typeof cls === "string"
            && cls.indexOf("inp") !== -1
        ) {
            return true;
        }
        if (kwargs && kwargs.type === "look" && suppressNextLookText) {
            return true;
        }
        var combatActiveAtTextStart = isCombatUiActive();
        if (
            !combatActiveAtTextStart
            &&
            !combatViewTransitionActive
            && ((document.body.classList.contains("brave-mainview-active")
                && !document.body.classList.contains("brave-sticky-view-active")
                && !isRoomLikeView(currentViewData))
                || ((kwargs && kwargs.type === "look") && !currentViewData))
        ) {
            clearTextOutput(getRoomRefreshPopupPreservationOptions());
        }
        var combatFx = null;
        var shouldRouteToCombatLog = combatActiveAtTextStart || isCombatUiActive();
        if (shouldRouteToCombatLog) {
            combatFx = extractCombatFxMarkers(rawText);
            appendTarget = ensureCombatLog() || mwin;
        } else if (
            currentViewData
            && isRoomLikeView(currentViewData)
        ) {
            if (shouldLogRoomActivity(rawText, cls, kwargs)) {
                pushRoomFeedEntry(cls || "out", rawText, kwargs || {});
            }
            return true;
        }
        var displayHtml = combatFx ? combatFx.html : rawText;
        appendTarget.append("<div class='" + cls + "'>" + displayHtml + "</div>");
        if (shouldRouteToCombatLog) {
            var appended = appendTarget.children().last().get(0);
            if (appended && combatFx && combatFx.events.length) {
                appended.dataset.braveFx = JSON.stringify(combatFx.events);
                if (combatFx.events.some(function (event) { return event && event.kind === "action"; })) {
                    appended.classList.add("brave-combat-log__entry--action");
                }
            }
            applyCombatFloatersFromNode(appended);
            claimCombatLogEntries();
        }
        if (currentViewData && currentViewData.variant === "connection") {
            pruneLegacyConnectionBoilerplate();
        }
        if (appendTarget.length && appendTarget[0] !== mwin[0]) {
            appendTarget.scrollTop(appendTarget[0].scrollHeight);
            return true;
        }
        var scrollHeight = mwin.parent().parent().prop("scrollHeight");
        mwin.parent().parent().animate({ scrollTop: scrollHeight }, 0);

        return true;
    };

    //
    // By default just show the prompt.
    var onPrompt = function (args, kwargs) {
        var prompts = $(".prompt");

        for (var x = 0; x < prompts.length; x++) {
            var prmpt = $(prompts[x]);
            var sibling = prmpt.siblings().first();

            prmpt.addClass("out").html(args[0]).css({ height: "1.5em" });

            sibling.css({ height: "calc(100% - 1.5em)" });
        }

        return true;
    };

    //
    // Handle Brave-specific OOB events before falling back to generic errors.
    var onUnknownCmd = function (cmdname, args, kwargs) {
        console.log("!!! OOB RECEIVE:", cmdname, args, kwargs);
        if (cmdname === "mapdata") {
            var mapPayload = getOobPayload(args, kwargs, "mapdata", "");
            renderMap(mapPayload);
            return true;
        }

        if (cmdname === "brave_font") {
            return true;
        }

        if (cmdname === "brave_theme") {
            if (kwargs && typeof kwargs.theme === "string") {
                applyTheme(kwargs.theme, kwargs);
            }
            return true;
        }

        if (cmdname === "brave_scene") {
            var scenePayload = getOobPayload(args, kwargs, "brave_scene", {});
            currentRoomSceneData = (scenePayload && typeof scenePayload === "object") ? scenePayload : {};
            if (isCombatUiActive()) {
                return true;
            }
            if (isPreservedSystemViewActive() && !shouldAllowCurrentRoomRefreshNavigation()) {
                return true;
            }
            renderSceneCard(scenePayload || {});
            return true;
        }

        if (cmdname === "brave_view") {
            var viewPayload = getOobPayload(args, kwargs, "brave_view", {});
            if (shouldIgnoreRoomViewDuringCombat(viewPayload || {})) {
                return true;
            }
            renderMainView(viewPayload || {});
            return true;
        }

        if (cmdname === "brave_arcade") {
            startArcadeMode(getOobPayload(args, kwargs, "brave_arcade", {}) || {});
            return true;
        }

        if (cmdname === "brave_panel") {
            var panelPayload = getOobPayload(args, kwargs, "brave_panel", {});
            if (isCombatPanelData(panelPayload || {}) && !isCombatUiActive()) {
                pendingCombatPanelData = panelPayload || {};
                return true;
            }
            if (
                isCombatPanelData(panelPayload || {})
                && (hasCombatFxWork() || !!pendingCombatViewData || combatViewTransitionActive || !!pendingCombatResultViewData)
            ) {
                pendingCombatPanelData = panelPayload || {};
                return true;
            }
            if (isCombatUiActive() && !isCombatPanelData(panelPayload || {})) {
                return true;
            }
            renderPanelCard(panelPayload || {});
            return true;
        }

        if (cmdname === "brave_combat_fx") {
            console.log("DEBUG: OOB event received:", cmdname, { args: args, kwargs: kwargs });
            var combatFxPayload = getOobPayload(args, kwargs, "brave_combat_fx", {}) || {};
            handleCombatFxEvent(combatFxPayload);
            var braveAudioCombat = getBraveAudio();
            if (braveAudioCombat && typeof braveAudioCombat.handleCombatFx === "function") {
                braveAudioCombat.handleCombatFx(combatFxPayload);
            }
            return true;
        }

        if (cmdname === "brave_notice") {
            renderBrowserNotice(getOobPayload(args, kwargs, "brave_notice", {}) || {});
            return true;
        }

        if (cmdname === "brave_objectives_update") {
            var refreshPayload = getOobPayload(args, kwargs, "brave_objectives_update", {}) || {};
            if (refreshPayload.tutorial) {
                renderObjectives({ guidance: refreshPayload.tutorial.guidance, guidance_eyebrow: refreshPayload.tutorial.eyebrow, guidance_title: refreshPayload.tutorial.title });
            }
            if (refreshPayload.tracked_quest && canRenderSceneRailNow()) {
                renderSceneCard({ tracked_quest: refreshPayload.tracked_quest });
            } else if (isStructuredMenuViewActive()) {
                clearSceneCard();
            }
            return true;
        }

        if (cmdname === "brave_quest_complete") {
            var questPayload = getOobPayload(args, kwargs, "brave_quest_complete", {}) || {};
            console.log("DEBUG: Quest Complete payload:", questPayload);
            renderQuestCompleteOverlay(questPayload);
            return true;
        }

        if (cmdname === "brave_fishing") {
            handleFishingPayload(getOobPayload(args, kwargs, "brave_fishing", {}) || {});
            return true;
        }

        if (cmdname === "brave_cooking") {
            renderCookingOverlay(getOobPayload(args, kwargs, "brave_cooking", {}) || {});
            return true;
        }

        if (cmdname === "brave_tinkering") {
            renderTinkeringOverlay(getOobPayload(args, kwargs, "brave_tinkering", {}) || {});
            return true;
        }

        if (cmdname === "brave_mastery") {
            renderMasteryOverlay(getOobPayload(args, kwargs, "brave_mastery", {}) || {});
            return true;
        }

        if (cmdname === "brave_room_activity") {
            var activityPayload = getOobPayload(args, kwargs, "brave_room_activity", {}) || {};
            pushRoomFeedEntry(activityPayload.cls || "out", activityPayload.text || "", activityPayload);
            var braveAudioActivity = getBraveAudio();
            if (braveAudioActivity && typeof braveAudioActivity.handleRoomActivity === "function") {
                braveAudioActivity.handleRoomActivity(activityPayload);
            }
            return true;
        }

        if (cmdname === "brave_clear") {
            if (isCombatUiActive()) {
                return true;
            }
            if (isPreservedSystemViewActive() && !shouldAllowCurrentRoomRefreshNavigation()) {
                return true;
            }
            allowNextRoomRefreshNavigationUntil = 0;
            var clearOptions = getRoomRefreshPopupPreservationOptions();
            if (clearOptions.preserveScroll) {
                pendingMainScrollRestore = captureMainScrollPositions();
            } else {
                clearOptions.deferScrollRestore = false;
                clearTextOutput(clearOptions);
                clearSceneRail();
            }
            return true;
        }

        if (cmdname === "brave_clear_all") {
            clearTextOutput();
            clearSceneRail();
            clearReactiveState();
            return true;
        }

        if (cmdname === "brave_connection") {
            var connectionPayload = getOobPayload(args, kwargs, "brave_connection", {}) || {};
            resetToConnectionView(connectionPayload && typeof connectionPayload.screen === "string" ? connectionPayload.screen : "menu");
            return true;
        }

        if (cmdname === "brave_combat_done") {
            if (pendingCombatResultViewData) {
                forceFlushQueuedCombatResultView();
                return true;
            }
            if (
                (currentViewData && currentViewData.variant === "combat-result")
                || document.querySelector("#messagewindow .brave-view--combat-result")
            ) {
                return true;
            }
            teardownCombatUiState();
            return true;
        }

        if (cmdname === "brave_arcade_done") {
            var arcadeDonePayload = getOobPayload(args, kwargs, "brave_arcade_done", {}) || {};
            teardownArcadeMode();
            restoreArcadeRoomView();
            if (
                arcadeDonePayload
                && ((Array.isArray(arcadeDonePayload.summary_stats) && arcadeDonePayload.summary_stats.length)
                    || (Array.isArray(arcadeDonePayload.leaderboard) && arcadeDonePayload.leaderboard.length)
                    || (Array.isArray(arcadeDonePayload.notes) && arcadeDonePayload.notes.length)
                    || (Array.isArray(arcadeDonePayload.stats) && arcadeDonePayload.stats.length)
                    || Array.isArray(arcadeDonePayload.lines) && arcadeDonePayload.lines.length
                    || arcadeDonePayload.title)
            ) {
                renderArcadeResultOverlay(arcadeDonePayload);
            }
            return true;
        }

        if (isCombatUiActive()) {
            return true;
        }

        var mwin = $("#messagewindow");
        mwin.append(
            "<div class='msg err'>"
            + "Error or Unhandled event:<br>"
            + cmdname + ", "
            + JSON.stringify(args) + ", "
            + JSON.stringify(kwargs) + "<p></div>"
        );
        mwin.scrollTop(mwin[0].scrollHeight);

        return true;
    };

    //
    // Mandatory plugin init function
    var init = function () {
        applyVideoSettings(getVideoSettings(), { persist: false, refreshTheme: false });
        var storedTheme = window.localStorage ? window.localStorage.getItem(THEME_STORAGE_KEY) : null;
        applyTheme(storedTheme || "hearth");
        var braveAudio = getBraveAudio();
        if (braveAudio && typeof braveAudio.init === "function") {
            braveAudio.init({ manifestUrl: window.BRAVE_AUDIO_MANIFEST_URL || "" });
        }
        clearBrowserNotice();
        clearSceneRail();
        clearReactiveState();
        bindBrowserInteractionHandlers();
        ensureConnectionBoilerplateObserver();
        ensureRoomActivityObserver();
        ensureCombatLogObserver();
        currentConnectionScreen = "menu";
        renderConnectionView();
        renderDesktopToolbar();
        console.log("DefaultOut initialized");
    };

    var onLoggedIn = function () {
        clearSceneRail();
        renderDesktopToolbar();
        resetAllScrollPositions();
        finishGameIntroVeil();
        if (currentViewData && currentViewData.variant === "connection") {
            window.setTimeout(function () {
                if (currentViewData && currentViewData.variant === "connection") {
                    sendBrowserCommand("look");
                }
            }, 80);
        }
    };

    var onConnectionClose = function () {
        teardownArcadeMode();
        clearBrowserNotice();
        clearSceneRail();
        renderDesktopToolbar();
        resetAllScrollPositions();
        clearReactiveState();
    };

    return {
        init: init,
        onText: onText,
        onPrompt: onPrompt,
        onUnknownCmd: onUnknownCmd,
        onLoggedIn: onLoggedIn,
        onConnectionClose: onConnectionClose,
        handleEscapeKey: handleEscapeKey,
    };
})();
plugin_handler.add("defaultout", defaultout_plugin);
