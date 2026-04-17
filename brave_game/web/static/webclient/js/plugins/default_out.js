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
    var LEGACY_FONT_STORAGE_KEY = "brave.webclient.font";
    var LEGACY_SIZE_STORAGE_KEY = "evenniaFontSize";
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
    var currentSceneData = null;
    var currentRoomFeedEntries = [];
    var roomActivityRailPinnedToBottom = true;
    var roomActivityRailScrollTop = 0;
    var roomActivityRailMissedCount = 0;
    var combatLogPinnedToBottom = true;
    var combatLogScrollTop = 0;
    var currentMapText = "";
    var currentMapGrid = null;
    var currentArcadeState = null;
    var currentMobileUtilityTab = null;
    var mobileRoomActivityUnreadCount = 0;
    var currentCombatActionTab = "abilities";
    var currentMobileSwipe = null;
    var currentPickerData = null;
    var currentPickerAnchorRect = null;
    var currentPickerSourceId = "";
    var currentNoticeTimer = null;
    var currentConnectionScreen = "menu";
    var suppressBrowserClickUntil = 0;
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
    var suppressedCombatEntryRefs = {};
    var combatViewTransitionActive = false;
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

    var prefersReducedMotion = function () {
        return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
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

    var syncInputContextForView = function (viewData) {
        var inputPlugin = getDefaultInPlugin();
        if (!inputPlugin || typeof inputPlugin.setInputContext !== "function") {
            return;
        }
        var nextContext = "command";
        if (
            viewData
            && viewData.variant !== "connection"
            && viewData.variant !== "chargen"
            && !(viewData.reactive && viewData.reactive.scene === "account")
        ) {
            nextContext = "play";
        }
        inputPlugin.setInputContext(nextContext);
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
        if (inputPlugin && typeof inputPlugin.openMobileInput === "function") {
            inputPlugin.openMobileInput();
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
        if (!isRoomLikeView(currentViewData)) {
            return null;
        }
        return currentViewData;
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
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--score'><span class='brave-view__arcade-stat-label'>1UP</span><span class='brave-view__arcade-stat-value' data-arcade-score>0</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--high'><span class='brave-view__arcade-stat-label'>High</span><span class='brave-view__arcade-stat-value' data-arcade-high-score>" + escapeHtml(highScore) + "</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--lives'><span class='brave-view__arcade-stat-label'>Lives</span><span class='brave-view__arcade-stat-value' data-arcade-lives>3</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--level'><span class='brave-view__arcade-stat-label'>Level</span><span class='brave-view__arcade-stat-value' data-arcade-level>1</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--bonus'><span class='brave-view__arcade-stat-label'>Bonus</span><span class='brave-view__arcade-stat-value' data-arcade-bonus data-arcade-tone='pie'>PIE 100</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--queue'><span class='brave-view__arcade-stat-label'>Queue</span><span class='brave-view__arcade-stat-value' data-arcade-queue>LEFT</span></div>"
            + "<div class='brave-view__arcade-stat brave-view__arcade-stat--status'><span class='brave-view__arcade-stat-label'>State</span><span class='brave-view__arcade-stat-value' data-arcade-status data-arcade-tone='ready'>READY!</span></div>"
            + "</div>"
            + "<div class='brave-view__arcade-frame'>"
            + "<pre class='brave-view__arcade-screen' aria-live='polite'></pre>"
            + "</div>"
            + "<div class='brave-view__arcade-footer'>"
            + "<span class='brave-view__arcade-hint brave-view__arcade-hint--move'>Arrows or WASD steer.</span>"
            + "<span class='brave-view__arcade-hint brave-view__arcade-hint--pause'>P pauses. Q cashes out.</span>"
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
            "#..........................#",
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
        if (!screen || !frame || !scoreNode || !highScoreNode || !livesNode || !levelNode || !bonusNode || !queueNode || !statusNode) {
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
            var shellTop = host.getBoundingClientRect().top;
            var availableWidth = Math.max(220, frame.clientWidth - 18);
            var reservedHeight = 26;
            var footerVisible = footer && window.getComputedStyle(footer).display !== "none";
            var controlsVisible = mobileControls && window.getComputedStyle(mobileControls).display !== "none";
            if (marquee) {
                reservedHeight += marquee.offsetHeight + 10;
            }
            if (footerVisible) {
                reservedHeight += footer.offsetHeight + 10;
            }
            if (controlsVisible) {
                reservedHeight += mobileControls.offsetHeight + 10;
            }
            var availableHeight = Math.max(
                180,
                Math.floor(window.innerHeight - shellTop - reservedHeight - (isMobileViewport() ? 16 : 26))
            );
            var widthFit = availableWidth / (width * 0.66);
            var heightFit = availableHeight / height;
            var minimum = isMobileViewport() ? 7.2 : 8.8;
            var maximum = isMobileViewport() ? 16 : 22;
            var fontSize = Math.max(minimum, Math.min(maximum, Math.floor(Math.min(widthFit, heightFit) * 100) / 100));
            frame.style.maxHeight = availableHeight + "px";
            frame.style.overflow = "hidden";
            screen.style.fontSize = fontSize + "px";
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
            bonusNode.textContent = currentBonusLabel(now);
            bonusNode.setAttribute("data-arcade-tone", bonusTone);
            queueNode.textContent = dirDisplay(state.player && state.player.nextDir ? state.player.nextDir : state.player && state.player.dir ? state.player.dir : null);
            statusNode.textContent = currentStatusLabel(now);
            statusNode.setAttribute("data-arcade-tone", statusTone);
            host.setAttribute("data-arcade-bonus-tone", bonusTone);
            host.setAttribute("data-arcade-status-tone", statusTone);
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
            finishRun("quit");
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

        var selector = payload && payload.game
            ? ".brave-view__arcade-shell[data-arcade-game='" + payload.game + "']"
            : ".brave-view__arcade-shell";
        var host = document.querySelector(selector) || document.querySelector(".brave-view__arcade-shell");
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
        var tracked = currentSceneData && currentSceneData.tracked_quest ? currentSceneData.tracked_quest : null;
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
            + " data-brave-mobile-panel='map' title='Open map'>"
            + "<span class='brave-view__mobile-utility-label'>Micromap</span>"
            + (currentMapGrid
                ? "<div class='brave-view__mobile-map-grid'>" + renderMapGrid(currentMapGrid, "brave-view__map-grid--compact") + "</div>"
                : (currentMapText
                    ? "<pre class='brave-view__mobile-map-pre'>" + escapeHtml(currentMapText) + "</pre>"
                    : "<div class='brave-view__mobile-map-placeholder'>" + icon("explore") + "<span>Open map</span></div>"))
            + "</button>";
        var questMarkup = (
            "<button type='button' class='brave-view__mobile-quest brave-click'"
            + " data-brave-mobile-panel='quest' title='Open quests'>"
            + "<div class='brave-view__mobile-utility-label'>Quests</div>"
            + (tracked
                ? "<div class='brave-view__mobile-quest-title'>" + escapeHtml(tracked.title || "") + "</div>"
                    + (objective ? "<div class='brave-view__mobile-quest-line'>" + escapeHtml(objective) + "</div>" : "<div class='brave-view__mobile-quest-line'>Open the journal for full objectives.</div>")
                : "<div class='brave-view__mobile-quest-title'>No tracked quest</div>"
                    + "<div class='brave-view__mobile-quest-line'>Open your journal to track one.</div>")
            + "</button>"
        );
        var statusMarkup =
            "<div class='brave-view__mobile-status' role='status' aria-label='Room status'>"
            + "<div class='brave-view__mobile-utility-label'>Status</div>"
            + "<div class='brave-view__mobile-status-main'>"
            + "<span class='brave-view__mobile-status-value'>" + escapeHtml(stateLabel) + "</span>"
            + "<span class='brave-view__mobile-status-routes'>" + escapeHtml(routeLabel) + "</span>"
            + "</div>"
            + "<div class='brave-view__mobile-status-copy'>" + escapeHtml(stateCopy) + "</div>"
            + "</div>";
        return "<div class='brave-view__mobile-utility'>" + mapMarkup + "<div class='brave-view__mobile-utility-side'>" + questMarkup + statusMarkup + "</div></div>";
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
        return (
            "<div class='brave-mobile-tools'>"
            + buildMobileUtilityButton("activity", "Activity", "timeline", currentMobileUtilityTab === "activity", mobileRoomActivityUnreadCount)
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

    var getMobileUtilityTabLabel = function (tab) {
        if (tab === "activity") {
            return "Activity";
        }
        if (tab === "menu") {
            return "Menu";
        }
        return "Menu";
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
                + "<div class='brave-mobile-activity-log brave-room-log'>"
                + "<div class='brave-room-log__body brave-room-log__body--mobile' role='log' aria-live='polite' aria-relevant='additions text'>"
                + currentRoomFeedEntries.map(renderRoomFeedEntryMarkup).join("")
                + "</div>"
                + "</div>"
                + "</div>";
        } else if (tab === "menu") {
            bodyMarkup =
                "<div class='brave-mobile-sheet__section'>"
                + "<div class='brave-mobile-sheet__list'>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='sheet'>Character Sheet</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='gear'>Equipment</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='pack'>Pack</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='quests'>Journal</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='map'>Map</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='party'>Party</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='theme'>Theme</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='help'>Help</button>"
                + "<button type='button' class='brave-mobile-sheet__action' data-brave-mobile-action='command'>Command</button>"
                + "<button type='button' class='brave-mobile-sheet__action brave-click' data-brave-command='quit'>Quit</button>"
                + "</div>"
                + "</div>";
        }

        return (
            "<div class='" + panelClass + "'>"
            + buildMobileSheetTabsMarkup()
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
        if (document.body && document.body.classList.contains("brave-notice-active")) {
            clearBrowserNotice();
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
        return true;
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
        if (!pickerData || (!pickerOptions.length && !pickerBody.length)) {
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

        host.innerHTML =
            "<div class='" + backdropClass + "' data-brave-picker-close='1'></div>"
            + "<div class='" + panelClass + "' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Details") + "'" + panelStyle + ">"
            + "<div class='brave-picker-sheet__head'>"
            + "<div class='brave-picker-sheet__titlebar'>"
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
        if (!pickerData || (!hasOptions && !hasBody)) {
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
            return openPickerSheet(pickerData);
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
        if (isMobileViewport() && openMobileCommandTray()) {
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
            title: "Menu",
            options: [
                { label: "Character Sheet", icon: "person", command: "sheet" },
                { label: "Equipment", icon: "shield", command: "gear" },
                { label: "Pack", icon: "backpack", command: "pack" },
                { label: "Journal", icon: "menu_book", command: "quests" },
                { label: "Map", icon: "map", command: "map" },
                { label: "Party", icon: "group", command: "party" },
                { label: "Theme", icon: "snowflake", command: "theme" },
                { label: "Help", icon: "help", command: "help" },
                { label: "Quit", icon: "logout", command: "quit", tone: "danger" }
            ]
        };
    };

    var positionDesktopToolbar = function () {
        var toolbar = document.getElementById("toolbar");
        if (!toolbar || toolbar.getAttribute("aria-hidden") !== "false" || isMobileViewport()) {
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

    var renderMap = function (payload) {
        var micromaps = document.querySelectorAll(".brave-view__micromap");
        var state = getMapPayloadState(payload);
        currentMapText = state.text;
        currentMapGrid = state.grid;
        if (micromaps.length) {
            micromaps.forEach(function (micromap) {
                var mapMarkup = currentMapText ? escapeHtml(currentMapText) : "";
                if (!mapMarkup && currentMapGrid) {
                    mapMarkup = renderMapGrid(currentMapGrid, "brave-view__map-grid--micro");
                }
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
        if (name === "check_circle" || name === "task_alt") {
            var checkClasses = "brave-icon brave-icon--check-circle";
            if (extraClass) {
                checkClasses += " " + extraClass;
            }
            return "<span class='" + checkClasses + "' aria-hidden='true'></span>";
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
        if (!entry || (!entry.command && !entry.prefill && !entry.picker && !entry.connection_screen)) {
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
        if (entry.picker) {
            attrs += " data-brave-picker='" + escapeHtml(JSON.stringify(entry.picker)) + "'";
            if (entry.picker.picker_id) {
                attrs += " data-brave-picker-id='" + escapeHtml(String(entry.picker.picker_id)) + "'";
            }
            if (!titleValue && entry.label) {
                titleValue = entry.label;
            }
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
        return !!(entry && (entry.command || entry.prefill || entry.picker || entry.connection_screen));
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
                subtitle: "Enter your account username and password.",
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
                                enterkeyhint: "go",
                            },
                        ],
                        submit_template: "create {username} {password}",
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
            eyebrow: "Welcome.",
            eyebrow_icon: null,
            title: "",
            title_icon: null,
            subtitle: "",
            chips: [],
            actions: [],
            sections: [
                {
                    label: "Account",
                    icon: "login",
                    kind: "list",
                    items: [
                        {
                            text: "Sign In",
                            badge: "IN",
                            connection_screen: "signin",
                        },
                        {
                            text: "Create Account",
                            badge: "NEW",
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
        return Array.prototype.slice.call(document.querySelectorAll(".brave-view--combat .brave-view__entry[data-entry-ref]"));
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
        return document.querySelector(".brave-view--combat .brave-view__entry[data-entry-ref='" + escapeCssAttributeValue(ref) + "']");
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
            style.textContent = ".brave-view--combat .brave-view__entry[data-entry-ref='" + ref + "'] { visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }";
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
            var node = document.querySelector(".brave-view--combat .brave-view__entry[data-entry-ref='" + ref + "']");
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
        target.innerHTML = source.innerHTML;
    };

    var reconcileCombatEntryCollection = function (targetEntries, sourceEntries) {
        if (!targetEntries || !sourceEntries) {
            return;
        }
        var currentChildren = Array.prototype.slice.call(targetEntries.children || []);
        var currentByRef = {};
        currentChildren.forEach(function (child) {
            var ref = child.getAttribute("data-entry-ref") || "";
            if (ref) {
                currentByRef[ref] = child;
            }
        });
        var nextOrder = [];
        Array.prototype.slice.call(sourceEntries.children || []).forEach(function (sourceChild) {
            var ref = sourceChild.getAttribute("data-entry-ref") || "";
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

        var currentSections = Array.prototype.slice.call(currentSectionsWrap.children || []);
        var nextSections = Array.prototype.slice.call(nextSectionsWrap.children || []);
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
        queueCombatFxEvents(events);
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
            var node = document.querySelector(".brave-view--combat .brave-view__entry[data-entry-ref='" + snapshot.ref + "']");
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

    var renderConnectionView = function () {
        renderMainView(buildConnectionViewData());
        pruneLegacyConnectionBoilerplate();
    };

    var resetToConnectionView = function (screen) {
        clearTextOutput();
        clearSceneRail();
        clearReactiveState();
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

    var showCombatTransitionOverlay = function (viewData) {
        if (!document.body) {
            return;
        }
        clearCombatTransitionOverlay();
        var overlay = document.createElement("div");
        overlay.id = "brave-combat-transition";
        overlay.className = "brave-combat-transition";
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
            + "<div class='brave-combat-transition__card'>"
            + "<div class='brave-combat-transition__eyebrow'>"
            + icon("swords", "brave-combat-transition__eyebrow-icon")
            + "<span>Encounter</span>"
            + "</div>"
            + "<div class='brave-combat-transition__title'>" + escapeHtml(title) + "</div>"
            + (subtitle ? "<div class='brave-combat-transition__subtitle'>" + escapeHtml(subtitle) + "</div>" : "")
            + "</div>";
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
        combatViewTransitionActive = false;
        if (document.body) {
            document.body.classList.remove("brave-combat-transition-active");
        }
        clearCombatTransitionOverlay();
    };

    var finishCombatTransitionOverlay = function () {
        var overlay = document.getElementById("brave-combat-transition");
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
            }
            clearCombatTransitionOverlay();
        }, 320);
    };

    var startCombatTransition = function (viewData) {
        if (!viewData || viewData.variant !== "combat" || prefersReducedMotion()) {
            return false;
        }
        pendingCombatTransitionViewData = viewData;
        combatViewTransitionActive = true;
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        if (document.body) {
            document.body.classList.add("brave-combat-transition-active");
        }
        showCombatTransitionOverlay(viewData);
        pendingCombatTransitionTimeout = window.setTimeout(function () {
            var queuedViewData = pendingCombatTransitionViewData;
            pendingCombatTransitionTimeout = null;
            pendingCombatTransitionViewData = null;
            if (!queuedViewData) {
                clearCombatTransitionState();
                return;
            }
            renderMainView(queuedViewData, { skipCombatTransition: true });
            finishCombatTransitionOverlay();
        }, 980);
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
    };

    var clearReactiveState = function () {
        setBodyState("scene", "system");
        setBodyState("world-tone", "neutral");
        setBodyState("danger", "");
        setBodyState("boss", "");
        setBodyState("view", "");
        document.body.classList.remove("brave-tone-shift", "brave-scene-shift", "brave-scene-combat-enter", "brave-combat-transition-active");
        if (pendingCombatTransitionTimeout) {
            window.clearTimeout(pendingCombatTransitionTimeout);
            pendingCombatTransitionTimeout = null;
        }
        if (pendingCombatTransitionCleanupTimeout) {
            window.clearTimeout(pendingCombatTransitionCleanupTimeout);
            pendingCombatTransitionCleanupTimeout = null;
        }
        pendingCombatTransitionViewData = null;
        combatViewTransitionActive = false;
        clearCombatTransitionOverlay();
        clearCombatFxOverlay();
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

    var renderRoomFeedEntryMarkup = function (entry) {
        if (!entry || !entry.text) {
            return "";
        }
        var cls = entry.cls || "out";
        return "<div class='" + cls + "'>" + escapeHtml(entry.text) + "</div>";
    };

    var addRoomFeedEntry = function (cls, rawContent) {
        if (typeof rawContent !== "string" || !rawContent.trim()) {
            return false;
        }
        var text = rawContent.replace(/\s+/g, " ").trim();
        if (!text) {
            return false;
        }
        var normalizedCls = cls || "out";
        var lastEntry = currentRoomFeedEntries.length ? currentRoomFeedEntries[currentRoomFeedEntries.length - 1] : null;
        if (lastEntry && lastEntry.cls === normalizedCls && lastEntry.text === text) {
            return false;
        }
        currentRoomFeedEntries.push({ cls: normalizedCls, text: text });
        if (currentRoomFeedEntries.length > 24) {
            currentRoomFeedEntries = currentRoomFeedEntries.slice(currentRoomFeedEntries.length - 24);
        }
        return true;
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

    var pushRoomFeedEntry = function (cls, rawText) {
        if (isCombatUiActive()) {
            return;
        }
        var added = addRoomFeedEntry(cls, rawText);
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
        }
    };

    var clearRoomActivityLog = function () {
        currentRoomFeedEntries = [];
        roomActivityRailPinnedToBottom = true;
        roomActivityRailScrollTop = 0;
        roomActivityRailMissedCount = 0;
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
            && document.body.getAttribute("data-brave-scene") === "combat"
            && window.matchMedia("(max-width: 640px)").matches;
        var preferredParent = useInlineStickyLog && inlineSectionParent.length ? inlineSectionParent : (useInlineStickyLog ? sticky : mwin);
        var fallbackParent = useInlineStickyLog ? sticky.add(mwin) : sticky;

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
        return (
            "<div class='brave-room-actions' aria-label='Room actions'>"
            + roomView.room_actions.map(function (action) {
                if (!action || (!action.command && !action.picker)) {
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
                + "<span>Activity</span>"
                + "<button type='button' class='brave-room-log__jump' data-brave-activity-scroll='rail' aria-label='Activity is at the latest line' disabled>0</button>"
                + "</div>"
                + "<div class='brave-room-log brave-room-log--rail'>"
                + "<div class='brave-room-log__body brave-room-log__body--rail' role='log' aria-live='polite' aria-relevant='additions text'></div>"
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
        if (!options.skipCombatTransition && pendingCombatTransitionViewData) {
            if (viewData.variant === "combat") {
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
        if (viewData.variant !== "combat") {
            clearDeferredCombatViewRender();
            pendingCombatResultViewData = null;
            pendingCombatPanelData = null;
        }
        syncInputContextForView(viewData);
        if (!preserveCombatPickerOnViewRefresh(viewData)) {
            clearPickerSheet();
        }

        var preserveRail = !!(viewData.layout === "explore" || viewData.preserve_rail);
        var stickyView = !!viewData.sticky;
        var isCombatView = viewData.variant === "combat";
        var enteringCombat = !!(isCombatView && (!currentViewData || currentViewData.variant !== "combat"));
        var variantClass = viewData.variant ? " brave-view--" + escapeHtml(viewData.variant) : "";
        var toneClass = viewData.tone ? " brave-view--tone-" + escapeHtml(viewData.tone) : "";
        if (!options.skipCombatTransition && enteringCombat && startCombatTransition(viewData)) {
            return;
        }
        if (isCombatView) {
            combatViewTransitionActive = true;
        }
        applyReactiveState(viewData.reactive || {});

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
                    var interactive = hasBrowserInteraction(entry);
                    if (interactive) {
                        rowClass += " brave-click brave-click--row";
                    }
                    var hasInlineActions = !!(entry && Array.isArray(entry.actions) && entry.actions.length);
                    if (interactive && hasInlineActions) {
                        rowClass += " brave-view__list-item--with-actions";
                        return (
                            "<li class='brave-view__list-row'>"
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
                            "<li class='brave-view__list-row'>"
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
                        "<li class='" + rowClass + "'>"
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
            if (!isMobileViewport() || viewData.variant !== "room") {
                return "";
            }
            return buildMobileRoomUtilityMarkup();
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
                    var lines = [];
                    if (entry && Array.isArray(entry.lines)) {
                        lines = lines.concat(entry.lines);
                    }
                    if (entry && entry.summary) {
                        lines.push(entry.summary);
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
                    var combatStateAttr = "";
                    if (entry && Array.isArray(entry.combat_state) && entry.combat_state.length) {
                        combatStateAttr = " data-combat-state='" + escapeHtml(entry.combat_state.join(" ")) + "'";
                    }
                    var combatRefAttr = "";
                    if (entry && entry.entry_ref) {
                        combatRefAttr = " data-entry-ref='" + escapeHtml(entry.entry_ref) + "'";
                    }
                    var hasInlineActions = !!(entry && Array.isArray(entry.actions) && entry.actions.length);
                    var useButtonRoot = hasBrowserInteraction(entry) && !hasInlineActions;
                    var tagName = useButtonRoot ? "button" : "article";
                    var extraAttrs = useButtonRoot ? " type='button'" : "";
                    if (useButtonRoot) {
                        rowClass += " brave-view__entry--button";
                    }
                    return (
                        "<" + tagName + " class='" + rowClass + "'"
                        + extraAttrs
                        + combatStateAttr
                        + combatRefAttr
                        + commandAttrs(entry)
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
                        + (lines.length
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
                            : "")
                        + renderInlineActions(entry && entry.actions)
                        + "</" + tagName + ">"
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
                    var aria = entry && (entry.aria_label || entry.label)
                        ? " aria-label='" + escapeHtml(entry.aria_label || entry.label) + "'"
                        : "";
                    return (
                        "<button type='button' class='brave-view__action brave-click" + toneClass + iconOnlyClass + "'"
                        + commandAttrs(entry, false)
                        + aria
                        + ">"
                        + icon(entry && entry.icon ? entry.icon : "chevron_right", "brave-view__action-icon")
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
            var mapMarkup = viewData.micromap ? renderMicromapMarkup(viewData.micromap) : "";
            return (
                "<div class='brave-view__micromap brave-click' data-brave-command='map' title='Open map' role='button' tabindex='0' aria-label='Open map'>"
                + mapMarkup
                + "</div>"
            );
        };

        var viewMarkup =
            "<div class='brave-view" + variantClass + toneClass + "'>"
            + "<div class='brave-view__hero'>"
            + (viewData.wordmark ? "<div class='brave-view__wordmark' aria-label='" + escapeHtml(viewData.wordmark) + "'><span class='brave-view__wordmark-text'>" + escapeHtml(viewData.wordmark) + "</span></div>" : "")
            + (((viewData.eyebrow_icon || viewData.eyebrow) || (!isMobileViewport() && isRoomLikeView(viewData)))
                ? "<div class='brave-view__hero-topbar'>"
                    + ((viewData.eyebrow_icon || viewData.eyebrow)
                        ? "<div class='brave-view__eyebrow'>"
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
            + (viewData.subtitle ? "<div class='brave-view__subtitle'>" + escapeHtml(viewData.subtitle) + "</div>" : "")
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
                setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

                var stickyContainer = mwin.children(".brave-sticky-view");
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
            clearTextOutput({ preserveCombatTransition: !!options.skipCombatTransition });
            if (!preserveRail) {
                clearSceneRail();
            }
            setMainViewMode(!preserveRail);
            setStickyViewMode(false);
            suppressNextLookText = !!(viewData.variant === "room" || viewData.layout === "explore");
            currentViewData = viewData;
            setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

            mwin.html(viewMarkup);
            if (isRoomLikeView(viewData)) {
                ensureRoomActivityLog();
                claimRoomActivityEntries();
                renderVicinityPanel(viewData);
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
            focusViewAutofocusField();
            resetAllScrollPositions();
        };

        applyStandardMarkup();
    };

    var clearMobileNavDock = function () {
        var dock = document.getElementById("mobile-nav-dock");
        if (dock) {
            dock.innerHTML = "";
        }
        if (document.body) {
            document.body.style.removeProperty("--brave-mobile-dock-clearance");
        }
        document.body.classList.remove("brave-mobile-nav-active");
        document.body.classList.remove("brave-mobile-command-dock-active");
        clearMobileUtilitySheet();
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
        if (confirmText && !window.confirm(confirmText)) {
            return;
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
        plugin_handler.onSend(command);
    };

    var focusViewAutofocusField = function () {
        var field = document.querySelector(".brave-view [data-brave-autofocus='1']");
        if (!field || typeof field.focus !== "function") {
            return;
        }
        window.setTimeout(function () {
            field.focus();
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
            var target = event.target.closest("[data-brave-command], [data-brave-prefill], [data-brave-picker], [data-brave-connection-screen]");
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

        document.addEventListener("submit", function (event) {
            var form = event.target.closest("[data-brave-form='1']");
            if (!form) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            submitBrowserForm(form);
        }, true);

        document.addEventListener("pointerdown", function (event) {
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
        var selectedSize = Number.isFinite(parsed) && parsed >= 0.8 && parsed <= 1.6 ? parsed.toFixed(1) : preset.size;

        document.body.setAttribute("data-brave-theme", selected);
        document.body.setAttribute("data-brave-font", selectedFont);
        document.documentElement.style.setProperty("--brave-font-size-scale", selectedSize);
        pulseBodyClass("brave-theme-shift", 320);
        if (window.localStorage) {
            window.localStorage.setItem(THEME_STORAGE_KEY, selected);
            window.localStorage.removeItem(LEGACY_FONT_STORAGE_KEY);
            window.localStorage.removeItem(LEGACY_SIZE_STORAGE_KEY);
        }
    };

    var clearTextOutput = function (options) {
        options = options || {};
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
        currentViewData = null;
        syncInputContextForView(null);
        clearPickerSheet();
        $("#messagewindow").empty();
        $(".prompt").empty().css({ height: "" });
        clearMobileNavDock();
        resetAllScrollPositions();
    };

    var shouldLogRoomActivity = function (rawText, cls, kwargs) {
        var text = typeof rawText === "string" ? rawText.trim() : "";
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
        return true;
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
                || ((kwargs && kwargs.type === "look") && !isRoomLikeView(currentViewData)))
        ) {
            clearTextOutput();
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
                mwin.append("<div class='" + cls + "'>" + rawText + "</div>");
                claimRoomActivityEntries();
                ensureRoomActivityLog();
            }
            return true;
        }
        var displayHtml = combatFx ? combatFx.html : rawText;
        appendTarget.append("<div class='" + cls + "'>" + displayHtml + "</div>");
        if (shouldRouteToCombatLog) {
            var appended = appendTarget.children().last().get(0);
            if (appended && combatFx && combatFx.events.length) {
                appended.dataset.braveFx = JSON.stringify(combatFx.events);
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
            if (isCombatUiActive()) {
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
            handleCombatFxEvent(getOobPayload(args, kwargs, "brave_combat_fx", {}) || {});
            return true;
        }

        if (cmdname === "brave_notice") {
            renderBrowserNotice(getOobPayload(args, kwargs, "brave_notice", {}) || {});
            return true;
        }

        if (cmdname === "brave_clear") {
            if (isCombatUiActive()) {
                return true;
            }
            clearTextOutput();
            clearSceneRail();
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
            teardownArcadeMode();
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
        var storedTheme = window.localStorage ? window.localStorage.getItem(THEME_STORAGE_KEY) : null;
        applyTheme(storedTheme || "hearth");
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
