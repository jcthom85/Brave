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
    var reactiveTimers = {};
    var currentViewData = null;
    var currentSceneData = null;
    var currentMapText = "";
    var currentArcadeState = null;
    var currentMobileUtilityTab = null;
    var currentCombatActionTab = "abilities";
    var currentMobileSwipe = null;
    var currentPickerData = null;
    var currentNoticeTimer = null;
    var currentConnectionScreen = "menu";
    var suppressBrowserClickUntil = 0;
    var ENABLE_ROOM_SWIPE_NAV = false;

    var isMobileViewport = function () {
        return !!(window.matchMedia && window.matchMedia("(max-width: 900px)").matches);
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
        var nextContext = "play";
        if (
            viewData
            && (
                viewData.variant === "connection"
                || viewData.variant === "chargen"
                || (viewData.reactive && viewData.reactive.scene === "account")
            )
        ) {
            nextContext = "command";
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

    var getCurrentRoomView = function () {
        if (!currentViewData || typeof currentViewData !== "object") {
            return null;
        }
        if (currentViewData.layout === "explore" || currentViewData.variant === "room") {
            return currentViewData;
        }
        return null;
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
            + (currentMapText
                ? "<pre class='brave-view__mobile-map-pre'>" + escapeHtml(currentMapText) + "</pre>"
                : "<div class='brave-view__mobile-map-placeholder'>" + icon("explore") + "<span>Open map</span></div>")
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

    var buildMobileUtilityButton = function (key, label, iconName, active) {
        var activeClass = active ? " brave-mobile-tools__button--active" : "";
        return (
            "<button type='button' class='brave-mobile-tools__button" + activeClass + "' data-brave-mobile-panel='" + escapeHtml(key) + "'>"
            + icon(iconName, "brave-mobile-tools__button-icon")
            + "<span>" + escapeHtml(label) + "</span>"
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

        if (tab === "menu") {
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
            "<div class='brave-mobile-sheet__panel'>"
            + buildMobileSheetTabsMarkup()
            + "<div class='brave-mobile-sheet__body'>"
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
    };

    var clearPickerSheet = function () {
        var host = document.getElementById("brave-picker-sheet");
        currentPickerData = null;
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
        if (!host) {
            return;
        }
        if (!pickerData || (!pickerOptions.length && !pickerBody.length)) {
            clearPickerSheet();
            return;
        }

        host.innerHTML =
            "<div class='brave-picker-sheet__backdrop' data-brave-picker-close='1'></div>"
            + "<div class='brave-picker-sheet__panel' role='dialog' aria-modal='true' aria-label='" + escapeHtml(pickerData.title || "Details") + "'>"
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
        renderPickerSheet();
        return true;
    };

    var openPickerFromTarget = function (target) {
        if (!target || !target.hasAttribute("data-brave-picker")) {
            return false;
        }
        try {
            return openPickerSheet(JSON.parse(target.getAttribute("data-brave-picker")));
        } catch (error) {
            return false;
        }
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

    var renderDesktopToolbar = function () {
        var toolbar = document.getElementById("toolbar");
        var show = !!(
            toolbar
            && !isMobileViewport()
            && currentViewData
            && currentViewData.variant
            && currentViewData.variant !== "connection"
            && currentViewData.variant !== "chargen"
            && currentViewData.variant !== "account"
        );
        if (!toolbar) {
            return;
        }
        toolbar.innerHTML = show
            ? "<div class='brave-toolbar'><button type='button' class='brave-toolbar__button brave-click' data-brave-command='more' title='more'>MENU</button></div>"
            : "";
        toolbar.setAttribute("aria-hidden", show ? "false" : "true");
    };

    var renderMap = function (mapText) {
        var overlay = document.getElementById("minimap-overlay");
        var micromaps = document.querySelectorAll(".brave-view__micromap");
        var raw = typeof mapText === "string" ? mapText : "";
        currentMapText = raw.replace(/\n+$/, "");
        if (overlay) {
            overlay.textContent = currentMapText;
        }
        if (micromaps.length) {
            micromaps.forEach(function (micromap) {
                micromap.textContent = currentMapText;
                micromap.setAttribute("aria-hidden", String(!currentMapText.trim()));
            });
        }
        syncSceneRailLayout();
        syncMobileShell();
    };

    var clearMicromap = function () {
        var micromaps = document.querySelectorAll(".brave-view__micromap");
        micromaps.forEach(function (micromap) {
            micromap.textContent = "";
            micromap.setAttribute("aria-hidden", "true");
        });
    };

    var syncSceneRailLayout = function () {
        var rail = document.getElementById("scene-rail");
        var card = document.getElementById("scene-card");
        var packPanel = document.getElementById("scene-pack-panel");
        var mapPanel = document.querySelector(".scene-rail__panel--map");
        var overlay = document.getElementById("minimap-overlay");
        if (!rail) {
            return;
        }

        var hasCard = !!(card && card.textContent && card.textContent.trim());
        var hasPack = !!(packPanel && packPanel.textContent && packPanel.textContent.trim());
        var hasMap = !!(overlay && overlay.textContent && overlay.textContent.trim());
        if (window.matchMedia && window.matchMedia("(max-width: 1099px)").matches) {
            hasCard = false;
        }

        if (mapPanel) {
            mapPanel.classList.toggle("scene-rail__panel--hidden", !hasMap);
        }
        if (packPanel) {
            packPanel.classList.toggle("scene-rail__panel--hidden", !hasPack);
        }

        rail.classList.toggle("scene-rail--map-hidden", !hasMap);
        rail.classList.toggle("scene-rail--pack-hidden", !hasPack);
        rail.classList.toggle("scene-rail--card-hidden", !hasCard);
        rail.classList.toggle("scene-rail--detail-hidden", !hasCard && !hasPack);
        rail.classList.toggle("scene-rail--empty", !hasCard && !hasPack && !hasMap);
    };

    var escapeHtml = function (value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    };

    var icon = function (name, extraClass) {
        var classes = "material-symbols-outlined";
        if (extraClass) {
            classes += " " + extraClass;
        }
        return "<span class='" + classes + "' aria-hidden='true'>" + escapeHtml(name) + "</span>";
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
        var inputPlugin = getDefaultInPlugin();
        if (inputPlugin && typeof inputPlugin.setInputValue === "function") {
            inputPlugin.setInputValue(value || "");
            return;
        }
        var inputfield = getCommandInput();
        if (!inputfield.length) {
            return;
        }
        inputfield.focus();
        inputfield.val(value || "");
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
                    + icon(entry && entry.icon ? entry.icon : "chevron_right", "brave-view__mini-action-icon")
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
        document.body.classList.remove("brave-tone-shift", "brave-scene-shift", "brave-scene-combat-enter");
    };

    var clearStickyView = function () {
        var mwin = $("#messagewindow");
        if (!mwin.length) {
            setStickyViewMode(false);
            return;
        }
        mwin.children(".brave-sticky-view").remove();
        mwin.children(".brave-combat-log").remove();
        setStickyViewMode(false);
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
                + "<div class='brave-combat-log__head'>Battle Feed</div>"
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
                log.prepend("<div class='brave-combat-log__head'>Battle Feed</div>");
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
            card.classList.remove("scene-card--clickable", "brave-click");
        }
        currentSceneData = null;
        syncSceneRailLayout();
        syncMobileShell();
    };

    var clearSceneRail = function () {
        var overlay = document.getElementById("minimap-overlay");
        if (overlay) {
            overlay.textContent = "";
        }
        currentMapText = "";
        clearMicromap();
        clearPackPanel();
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

    var renderStructuredCard = function (card, panelData) {
        if (!card) {
            return;
        }

        card.removeAttribute("data-brave-command");
        card.removeAttribute("data-brave-confirm");
        card.removeAttribute("title");
        card.removeAttribute("role");
        card.removeAttribute("tabindex");
        card.classList.remove("scene-card--clickable", "brave-click");

        if (!panelData || typeof panelData !== "object") {
            clearSceneCard();
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
            return (
                "<li class='scene-card__item'>"
                + lead
                + "<span class='scene-card__item-body'>"
                + "<span class='scene-card__text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
                + (entry && entry.meta ? "<span class='scene-card__item-meta'>" + escapeHtml(entry.meta) + "</span>" : "")
                + meterMarkup
                + "</span>"
                + "</li>"
            );
        };

        var renderListSection = function (label, iconName, items, formatter) {
            if (!Array.isArray(items) || !items.length) {
                return "";
            }
            return (
                "<section class='scene-card__section'>"
                + "<div class='scene-card__label'>"
                + icon(iconName, "scene-card__section-icon")
                + "<span>" + escapeHtml(label) + "</span>"
                + "</div>"
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

        card.innerHTML =
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
            + (chips.length ? "<div class='scene-card__meta'>" + chips.map(renderChip).join("") + "</div>" : "")
            + renderedSections.join("");
    };

    var renderPackPanel = function () {
        var panel = document.getElementById("scene-pack-panel");
        if (!panel) {
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
            + "<div class='scene-card__eyebrow scene-pack-panel__title'><span class='material-symbols-outlined scene-card__eyebrow-icon scene-pack-panel__title-icon' aria-hidden='true'>backpack</span><span>Pack</span></div>"
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
                return { text: entry, icon: "radio_button_unchecked" };
            })
            : [];

        renderPanelCard({
            eyebrow: "Tracked Quest",
            eyebrow_icon: "flag",
            title: tracked.title || "",
            title_icon: "assignment",
            chips: tracked.giver ? [{ label: tracked.giver, icon: "person_pin", tone: "muted" }] : [],
            hide_empty_state: true,
            sections: objectiveItems.length ? [{
                label: "Objectives",
                icon: "checklist",
                items: objectiveItems,
            }] : [],
        });

        var card = document.getElementById("scene-card");
        if (card) {
            card.setAttribute("data-brave-command", "quests");
            card.setAttribute("title", "quests");
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", "0");
            card.classList.add("scene-card--clickable", "brave-click");
        }
        syncMobileShell();
    };

    var renderMainView = function (viewData) {
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
            clearTextOutput();
            clearSceneCard();
            return;
        }
        syncInputContextForView(viewData);
        clearPickerSheet();

        var preserveRail = !!(viewData.layout === "explore" || viewData.preserve_rail);
        var stickyView = !!viewData.sticky;
        var variantClass = viewData.variant ? " brave-view--" + escapeHtml(viewData.variant) : "";
        var toneClass = viewData.tone ? " brave-view--tone-" + escapeHtml(viewData.tone) : "";
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
                    return (
                        "<div class='brave-view__meter" + toneClass + "'>"
                        + "<div class='brave-view__meter-head'>"
                        + "<span class='brave-view__meter-label'>" + escapeHtml(meter && meter.label ? meter.label : "") + "</span>"
                        + "<span class='brave-view__meter-value'>" + escapeHtml(meter && meter.value ? meter.value : "") + "</span>"
                        + "</div>"
                        + "<div class='brave-view__meter-track'><span class='brave-view__meter-fill' style='width: " + percent + "%;'></span></div>"
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
                    if (entry && entry.badge) {
                        lead = "<span class='brave-view__badge'>" + escapeHtml(entry.badge) + "</span>";
                    } else {
                        lead = "<span class='brave-view__bullet'>"
                            + icon(entry && entry.icon ? entry.icon : "chevron_right", "brave-view__bullet-icon")
                            + "</span>";
                    }
                    var rowClass = "brave-view__list-item";
                    var interactive = hasBrowserInteraction(entry);
                    if (interactive) {
                        rowClass += " brave-click brave-click--row";
                    }
                    var hasInlineActions = !!(entry && Array.isArray(entry.actions) && entry.actions.length);
                    if (interactive && hasInlineActions) {
                        return (
                            "<li class='brave-view__list-row'>"
                            + "<div class='" + rowClass + "'>"
                            + "<button type='button' class='brave-view__list-primary brave-click brave-click--row'"
                            + commandAttrs(entry, false)
                            + ">"
                            + "<div class='brave-view__list-main'>"
                            + lead
                            + "<span class='brave-view__list-text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
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
                            + "<span class='brave-view__list-text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
                            + "</div>"
                            + "</button>"
                            + "</li>"
                        );
                    }
                    return (
                        "<li class='" + rowClass + "'>"
                        + "<div class='brave-view__list-main'>"
                        + lead
                        + "<span class='brave-view__list-text'>" + escapeHtml(entry && entry.text ? entry.text : "") + "</span>"
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

        var renderPre = function (section) {
            var toneClass = section && section.tone ? " brave-view__pre--" + escapeHtml(section.tone) : "";
            return "<pre class='brave-view__pre" + toneClass + "'>" + escapeHtml(section && section.text ? section.text : "") + "</pre>";
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
                    if (entry && entry.badge) {
                        lead = "<span class='brave-view__entry-badge'>" + escapeHtml(entry.badge) + "</span>";
                    } else {
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
                    if (hasBrowserInteraction(entry)) {
                        rowClass += " brave-click brave-click--row";
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
                        + commandAttrs(entry)
                        + ">"
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
                + icon(entry && entry.icon ? entry.icon : "arrow_back", "brave-view__action-icon")
                + "<span>" + escapeHtml(entry && entry.text ? entry.text : entry && entry.label ? entry.label : "Back") + "</span>"
                + "</button>"
            );
        };

        var viewMarkup =
            "<div class='brave-view" + variantClass + toneClass + "'>"
            + "<div class='brave-view__hero'>"
            + (viewData.wordmark ? "<div class='brave-view__wordmark' aria-label='" + escapeHtml(viewData.wordmark) + "'><span class='brave-view__wordmark-text'>" + escapeHtml(viewData.wordmark) + "</span></div>" : "")
            + ((viewData.eyebrow_icon || viewData.eyebrow)
                ? "<div class='brave-view__eyebrow'>"
                    + (viewData.eyebrow_icon ? icon(viewData.eyebrow_icon, "brave-view__eyebrow-icon") : "")
                    + (viewData.eyebrow ? "<span>" + escapeHtml(viewData.eyebrow) + "</span>" : "")
                    + "</div>"
                : "")
            + (viewData.variant === "room" ? "<div class='brave-view__micromap' aria-hidden='true'></div>" : "")
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
            + (Array.isArray(viewData.sections) ? viewData.sections.map(renderSection).join("") : "")
            + "</div>"
            + "</div>";

        if (
            stickyView
            && viewData.variant === "combat"
            && (!currentViewData || currentViewData.variant !== "combat")
        ) {
            clearTextOutput();
        }

        if (stickyView) {
            if (!preserveRail) {
                clearSceneRail();
            }
            setMainViewMode(!preserveRail);
            setStickyViewMode(true);
            suppressNextLookText = false;
            currentViewData = viewData;
            setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

            var stickyContainer = mwin.children(".brave-sticky-view");
            if (stickyContainer.length) {
                stickyContainer.html(viewMarkup);
            } else {
                mwin.prepend("<div class='brave-sticky-view'>" + viewMarkup + "</div>");
            }
            if (currentMapText) {
                renderMap(currentMapText);
            }
            if (viewData.variant === "combat") {
                ensureCombatLog();
            }
            renderPackPanel();
            renderDesktopToolbar();
            syncMobileShell();
            focusViewAutofocusField();
            return;
        }

        clearTextOutput();
        if (!preserveRail) {
            clearSceneRail();
        }
        setMainViewMode(!preserveRail);
        setStickyViewMode(false);
        suppressNextLookText = !!(viewData.variant === "room" || viewData.layout === "explore");
        currentViewData = viewData;
        setBodyState("view", viewData && viewData.variant ? viewData.variant : "");

        mwin.html(viewMarkup);
        if (currentMapText) {
            renderMap(currentMapText);
        }
        renderPackPanel();
        renderDesktopToolbar();
        syncMobileShell();
        focusViewAutofocusField();
        resetAllScrollPositions();
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

        if (currentViewData && currentViewData.variant === "combat") {
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
                    if (typeof submitForm.requestSubmit === "function") {
                        submitForm.requestSubmit();
                    } else {
                        submitForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
                    }
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
                return;
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
                return;
            }
            sendBrowserCommand(command);
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
                + ".brave-view__mini-action[data-brave-connection-screen]"
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
            if (event.key === "Escape" && currentPickerData) {
                clearPickerSheet();
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            if (event.key === "Escape" && document.body.classList.contains("brave-notice-active")) {
                clearBrowserNotice();
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

    var clearTextOutput = function () {
        teardownArcadeMode();
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
        if (
            ((document.body.classList.contains("brave-mainview-active")
                && !document.body.classList.contains("brave-sticky-view-active"))
                || (kwargs && kwargs.type === "look"))
        ) {
            clearTextOutput();
        }
        if (
            currentViewData
            && currentViewData.variant === "combat"
        ) {
            appendTarget = ensureCombatLog() || mwin;
        }
        appendTarget.append("<div class='" + cls + "'>" + rawText + "</div>");
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
            var mapText = "";
            if (Array.isArray(args) && typeof args[0] === "string") {
                mapText = args[0];
            } else if (kwargs && typeof kwargs.mapdata === "string") {
                mapText = kwargs.mapdata;
            }
            renderMap(mapText);
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
            renderSceneCard(kwargs || {});
            return true;
        }

        if (cmdname === "brave_view") {
            renderMainView(kwargs || {});
            return true;
        }

        if (cmdname === "brave_arcade") {
            startArcadeMode(kwargs || {});
            return true;
        }

        if (cmdname === "brave_panel") {
            renderPanelCard(kwargs || {});
            return true;
        }

        if (cmdname === "brave_notice") {
            renderBrowserNotice(kwargs || {});
            return true;
        }

        if (cmdname === "brave_clear") {
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
            resetToConnectionView(kwargs && typeof kwargs.screen === "string" ? kwargs.screen : "menu");
            return true;
        }

        if (cmdname === "brave_combat_done") {
            clearStickyView();
            return true;
        }

        if (cmdname === "brave_arcade_done") {
            teardownArcadeMode();
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
    };
})();
plugin_handler.add("defaultout", defaultout_plugin);
