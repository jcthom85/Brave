(function () {
    "use strict";

    var SETTINGS_KEY = "brave.webclient.audio";
    var DEFAULT_SETTINGS = {
        enabled: true,
        muted: false,
        reduce_repetition: true,
        master: 0.9,
        ambience: 0.55,
        music: 0.45,
        sfx: 0.8
    };
    var TITLE_MUSIC_CUE_ID = "music.title";
    var TITLE_MUSIC_FALLBACK_CUE = {
        bus: "music",
        loop: true,
        gain: 0.58,
        fade_in_sec: 1.6,
        fade_out_sec: 1.1,
        files: [
            "music/elevenlabs_tests/title_test.mp3"
        ]
    };
    var FALLBACK_MANIFEST = {
        version: 1,
        buses: {
            master: { default_volume: 0.9 },
            ambience: { default_volume: 0.55 },
            music: { default_volume: 0.45 },
            sfx: { default_volume: 0.8 }
        },
        cues: {
            "music.explore.safe": {
                bus: "music",
                loop: true,
                fade_in_sec: 1.5,
                fade_out_sec: 0.9,
                voices: [
                    { waveform: "triangle", frequency: 220, gain: 0.02, lfo_rate: 0.08, lfo_depth: 0.08 }
                ]
            },
            "sfx.ui.click": {
                bus: "sfx",
                duration_sec: 0.09,
                cooldown_ms: 45,
                voices: [
                    { waveform: "square", frequency: 760, gain: 0.025, attack_sec: 0.003, release_sec: 0.07 }
                ]
            }
        }
    };
    var BUS_NAMES = ["master", "ambience", "music", "sfx"];
    var manifestUrl = "";
    var manifestBaseUrl = "";
    var context = null;
    var masterGain = null;
    var busGains = {};
    var manifest = null;
    var audioBufferCache = {};
    var audioBufferLoads = {};
    var mediaPlaybacks = [];
    var settings = loadSettings();
    var activeLayers = {
        ambience: null,
        music: null
    };
    var desiredLayers = {
        ambience: "",
        music: ""
    };
    var currentReactiveState = {};
    var lastCueAt = {};
    var layerTokens = {
        ambience: 0,
        music: 0
    };
    var unlockHandlersBound = false;
    var unlockInFlight = null;
    var manifestLoaded = false;
    var manifestLoadPromise = null;
    var contextUnlocked = false;
    var mobilePlaybackArmed = false;
    var initialized = false;
    var mobileTitleStartPendingCue = "";
    var lastPlayback = {
        cue: "",
        mode: "",
        error: ""
    };

    function cloneJsonSafe(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function clamp01(value, fallback) {
        var numeric = typeof value === "number" ? value : parseFloat(value);
        if (!isFinite(numeric)) {
            numeric = fallback;
        }
        return Math.max(0, Math.min(1, numeric));
    }

    function isProbablyMobile() {
        var userAgent = String((window.navigator && window.navigator.userAgent) || "").toLowerCase();
        if (/android|iphone|ipad|ipod|mobile/.test(userAgent)) {
            return true;
        }
        return !!(
            window.matchMedia
            && window.matchMedia("(hover: none), (pointer: coarse), (max-width: 820px)").matches
        );
    }

    function isContextRunning() {
        return !!(context && context.state === "running");
    }

    function canAttemptImmediatePlayback() {
        return contextUnlocked || mobilePlaybackArmed || isProbablyMobile() || isContextRunning();
    }

    function loadSettings() {
        var parsed = {};
        try {
            if (window.localStorage) {
                parsed = JSON.parse(window.localStorage.getItem(SETTINGS_KEY) || "{}") || {};
            }
        } catch (error) {
            parsed = {};
        }
        return {
            enabled: parsed.enabled !== false,
            muted: !!parsed.muted,
            reduce_repetition: parsed.reduce_repetition !== false,
            master: clamp01(parsed.master, DEFAULT_SETTINGS.master),
            ambience: clamp01(parsed.ambience, DEFAULT_SETTINGS.ambience),
            music: clamp01(parsed.music, DEFAULT_SETTINGS.music),
            sfx: clamp01(parsed.sfx, DEFAULT_SETTINGS.sfx)
        };
    }

    function persistSettings() {
        try {
            if (window.localStorage) {
                window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
            }
        } catch (error) {
            // Ignore storage failures.
        }
    }

    function dispatchStateChange() {
        if (!window.dispatchEvent || !window.CustomEvent) {
            return;
        }
        window.dispatchEvent(new window.CustomEvent("brave:audio-state", {
            detail: getState()
        }));
    }

    function getAudioContext() {
        var AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
            return null;
        }
        if (!context) {
            context = new AudioContextCtor();
            buildBusGraph();
        }
        return context;
    }

    function buildBusGraph() {
        var ctx = context;
        if (!ctx) {
            return;
        }
        masterGain = ctx.createGain();
        masterGain.connect(ctx.destination);
        BUS_NAMES.forEach(function (name) {
            if (name === "master") {
                return;
            }
            var gainNode = ctx.createGain();
            gainNode.connect(masterGain);
            busGains[name] = gainNode;
        });
        applyBusVolumes();
    }

    function getBusNode(busName) {
        var ctx = getAudioContext();
        if (!ctx) {
            return null;
        }
        if (busName === "master") {
            return masterGain;
        }
        return busGains[busName] || null;
    }

    function applyBusVolumes() {
        var ctx = context;
        if (!ctx || !masterGain) {
            mediaPlaybacks.forEach(function (playback) {
                if (playback && typeof playback.applyVolume === "function") {
                    playback.applyVolume();
                }
            });
            return;
        }
        var now = ctx.currentTime;
        masterGain.gain.cancelScheduledValues(now);
        masterGain.gain.setValueAtTime(settings.muted || !settings.enabled ? 0.0001 : Math.max(0.0001, settings.master), now);
        ["ambience", "music", "sfx"].forEach(function (busName) {
            var gainNode = busGains[busName];
            if (!gainNode) {
                return;
            }
            gainNode.gain.cancelScheduledValues(now);
            gainNode.gain.setValueAtTime(Math.max(0.0001, settings[busName]), now);
        });
        mediaPlaybacks.forEach(function (playback) {
            if (playback && typeof playback.applyVolume === "function") {
                playback.applyVolume();
            }
        });
    }

    function normalizeManifest(rawManifest) {
        var nextManifest = rawManifest && typeof rawManifest === "object" ? cloneJsonSafe(rawManifest) : cloneJsonSafe(FALLBACK_MANIFEST);
        if (!nextManifest.buses || typeof nextManifest.buses !== "object") {
            nextManifest.buses = cloneJsonSafe(FALLBACK_MANIFEST.buses);
        }
        if (!nextManifest.cues || typeof nextManifest.cues !== "object") {
            nextManifest.cues = cloneJsonSafe(FALLBACK_MANIFEST.cues);
        }
        return nextManifest;
    }

    function getManifestBase(nextUrl) {
        if (!nextUrl) {
            return window.location.href;
        }
        try {
            return new window.URL(".", new window.URL(nextUrl, window.location.href).href).href;
        } catch (error) {
            return window.location.href;
        }
    }

    function loadManifest(url) {
        manifestUrl = url || manifestUrl || "";
        manifestBaseUrl = getManifestBase(manifestUrl);
        if (!window.fetch || !manifestUrl) {
            manifest = normalizeManifest(FALLBACK_MANIFEST);
            manifestLoaded = true;
            dispatchStateChange();
            refreshLayerTargets();
            return Promise.resolve(manifest);
        }
        return window.fetch(manifestUrl, { credentials: "same-origin" })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Manifest request failed");
                }
                return response.json();
            })
            .catch(function () {
                return cloneJsonSafe(FALLBACK_MANIFEST);
            })
            .then(function (payload) {
                manifest = normalizeManifest(payload);
                manifestLoaded = true;
                dispatchStateChange();
                refreshLayerTargets();
                return manifest;
            });
    }

    function getCue(cueId) {
        if (!manifest || !manifest.cues) {
            return null;
        }
        return manifest.cues[cueId] || null;
    }

    function chooseAvailableCue(cueIds) {
        if (!Array.isArray(cueIds)) {
            return "";
        }
        for (var index = 0; index < cueIds.length; index += 1) {
            if (getCue(cueIds[index])) {
                return cueIds[index];
            }
        }
        return cueIds.length ? cueIds[cueIds.length - 1] : "";
    }

    function playFirstCue(cueIds, options) {
        var cueId = chooseAvailableCue(cueIds);
        if (!cueId) {
            return false;
        }
        return playCue(cueId, options);
    }

    function getCueCooldownMs(cueId, cue) {
        if (!settings.reduce_repetition) {
            return 0;
        }
        if (cue && typeof cue.cooldown_ms === "number") {
            return Math.max(0, cue.cooldown_ms);
        }
        return 0;
    }

    function shouldThrottleCue(cueId, cue, force) {
        if (!cueId || force) {
            return false;
        }
        var cooldownMs = getCueCooldownMs(cueId, cue);
        if (!cooldownMs) {
            return false;
        }
        var now = Date.now();
        if (lastCueAt[cueId] && (now - lastCueAt[cueId]) < cooldownMs) {
            return true;
        }
        lastCueAt[cueId] = now;
        return false;
    }

    function getCueDuration(cue) {
        if (cue && typeof cue.duration_sec === "number" && cue.duration_sec > 0) {
            return cue.duration_sec;
        }
        return 0.18;
    }

    function getCueEffectiveVolume(cue, busName) {
        if (!settings.enabled || settings.muted) {
            return 0;
        }
        var cueGain = Math.max(0, typeof cue.gain === "number" ? cue.gain : 1.0);
        var busVolume = busName === "master" ? settings.master : (settings[busName] || 0);
        return clamp01(settings.master * busVolume * cueGain, 0);
    }

    function resolveAssetUrl(assetPath) {
        if (!assetPath || typeof assetPath !== "string") {
            return "";
        }
        try {
            return new window.URL(assetPath, manifestBaseUrl || window.location.href).href;
        } catch (error) {
            return assetPath;
        }
    }

    function getCueFiles(cue) {
        if (!cue) {
            return [];
        }
        if (Array.isArray(cue.files)) {
            return cue.files.filter(function (entry) {
                return typeof entry === "string" && !!entry;
            });
        }
        if (typeof cue.file === "string" && cue.file) {
            return [cue.file];
        }
        return [];
    }

    function chooseCueAsset(cue) {
        var files = getCueFiles(cue);
        if (!files.length) {
            return "";
        }
        return files[0];
    }

    function decodeAudioBuffer(ctx, arrayBuffer) {
        return new Promise(function (resolve, reject) {
            var settled = false;
            function onResolve(buffer) {
                if (settled) {
                    return;
                }
                settled = true;
                resolve(buffer);
            }
            function onReject(error) {
                if (settled) {
                    return;
                }
                settled = true;
                reject(error);
            }
            try {
                var result = ctx.decodeAudioData(arrayBuffer, onResolve, onReject);
                if (result && typeof result.then === "function") {
                    result.then(onResolve).catch(onReject);
                }
            } catch (error) {
                reject(error);
            }
        });
    }

    function loadAudioBuffer(assetPath) {
        var resolvedUrl = resolveAssetUrl(assetPath);
        var ctx = getAudioContext();
        if (!ctx || !resolvedUrl || !window.fetch) {
            return Promise.resolve(null);
        }
        if (audioBufferCache[resolvedUrl]) {
            return Promise.resolve({
                assetPath: assetPath,
                resolvedUrl: resolvedUrl,
                buffer: audioBufferCache[resolvedUrl]
            });
        }
        if (audioBufferLoads[resolvedUrl]) {
            return audioBufferLoads[resolvedUrl];
        }
        audioBufferLoads[resolvedUrl] = window.fetch(resolvedUrl, { credentials: "same-origin" })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Audio request failed");
                }
                return response.arrayBuffer();
            })
            .then(function (arrayBuffer) {
                return decodeAudioBuffer(ctx, arrayBuffer);
            })
            .then(function (buffer) {
                audioBufferCache[resolvedUrl] = buffer;
                return {
                    assetPath: assetPath,
                    resolvedUrl: resolvedUrl,
                    buffer: buffer
                };
            })
            .catch(function () {
                lastPlayback.error = "decode/fetch failed for " + assetPath;
                return null;
            })
            .finally(function () {
                delete audioBufferLoads[resolvedUrl];
        });
        return audioBufferLoads[resolvedUrl];
    }

    function performUnlockPulse(ctx) {
        try {
            var buffer = ctx.createBuffer(1, 1, Math.max(22050, ctx.sampleRate || 44100));
            var source = ctx.createBufferSource();
            var gain = ctx.createGain();
            gain.gain.value = 0.0001;
            source.buffer = buffer;
            source.connect(gain);
            gain.connect(ctx.destination);
            source.start(0);
            source.stop(ctx.currentTime + 0.001);
            disconnectNodeLater(gain, 50);
        } catch (error) {
            // Ignore unlock pulse failures.
        }
    }

    function unregisterMediaPlayback(playback) {
        mediaPlaybacks = mediaPlaybacks.filter(function (entry) {
            return entry !== playback;
        });
    }

    function playMediaCue(cue, cueId, options) {
        options = options || {};
        var assetPath = options.assetPath || chooseCueAsset(cue);
        var resolvedUrl = resolveAssetUrl(assetPath);
        var busName = cue.bus || options.bus || "sfx";
        if (!resolvedUrl || typeof window.Audio !== "function") {
            return Promise.resolve(null);
        }
        return new Promise(function (resolve) {
            var audio = new window.Audio();
            var loop = !!cue.loop;
            var fadeInSec = Math.max(0.02, typeof cue.fade_in_sec === "number" ? cue.fade_in_sec : 0.04);
            var fadeOutSec = Math.max(0.03, typeof cue.fade_out_sec === "number" ? cue.fade_out_sec : 0.08);
            var durationSec = getCueDuration(cue);
            var stopped = false;
            var cleanupTimer = null;
            audio.preload = "auto";
            audio.src = resolvedUrl;
            audio.loop = loop;
            audio.playsInline = true;
            audio.setAttribute("playsinline", "playsinline");
            audio.volume = 0;
            var playback = {
                cueId: cueId,
                bus: busName,
                loop: loop,
                cue: cue,
                assetPath: assetPath,
                audio: audio,
                startedAt: Date.now(),
                applyVolume: function () {
                    var targetVolume = getCueEffectiveVolume(cue, busName);
                    audio.volume = clamp01(targetVolume, 0);
                },
                stop: function (fadeMs) {
                    if (stopped) {
                        return;
                    }
                    stopped = true;
                    var fadeSeconds = Math.max(0.04, (typeof fadeMs === "number" ? fadeMs : fadeOutSec * 1000) / 1000);
                    var startVolume = audio.volume;
                    var startedAt = Date.now();
                    var fadeInterval = window.setInterval(function () {
                        var progress = Math.min(1, (Date.now() - startedAt) / (fadeSeconds * 1000));
                        audio.volume = clamp01(startVolume * (1 - progress), 0);
                        if (progress >= 1) {
                            window.clearInterval(fadeInterval);
                            try {
                                audio.pause();
                                audio.src = "";
                            } catch (error) {
                                // Ignore pause/clear failures.
                            }
                            unregisterMediaPlayback(playback);
                        }
                    }, 30);
                }
            };
            audio.addEventListener("ended", function () {
                unregisterMediaPlayback(playback);
            });
            mediaPlaybacks.push(playback);
            audio.play().then(function () {
                lastPlayback.cue = cueId;
                lastPlayback.mode = "htmlaudio";
                lastPlayback.error = "";
                playback.applyVolume();
                if (!loop) {
                    cleanupTimer = window.setTimeout(function () {
                        playback.stop(fadeOutSec * 1000);
                    }, Math.max(120, (durationSec * 1000) - (fadeOutSec * 500)));
                }
                resolve(playback);
            }).catch(function () {
                lastPlayback.error = "htmlaudio play failed for " + cueId;
                if (cleanupTimer) {
                    window.clearTimeout(cleanupTimer);
                }
                unregisterMediaPlayback(playback);
                resolve(null);
            });
        });
    }

    function createVoiceChain(ctx, voice, output, startTime, durationSec, loop) {
        var oscillator = ctx.createOscillator();
        var voiceGain = ctx.createGain();
        var filter = null;
        var attackSec = Math.max(0.001, typeof voice.attack_sec === "number" ? voice.attack_sec : 0.01);
        var releaseSec = Math.max(0.01, typeof voice.release_sec === "number" ? voice.release_sec : 0.08);
        var peakGain = Math.max(0.0001, typeof voice.gain === "number" ? voice.gain : 0.02);
        var waveform = typeof voice.waveform === "string" ? voice.waveform : "sine";
        var baseFrequency = Math.max(20, typeof voice.frequency === "number" ? voice.frequency : 220);
        var lfo = null;
        var lfoGain = null;
        var frequencyLfo = null;
        var frequencyLfoGain = null;
        oscillator.type = waveform;
        oscillator.frequency.setValueAtTime(baseFrequency, startTime);
        if (typeof voice.detune === "number") {
            oscillator.detune.setValueAtTime(voice.detune, startTime);
        }
        if (voice.filter_type || voice.filter_frequency) {
            filter = ctx.createBiquadFilter();
            filter.type = typeof voice.filter_type === "string" ? voice.filter_type : "lowpass";
            filter.frequency.setValueAtTime(Math.max(40, typeof voice.filter_frequency === "number" ? voice.filter_frequency : 1200), startTime);
            oscillator.connect(filter);
            filter.connect(voiceGain);
        } else {
            oscillator.connect(voiceGain);
        }
        voiceGain.connect(output);
        voiceGain.gain.setValueAtTime(0.0001, startTime);
        voiceGain.gain.linearRampToValueAtTime(peakGain, startTime + attackSec);
        if (!loop) {
            var sustainUntil = Math.max(startTime + attackSec, startTime + Math.max(0.02, durationSec - releaseSec));
            voiceGain.gain.setValueAtTime(peakGain, sustainUntil);
            voiceGain.gain.exponentialRampToValueAtTime(0.0001, startTime + durationSec);
        }
        if (typeof voice.lfo_rate === "number" && typeof voice.lfo_depth === "number" && voice.lfo_depth > 0) {
            lfo = ctx.createOscillator();
            lfoGain = ctx.createGain();
            lfo.type = "sine";
            lfo.frequency.setValueAtTime(Math.max(0.01, voice.lfo_rate), startTime);
            lfoGain.gain.setValueAtTime(peakGain * voice.lfo_depth, startTime);
            lfo.connect(lfoGain);
            lfoGain.connect(voiceGain.gain);
            lfo.start(startTime);
            if (!loop) {
                lfo.stop(startTime + durationSec + 0.05);
            }
        }
        if (typeof voice.frequency_lfo_rate === "number" && typeof voice.frequency_lfo_depth === "number" && voice.frequency_lfo_depth > 0) {
            frequencyLfo = ctx.createOscillator();
            frequencyLfoGain = ctx.createGain();
            frequencyLfo.type = "sine";
            frequencyLfo.frequency.setValueAtTime(Math.max(0.01, voice.frequency_lfo_rate), startTime);
            frequencyLfoGain.gain.setValueAtTime(voice.frequency_lfo_depth, startTime);
            frequencyLfo.connect(frequencyLfoGain);
            frequencyLfoGain.connect(oscillator.frequency);
            frequencyLfo.start(startTime);
            if (!loop) {
                frequencyLfo.stop(startTime + durationSec + 0.05);
            }
        }
        oscillator.start(startTime);
        if (!loop) {
            oscillator.stop(startTime + durationSec + 0.05);
        }
        return {
            oscillator: oscillator,
            gainNode: voiceGain,
            filter: filter,
            lfo: lfo,
            lfoGain: lfoGain,
            frequencyLfo: frequencyLfo,
            frequencyLfoGain: frequencyLfoGain
        };
    }

    function disconnectNodeLater(node, delayMs) {
        window.setTimeout(function () {
            try {
                node.disconnect();
            } catch (error) {
                // Ignore disconnect errors.
            }
        }, Math.max(0, delayMs || 0));
    }

    function playSynthCue(cue, cueId, options) {
        options = options || {};
        if (!cue || !cue.voices || !cue.voices.length) {
            return null;
        }
        var ctx = getAudioContext();
        if (!ctx) {
            return null;
        }
        var busName = cue.bus || options.bus || "sfx";
        var busNode = getBusNode(busName);
        if (!busNode) {
            return null;
        }
        var durationSec = getCueDuration(cue);
        var loop = !!cue.loop;
        var fadeInSec = Math.max(0.02, typeof cue.fade_in_sec === "number" ? cue.fade_in_sec : 0.04);
        var fadeOutSec = Math.max(0.03, typeof cue.fade_out_sec === "number" ? cue.fade_out_sec : 0.08);
        var startTime = ctx.currentTime + 0.01;
        var outputGain = ctx.createGain();
        var voices = [];
        outputGain.connect(busNode);
        outputGain.gain.setValueAtTime(0.0001, startTime);
        outputGain.gain.linearRampToValueAtTime(1.0, startTime + fadeInSec);
        if (!loop) {
            var outputSustainUntil = Math.max(startTime + fadeInSec, startTime + Math.max(0.02, durationSec - fadeOutSec));
            outputGain.gain.setValueAtTime(1.0, outputSustainUntil);
            outputGain.gain.exponentialRampToValueAtTime(0.0001, startTime + durationSec);
        }
        cue.voices.forEach(function (voice) {
            voices.push(createVoiceChain(ctx, voice, outputGain, startTime, durationSec, loop));
        });
        var playback = {
            cueId: cueId,
            bus: busName,
            loop: loop,
            cue: cue,
            output: outputGain,
            voices: voices,
            startedAt: Date.now(),
            stop: function (fadeMs) {
                var fadeSeconds = Math.max(0.04, (typeof fadeMs === "number" ? fadeMs : fadeOutSec * 1000) / 1000);
                var stopAt = ctx.currentTime + fadeSeconds;
                outputGain.gain.cancelScheduledValues(ctx.currentTime);
                outputGain.gain.setValueAtTime(Math.max(0.0001, outputGain.gain.value || 0.0001), ctx.currentTime);
                outputGain.gain.exponentialRampToValueAtTime(0.0001, stopAt);
                voices.forEach(function (entry) {
                    try {
                        entry.oscillator.stop(stopAt + 0.05);
                    } catch (error) {
                        // Ignore duplicate-stop errors.
                    }
                    if (entry.lfo) {
                        try {
                            entry.lfo.stop(stopAt + 0.05);
                        } catch (error2) {
                            // Ignore duplicate-stop errors.
                        }
                    }
                    if (entry.frequencyLfo) {
                        try {
                            entry.frequencyLfo.stop(stopAt + 0.05);
                        } catch (error3) {
                            // Ignore duplicate-stop errors.
                        }
                    }
                });
                disconnectNodeLater(outputGain, (fadeSeconds * 1000) + 120);
            }
        };
        if (!loop) {
            disconnectNodeLater(outputGain, (durationSec * 1000) + 180);
        }
        return playback;
    }

    function playFileCue(cue, cueId, options) {
        options = options || {};
        var assetPath = options.assetPath || chooseCueAsset(cue);
        if (!assetPath) {
            return Promise.resolve(null);
        }
        var ctx = getAudioContext();
        if (!ctx) {
            return Promise.resolve(null);
        }
        var busName = cue.bus || options.bus || "sfx";
        var busNode = getBusNode(busName);
        if (!busNode) {
            return Promise.resolve(null);
        }
        return loadAudioBuffer(assetPath).then(function (loaded) {
            if (!loaded || !loaded.buffer) {
                return null;
            }
            var startTime = ctx.currentTime + 0.01;
            var loop = !!cue.loop;
            var fadeInSec = Math.max(0.02, typeof cue.fade_in_sec === "number" ? cue.fade_in_sec : 0.04);
            var fadeOutSec = Math.max(0.03, typeof cue.fade_out_sec === "number" ? cue.fade_out_sec : 0.08);
            var durationSec = loop ? loaded.buffer.duration : Math.max(0.03, getCueDuration(cue));
            var outputGain = ctx.createGain();
            var source = ctx.createBufferSource();
            var peakGain = Math.max(0.0001, typeof cue.gain === "number" ? cue.gain : 1.0);
            outputGain.connect(busNode);
            source.connect(outputGain);
            source.buffer = loaded.buffer;
            if (typeof cue.playback_rate === "number" && cue.playback_rate > 0) {
                source.playbackRate.setValueAtTime(cue.playback_rate, startTime);
            }
            source.loop = loop;
            if (loop && typeof cue.loop_start_sec === "number" && cue.loop_start_sec >= 0) {
                source.loopStart = cue.loop_start_sec;
            }
            if (loop && typeof cue.loop_end_sec === "number" && cue.loop_end_sec > 0) {
                source.loopEnd = cue.loop_end_sec;
            }
            outputGain.gain.setValueAtTime(0.0001, startTime);
            outputGain.gain.linearRampToValueAtTime(peakGain, startTime + fadeInSec);
            if (!loop) {
                var sustainUntil = Math.max(startTime + fadeInSec, startTime + Math.max(0.02, durationSec - fadeOutSec));
                outputGain.gain.setValueAtTime(peakGain, sustainUntil);
                outputGain.gain.exponentialRampToValueAtTime(0.0001, startTime + durationSec);
            }
            source.start(startTime);
            if (!loop) {
                source.stop(startTime + durationSec + 0.05);
            }
            var playback = {
                cueId: cueId,
                bus: busName,
                loop: loop,
                cue: cue,
                output: outputGain,
                source: source,
                assetPath: loaded.assetPath,
                startedAt: Date.now(),
                stop: function (fadeMs) {
                    var fadeSeconds = Math.max(0.04, (typeof fadeMs === "number" ? fadeMs : fadeOutSec * 1000) / 1000);
                    var stopAt = ctx.currentTime + fadeSeconds;
                    outputGain.gain.cancelScheduledValues(ctx.currentTime);
                    outputGain.gain.setValueAtTime(Math.max(0.0001, outputGain.gain.value || 0.0001), ctx.currentTime);
                    outputGain.gain.exponentialRampToValueAtTime(0.0001, stopAt);
                    try {
                        source.stop(stopAt + 0.05);
                    } catch (error) {
                        // Ignore duplicate-stop errors.
                    }
                    disconnectNodeLater(outputGain, (fadeSeconds * 1000) + 120);
                }
            };
            if (!loop) {
                disconnectNodeLater(outputGain, (durationSec * 1000) + 180);
            }
            lastPlayback.cue = cueId;
            lastPlayback.mode = "webaudio-file";
            lastPlayback.error = "";
            return playback;
        });
    }

    function playCueInternal(cueId, cue, options) {
        var cueFiles = getCueFiles(cue);
        if (cueFiles.length) {
            if (isProbablyMobile()) {
                return playMediaCue(cue, cueId, options).then(function (playback) {
                    return playback || playFileCue(cue, cueId, options).then(function (bufferPlayback) {
                        return bufferPlayback || playSynthCue(cue, cueId, options);
                    });
                });
            }
            return playFileCue(cue, cueId, options).then(function (playback) {
                return playback || playMediaCue(cue, cueId, options).then(function (mediaPlayback) {
                    return mediaPlayback || playSynthCue(cue, cueId, options);
                });
            });
        }
        var synthPlayback = playSynthCue(cue, cueId, options);
        if (synthPlayback) {
            lastPlayback.cue = cueId;
            lastPlayback.mode = "synth";
            lastPlayback.error = "";
        } else {
            lastPlayback.error = "no playback path for " + cueId;
        }
        return Promise.resolve(synthPlayback);
    }

    function startLayer(busName, cueId) {
        var cue = getCue(cueId);
        if (!cue || !cue.loop) {
            return Promise.resolve(null);
        }
        layerTokens[busName] = (layerTokens[busName] || 0) + 1;
        var token = layerTokens[busName];
        return playCueInternal(cueId, cue, { bus: busName, force: true, layer: true }).then(function (playback) {
            if (!playback) {
                return null;
            }
            if (token !== layerTokens[busName] || desiredLayers[busName] !== cueId) {
                playback.stop(60);
                return null;
            }
            activeLayers[busName] = playback;
            dispatchStateChange();
            return playback;
        });
    }

    function startMobileTitleLayer(cueId) {
        cueId = cueId || TITLE_MUSIC_CUE_ID;
        var cue = getCue(cueId) || (cueId === TITLE_MUSIC_CUE_ID ? TITLE_MUSIC_FALLBACK_CUE : null);
        if (!cue || !cue.loop || !isProbablyMobile()) {
            return Promise.resolve(null);
        }
        if (!manifestBaseUrl && window.BRAVE_AUDIO_MANIFEST_URL) {
            manifestBaseUrl = getManifestBase(window.BRAVE_AUDIO_MANIFEST_URL);
        }
        var active = activeLayers.music;
        if (active && active.cueId === cueId) {
            return Promise.resolve(active);
        }
        stopLayer("music", 120);
        layerTokens.music = (layerTokens.music || 0) + 1;
        var token = layerTokens.music;
        mobileTitleStartPendingCue = cueId;
        return playMediaCue(cue, cueId, { bus: "music", force: true, layer: true }).then(function (playback) {
            if (!playback) {
                if (token === layerTokens.music && mobileTitleStartPendingCue === cueId) {
                    mobileTitleStartPendingCue = "";
                    refreshLayerTargets();
                }
                return null;
            }
            if (token !== layerTokens.music || desiredLayers.music !== cueId) {
                if (mobileTitleStartPendingCue === cueId) {
                    mobileTitleStartPendingCue = "";
                }
                playback.stop(60);
                return null;
            }
            mobileTitleStartPendingCue = "";
            activeLayers.music = playback;
            dispatchStateChange();
            return playback;
        });
    }

    function stopLayer(busName, fadeMs) {
        layerTokens[busName] = (layerTokens[busName] || 0) + 1;
        var active = activeLayers[busName];
        if (!active) {
            if (busName === "music") {
                mobileTitleStartPendingCue = "";
            }
            return;
        }
        active.stop(fadeMs);
        activeLayers[busName] = null;
        if (busName === "music") {
            mobileTitleStartPendingCue = "";
        }
    }

    function refreshLayerTargets() {
        if (!initialized) {
            return;
        }
        if (!manifestLoaded || !settings.enabled) {
            stopLayer("ambience", 300);
            stopLayer("music", 300);
            return;
        }
        if (!canAttemptImmediatePlayback()) {
            return;
        }
        ["ambience", "music"].forEach(function (busName) {
            var desiredCueId = desiredLayers[busName] || "";
            var active = activeLayers[busName];
            if (active && active.cueId === desiredCueId) {
                return;
            }
            if (busName === "music" && mobileTitleStartPendingCue && mobileTitleStartPendingCue === desiredCueId) {
                return;
            }
            stopLayer(busName, 700);
            if (desiredCueId) {
                startLayer(busName, desiredCueId);
            }
        });
    }

    function chooseAmbienceCue(reactive) {
        var scene = String((reactive && reactive.scene) || "system").toLowerCase();
        var tone = String((reactive && reactive.world_tone) || "neutral").toLowerCase();
        var sourceId = String((reactive && reactive.source_id) || "").toLowerCase();
        if (
            scene !== "explore"
            && scene !== "travel"
            && scene !== "map"
            && scene !== "arcade"
            && scene !== "chapel"
        ) {
            return "";
        }
        if (sourceId.indexOf("rat_and_kettle_cellar") >= 0 || sourceId.indexOf("cellar") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.cellar", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("lantern_rest_inn") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.inn", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("chapel") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.chapel", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("ironroot_forge") >= 0 || sourceId.indexOf("forge") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.forge", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("hobbyists_wharf") >= 0 || sourceId.indexOf("wharf") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.wharf", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("observatory") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.observatory", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("menders_shed") >= 0 || sourceId.indexOf("mender") >= 0) {
            return chooseAvailableCue(["ambience.brambleford.mender", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("nexus_gate") >= 0) {
            return chooseAvailableCue(["ambience.portal", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("wayfarer") >= 0 || sourceId.indexOf("sparring") >= 0 || sourceId.indexOf("quartermaster") >= 0 || sourceId.indexOf("vermin_pens") >= 0) {
            return chooseAvailableCue(["ambience.wayfarers_yard", "ambience.brambleford"]);
        }
        if (sourceId.indexOf("brambleford_") >= 0) {
            return chooseAvailableCue(["ambience.brambleford"]);
        }
        if (sourceId.indexOf("fencebreaker_camp") >= 0) {
            return chooseAvailableCue(["ambience.goblin_road.camp", "ambience.goblinroad"]);
        }
        if (sourceId.indexOf("briar_glade") >= 0 || sourceId.indexOf("greymaw") >= 0) {
            return chooseAvailableCue(["ambience.whispering_woods.briar", "ambience.whisperingwoods"]);
        }
        if (sourceId.indexOf("whispering_woods") >= 0) {
            return chooseAvailableCue(["ambience.whisperingwoods"]);
        }
        if (sourceId.indexOf("boglight") >= 0 || sourceId.indexOf("miretooth") >= 0) {
            return chooseAvailableCue(["ambience.blackfen.boglight", "ambience.blackfen.reedflats"]);
        }
        if (sourceId.indexOf("blackfen") >= 0) {
            return chooseAvailableCue(["ambience.blackfen.reedflats"]);
        }
        if (sourceId.indexOf("barrow_circle") >= 0 || sourceId.indexOf("sunken_dais") >= 0) {
            return chooseAvailableCue(["ambience.old_barrow.circle", "ambience.oldbarrow"]);
        }
        if (sourceId.indexOf("old_barrow") >= 0) {
            return chooseAvailableCue(["ambience.oldbarrow"]);
        }
        if (sourceId.indexOf("sluice") >= 0 || sourceId.indexOf("sunken_lock") >= 0 || sourceId.indexOf("lamp_house") >= 0) {
            return chooseAvailableCue(["ambience.drowned_weir.sluice", "ambience.drowned_weir.causeway"]);
        }
        if (sourceId.indexOf("drowned_weir") >= 0) {
            return chooseAvailableCue(["ambience.drowned_weir.causeway"]);
        }
        if (sourceId.indexOf("blackreed_roost") >= 0 || sourceId.indexOf("archers_ledge") >= 0) {
            return chooseAvailableCue(["ambience.ruined_watchtower.roost", "ambience.ruined_watchtower.approach"]);
        }
        if (sourceId.indexOf("ruined_watchtower") >= 0) {
            return chooseAvailableCue(["ambience.ruined_watchtower.approach"]);
        }
        if (sourceId.indexOf("feast_hall") >= 0 || sourceId.indexOf("pot_kings_court") >= 0) {
            return chooseAvailableCue(["ambience.goblin_warrens.feast", "ambience.goblin_warrens.tunnel"]);
        }
        if (sourceId.indexOf("sludge_run") >= 0 || sourceId.indexOf("bone_midden") >= 0) {
            return chooseAvailableCue(["ambience.goblin_warrens.sludge", "ambience.goblin_warrens.tunnel"]);
        }
        if (sourceId.indexOf("goblin_warrens") >= 0) {
            return chooseAvailableCue(["ambience.goblin_warrens.tunnel"]);
        }
        if (sourceId.indexOf("relay_trench") >= 0 || sourceId.indexOf("scrapway") >= 0) {
            return chooseAvailableCue(["ambience.junkyard.relay", "ambience.junkyard.landing"]);
        }
        if (sourceId.indexOf("anchor_pit") >= 0 || sourceId.indexOf("crane_grave") >= 0) {
            return chooseAvailableCue(["ambience.junkyard.anchor_pit", "ambience.junkyard.landing"]);
        }
        if (sourceId.indexOf("junkyard") >= 0) {
            return chooseAvailableCue(["ambience.junkyard.landing"]);
        }
        if (tone === "brambleford") {
            return chooseAvailableCue(["ambience.brambleford"]);
        }
        if (tone === "wayfarersyard" || tone === "wayfarers_yard" || tone === "training") {
            return chooseAvailableCue(["ambience.wayfarers_yard", "ambience.brambleford"]);
        }
        if (tone === "goblinroad" || tone === "watchtower") {
            return chooseAvailableCue([
                tone === "watchtower" ? "ambience.ruined_watchtower.approach" : "ambience.goblinroad",
                "ambience.goblinroad"
            ]);
        }
        if (tone === "woods") {
            return chooseAvailableCue(["ambience.whispering_woods.briar", "ambience.whisperingwoods"]);
        }
        if (tone === "blackfen") {
            return chooseAvailableCue(["ambience.blackfen.reedflats", "ambience.whisperingwoods"]);
        }
        if (tone === "oldbarrow") {
            return chooseAvailableCue(["ambience.old_barrow.circle", "ambience.oldbarrow"]);
        }
        if (tone === "drownedweir") {
            return chooseAvailableCue(["ambience.drowned_weir.causeway", "ambience.oldbarrow"]);
        }
        if (tone === "warrens") {
            return chooseAvailableCue(["ambience.goblin_warrens.tunnel", "ambience.oldbarrow"]);
        }
        if (tone === "nexus" || tone === "portal" || tone === "junkyard") {
            return chooseAvailableCue([
                tone === "junkyard" ? "ambience.junkyard.landing" : "ambience.nexus_gate",
                "ambience.portal"
            ]);
        }
        return "ambience.brambleford";
    }

    function chooseMusicCue(reactive) {
        var scene = String((reactive && reactive.scene) || "system").toLowerCase();
        var tone = String((reactive && reactive.world_tone) || "neutral").toLowerCase();
        var danger = String((reactive && reactive.danger) || "").toLowerCase();
        var boss = !!(reactive && reactive.boss);
        if (scene === "victory") {
            return chooseAvailableCue(["music.victory"]);
        }
        if (scene === "combat") {
            return chooseAvailableCue([boss ? "music.combat.boss" : "music.combat.standard"]);
        }
        if (scene === "account" || scene === "chargen" || scene === "connection") {
            return chooseAvailableCue(["music.title"]);
        }
        if (tone === "nexus" || tone === "portal" || tone === "junkyard") {
            return chooseAvailableCue(["music.region.junkyard_planet", "music.portal"]);
        }
        if (tone === "goblinroad") {
            return chooseAvailableCue(["music.region.goblin_road", "music.explore.danger"]);
        }
        if (tone === "oldbarrow") {
            return chooseAvailableCue(["music.region.old_barrow", "music.explore.danger"]);
        }
        if (tone === "woods") {
            return chooseAvailableCue(["music.region.whispering_woods", "music.explore.danger"]);
        }
        if (tone === "blackfen") {
            return chooseAvailableCue(["music.region.blackfen", "music.explore.danger"]);
        }
        if (tone === "drownedweir") {
            return chooseAvailableCue(["music.region.drowned_weir", "music.explore.danger"]);
        }
        if (tone === "watchtower") {
            return chooseAvailableCue(["music.region.ruined_watchtower", "music.explore.danger"]);
        }
        if (tone === "warrens") {
            return chooseAvailableCue(["music.region.goblin_warrens", "music.explore.danger"]);
        }
        if (danger === "danger" || danger === "combat") {
            return chooseAvailableCue(["music.explore.danger"]);
        }
        return "music.explore.safe";
    }

    function isTitleExperienceScene(scene) {
        scene = String(scene || "").toLowerCase();
        return scene === "account" || scene === "chargen" || scene === "connection";
    }

    function setReactiveState(reactive) {
        var previousState = currentReactiveState || {};
        var nextState = reactive && typeof reactive === "object" ? cloneJsonSafe(reactive) : {};
        currentReactiveState = nextState;
        desiredLayers.ambience = chooseAmbienceCue(nextState);
        desiredLayers.music = chooseMusicCue(nextState);
        if (
            previousState
            && previousState.source_id
            && nextState.source_id
            && String(previousState.source_id) !== String(nextState.source_id)
            && String(nextState.scene || "").toLowerCase() === "explore"
        ) {
            playFirstCue(["sfx.travel.step"], { force: true });
        }
        if (
            previousState
            && !previousState.boss
            && nextState.boss
            && String(nextState.scene || "").toLowerCase() === "combat"
        ) {
            playFirstCue(["sfx.combat.boss_intro", "sfx.portal.warp"], { force: true });
        }
        refreshLayerTargets();
        dispatchStateChange();
    }

    function startTitleMusic() {
        var titleState = { scene: "account", world_tone: "neutral" };
        var applyTitleState = function () {
            var startedMobileTitle = false;
            currentReactiveState = cloneJsonSafe(titleState);
            desiredLayers.ambience = "";
            desiredLayers.music = chooseAvailableCue([TITLE_MUSIC_CUE_ID]);
            if (isProbablyMobile() && desiredLayers.music) {
                mobilePlaybackArmed = true;
                startedMobileTitle = true;
                startMobileTitleLayer(desiredLayers.music);
            }
            if (startedMobileTitle) {
                stopLayer("ambience", 300);
            } else {
                refreshLayerTargets();
            }
            dispatchStateChange();
            return getState();
        };
        if (isProbablyMobile()) {
            var mobileState = applyTitleState();
            if (!initialized) {
                init({ manifestUrl: window.BRAVE_AUDIO_MANIFEST_URL || "" });
            }
            return Promise.resolve(mobileState);
        }
        if (!initialized) {
            var initialUnlockPromise = unlock();
            return init({ manifestUrl: window.BRAVE_AUDIO_MANIFEST_URL || "" }).then(function () {
                return initialUnlockPromise.then(applyTitleState);
            });
        }
        if (!manifestLoaded && manifestLoadPromise) {
            var unlockPromise = unlock();
            return manifestLoadPromise.then(function () {
                return unlockPromise.then(applyTitleState);
            });
        }
        if (!canAttemptImmediatePlayback()) {
            return unlock().then(function () {
                return applyTitleState();
            });
        }
        return Promise.resolve(applyTitleState());
    }

    function clearReactiveState() {
        var preserveTitleMusic = isTitleExperienceScene(currentReactiveState && currentReactiveState.scene)
            && (desiredLayers.music === "music.title" || (activeLayers.music && activeLayers.music.cueId === "music.title"));
        currentReactiveState = {};
        desiredLayers.ambience = "";
        desiredLayers.music = preserveTitleMusic ? "music.title" : "";
        stopLayer("ambience", 450);
        if (!preserveTitleMusic) {
            stopLayer("music", 450);
        }
        dispatchStateChange();
    }

    function playCue(cueId, options) {
        options = options || {};
        if (!settings.enabled || settings.muted) {
            return false;
        }
        var cue = getCue(cueId);
        if (!cue) {
            return false;
        }
        if (shouldThrottleCue(cueId, cue, !!options.force)) {
            return false;
        }
        if (!canAttemptImmediatePlayback()) {
            lastPlayback.error = "playback blocked pending unlock for " + cueId;
            unlock().then(function (didUnlock) {
                if (didUnlock && settings.enabled && !settings.muted && !shouldThrottleCue(cueId, cue, true)) {
                    playCueInternal(cueId, cue, options);
                }
            });
            return true;
        }
        playCueInternal(cueId, cue, options).then(function (playback) {
            if (cue.loop && playback && !options.layer) {
                window.setTimeout(function () {
                    playback.stop(220);
                }, 1600);
            }
        });
        return true;
    }

    function handleCombatFx(payload) {
        var event = payload && typeof payload === "object" ? payload : {};
        var kind = String(event.kind || "").toLowerCase();
        var element = String(event.element || "").toLowerCase();
        if (kind === "heal") {
            playFirstCue(["sfx.class.cleric.heal", "sfx.combat.heal"]);
            return;
        }
        if (kind === "defend") {
            playFirstCue(["sfx.combat.block.shield", "sfx.status.shield"]);
            return;
        }
        if (kind === "miss") {
            playFirstCue(["sfx.combat.miss"]);
            return;
        }
        if (kind === "defeat") {
            playFirstCue(["sfx.combat.defeat"]);
            return;
        }
        if (kind === "damage") {
            if (event.critical) {
                playFirstCue(["sfx.combat.critical", "sfx.combat.hit.heavy", "sfx.combat.hit.melee"]);
                return;
            }
            if (element === "bleed") {
                playFirstCue(["sfx.status.bleed", "sfx.combat.hit.melee"]);
                return;
            }
            if (element === "burn") {
                playFirstCue(["sfx.status.burn", "sfx.combat.hit.fire"]);
                return;
            }
            if (element === "poison") {
                playFirstCue(["sfx.status.poison", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "curse") {
                playFirstCue(["sfx.status.curse", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "fire") {
                playFirstCue(["sfx.class.mage.firebolt", "sfx.combat.hit.fire"]);
                return;
            }
            if (element === "holy") {
                playFirstCue(["sfx.class.paladin.holy_strike", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "nature") {
                playFirstCue(["sfx.class.druid.roots", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "frost") {
                playFirstCue(["sfx.class.mage.frostbind", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "lightning") {
                playFirstCue(["sfx.class.mage.arcspark", "sfx.combat.hit.magic"]);
                return;
            }
            if (element === "shadow") {
                playFirstCue(["sfx.class.rogue.shadowstep", "sfx.combat.hit.magic"]);
                return;
            }
            playFirstCue(["sfx.combat.hit.melee"]);
            return;
        }
        if (kind === "action") {
            playFirstCue(["sfx.combat.swing"]);
        }
    }

    function handleNotice(payload) {
        var tone = String((payload && payload.tone) || "muted").toLowerCase();
        if (tone === "good") {
            playFirstCue(["sfx.notice.good"]);
            return;
        }
        if (tone === "warn") {
            playFirstCue(["sfx.notice.warn"]);
            return;
        }
        if (tone === "danger") {
            playFirstCue(["sfx.notice.danger"]);
        }
    }

    function handleRoomActivity(payload) {
        var category = String((payload && payload.category) || "").toLowerCase();
        if (category === "threat") {
            playFirstCue(["sfx.activity.threat"]);
            return;
        }
        if (category === "arrival") {
            playFirstCue(["sfx.activity.arrival"]);
            return;
        }
        if (category === "departure") {
            playFirstCue(["sfx.activity.departure", "sfx.activity.arrival"]);
            return;
        }
        if (category === "loot") {
            playFirstCue(["sfx.activity.loot", "sfx.loot.reward"]);
        }
    }

    function handleUiAction(kind) {
        var unlockPromise = null;
        if (!initialized) {
            unlockPromise = unlock();
            init({ manifestUrl: window.BRAVE_AUDIO_MANIFEST_URL || "" }).then(function () {
                handleUiAction(kind);
            });
            if (unlockPromise && typeof unlockPromise.then === "function") {
                unlockPromise.then(function () {
                    refreshLayerTargets();
                });
            }
            return;
        }
        if (!manifestLoaded && manifestLoadPromise) {
            unlockPromise = unlock();
            manifestLoadPromise.then(function () {
                handleUiAction(kind);
            });
            if (unlockPromise && typeof unlockPromise.then === "function") {
                unlockPromise.then(function () {
                    refreshLayerTargets();
                });
            }
            return;
        }
        var normalized = String(kind || "").toLowerCase();
        var cueIds = ["sfx.ui.click"];
        if (normalized === "error") {
            cueIds = ["sfx.ui.error"];
        } else if (normalized === "success") {
            cueIds = ["sfx.quest.complete", "sfx.notice.good", "sfx.ui.confirm", "sfx.ui.click"];
        } else if (normalized === "select") {
            cueIds = ["sfx.ui.confirm", "sfx.quest.started", "sfx.ui.click"];
        } else if (normalized === "equip") {
            cueIds = ["sfx.inventory.equip", "sfx.ui.confirm", "sfx.ui.click"];
        } else if (normalized === "unequip") {
            cueIds = ["sfx.inventory.unequip", "sfx.inventory.equip", "sfx.ui.back", "sfx.ui.click"];
        } else if (normalized === "menu" || normalized === "open") {
            cueIds = ["sfx.ui.menu_open", "sfx.ui.click"];
        } else if (normalized === "journal_tab" || normalized === "tab") {
            cueIds = ["sfx.ui.journal_tab", "sfx.ui.menu_open", "sfx.ui.click"];
        } else if (normalized === "navigate" || normalized === "move") {
            cueIds = ["sfx.ui.navigate", "sfx.ui.click"];
        } else if (normalized === "back" || normalized === "close") {
            cueIds = ["sfx.ui.back", "sfx.ui.click"];
        }
        if (!canAttemptImmediatePlayback()) {
            unlock().then(function (didUnlock) {
                if (didUnlock || canAttemptImmediatePlayback()) {
                    refreshLayerTargets();
                    playFirstCue(cueIds, { force: true });
                }
            });
            return;
        }
        refreshLayerTargets();
        playFirstCue(cueIds);
    }

    function handleRest(payload) {
        if (!contextUnlocked) {
            unlock().then(function (didUnlock) {
                if (didUnlock || contextUnlocked) {
                    playFirstCue(["music.rest"], { force: true });
                    playFirstCue(["sfx.activity.rest", "sfx.combat.heal"], { force: true });
                }
            });
            return;
        }
        playFirstCue(["music.rest"], { force: true });
        playFirstCue(["sfx.activity.rest", "sfx.combat.heal"], { force: true });
    }

    function previewCue(cueId) {
        if (isProbablyMobile()) {
            mobilePlaybackArmed = true;
        }
        unlock().then(function (didUnlock) {
            if (!didUnlock && !canAttemptImmediatePlayback()) {
                return;
            }
            playCue(cueId, { force: true });
            dispatchStateChange();
        });
    }

    function bindUnlockHandlers() {
        if (unlockHandlersBound) {
            return;
        }
        var unlockOnce = function () {
            if (isProbablyMobile()) {
                mobilePlaybackArmed = true;
                refreshLayerTargets();
                dispatchStateChange();
            }
            unlock();
        };
        ["pointerdown", "touchstart", "touchend", "mousedown", "keydown"].forEach(function (eventName) {
            document.addEventListener(eventName, unlockOnce, { passive: true, capture: true });
        });
        unlockHandlersBound = true;
    }

    function unlock() {
        var ctx = getAudioContext();
        if (isProbablyMobile()) {
            mobilePlaybackArmed = true;
        }
        if (!ctx) {
            dispatchStateChange();
            refreshLayerTargets();
            return Promise.resolve(!!mobilePlaybackArmed);
        }
        if (contextUnlocked && ctx.state !== "suspended") {
            return Promise.resolve(true);
        }
        if (unlockInFlight) {
            return unlockInFlight;
        }
        unlockInFlight = ctx.resume()
            .then(function () {
                performUnlockPulse(ctx);
                contextUnlocked = true;
                if (isProbablyMobile()) {
                    mobilePlaybackArmed = true;
                }
                applyBusVolumes();
                refreshLayerTargets();
                dispatchStateChange();
                return true;
            })
            .catch(function () {
                if (isProbablyMobile()) {
                    applyBusVolumes();
                    refreshLayerTargets();
                    dispatchStateChange();
                    return true;
                }
                return false;
            })
            .finally(function () {
                unlockInFlight = null;
            });
        return unlockInFlight;
    }

    function setSetting(key, value) {
        if (!Object.prototype.hasOwnProperty.call(DEFAULT_SETTINGS, key)) {
            return getState();
        }
        if (typeof DEFAULT_SETTINGS[key] === "boolean") {
            settings[key] = !!value;
        } else {
            settings[key] = clamp01(value, DEFAULT_SETTINGS[key]);
        }
        persistSettings();
        applyBusVolumes();
        if (!settings.enabled || settings.muted) {
            stopLayer("ambience", 260);
            stopLayer("music", 260);
        } else {
            refreshLayerTargets();
        }
        dispatchStateChange();
        return getState();
    }

    function toggleSetting(key) {
        if (!Object.prototype.hasOwnProperty.call(DEFAULT_SETTINGS, key) || typeof DEFAULT_SETTINGS[key] !== "boolean") {
            return getState();
        }
        return setSetting(key, !settings[key]);
    }

    function getState() {
        return {
            supported: !!(window.AudioContext || window.webkitAudioContext),
            mobile: isProbablyMobile(),
            initialized: initialized,
            unlocked: contextUnlocked,
            mobile_playback_armed: mobilePlaybackArmed,
            manifest_loaded: manifestLoaded,
            manifest_url: manifestUrl || "",
            settings: cloneJsonSafe(settings),
            active_layers: {
                ambience: activeLayers.ambience ? activeLayers.ambience.cueId : "",
                music: activeLayers.music ? activeLayers.music.cueId : ""
            },
            desired_layers: cloneJsonSafe(desiredLayers),
            reactive: cloneJsonSafe(currentReactiveState),
            last_playback: cloneJsonSafe(lastPlayback)
        };
    }

    function init(options) {
        options = options || {};
        if (initialized) {
            if (manifestLoadPromise && !manifestLoaded) {
                return manifestLoadPromise.then(function () {
                    return getState();
                });
            }
            return Promise.resolve(getState());
        }
        initialized = true;
        manifestUrl = options.manifestUrl || window.BRAVE_AUDIO_MANIFEST_URL || "";
        getAudioContext();
        if (isContextRunning()) {
            contextUnlocked = true;
            mobilePlaybackArmed = true;
        }
        bindUnlockHandlers();
        dispatchStateChange();
        manifestLoadPromise = loadManifest(manifestUrl).then(function () {
            return getState();
        });
        return manifestLoadPromise;
    }

    window.BraveAudio = {
        init: init,
        unlock: unlock,
        getState: getState,
        setReactiveState: setReactiveState,
        startTitleMusic: startTitleMusic,
        clearReactiveState: clearReactiveState,
        handleCombatFx: handleCombatFx,
        handleNotice: handleNotice,
        handleRest: handleRest,
        handleRoomActivity: handleRoomActivity,
        handleUiAction: handleUiAction,
        play: playCue,
        previewCue: previewCue,
        setSetting: setSetting,
        toggleSetting: toggleSetting
    };
})();
