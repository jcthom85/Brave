"""This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

from .views.creator import (
    creator_index,
    creator_character_editor,
    creator_dialogue_editor,
    creator_encounter_editor,
    creator_item_editor,
    creator_quest_editor,
    creator_world_editor,
)

urlpatterns = [
    path("creator/", creator_index, name="creator-index"),
    path("creator/world/", creator_world_editor, name="creator-world-editor"),
    path("creator/quests/", creator_quest_editor, name="creator-quest-editor"),
    path("creator/characters/", creator_character_editor, name="creator-character-editor"),
    path("creator/dialogue/", creator_dialogue_editor, name="creator-dialogue-editor"),
    path("creator/encounters/", creator_encounter_editor, name="creator-encounter-editor"),
    path("creator/items/", creator_item_editor, name="creator-item-editor"),
]

urlpatterns = urlpatterns + evennia_website_urlpatterns
