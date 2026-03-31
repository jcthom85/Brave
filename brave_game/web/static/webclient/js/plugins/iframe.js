/*
 * Brave override of Evennia's iframe plugin.
 *
 * The stock Browser-in-Browser pane can strand users in a saved layout state
 * that is hostile to the game UI, so Brave disables it entirely.
 */
let iframe = (function () {
    "use strict";

    return {
        init: function () {},
        postInit: function () {},
    };
})();
window.plugin_handler.add("iframe", iframe);
