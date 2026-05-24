r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from pathlib import Path

from evennia.settings_default import *

BRAVE_GAME_DIR = Path(__file__).resolve().parents[2]
BRAVE_TEMPLATE_DIR = BRAVE_GAME_DIR / "web" / "templates"
if BRAVE_TEMPLATE_DIR.exists():
    TEMPLATES[0]["DIRS"] = [str(BRAVE_TEMPLATE_DIR), *TEMPLATES[0].get("DIRS", [])]

# Dynamic static asset versioning for cache-busting on server restart
import time
BRAVE_REAL_STATIC_VERSION = f"prod-{int(time.time())}"

def brave_static_version_processor(request):
    return {
        "brave_real_static_v": BRAVE_REAL_STATIC_VERSION,
        "brave_static_v": BRAVE_REAL_STATIC_VERSION,
    }

TEMPLATES[0]["OPTIONS"].setdefault("context_processors", []).append(
    "server.conf.settings.brave_static_version_processor"
)

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Brave"
GAME_SLOGAN = "A cozy frontier town and a dangerous world beyond it."
TIME_ZONE = "America/New_York"
MULTISESSION_MODE = 2
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_CHARACTERS = 10

# Production Proxy Settings
WEBSOCKET_CLIENT_URL = "wss://brave.junewiregames.com/ws"
CSRF_TRUSTED_ORIGINS = ["https://brave.junewiregames.com"]
ALLOWED_HOSTS = ["brave.junewiregames.com", "localhost", "127.0.0.1"]
DEBUG = False

# The default Evennia networking settings already listen on 0.0.0.0 and allow
# LAN access, which matches Brave's local-family multiplayer target.


######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
