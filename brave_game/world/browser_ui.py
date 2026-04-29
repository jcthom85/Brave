"""Shared browser-view payload primitives for Brave."""

from world.browser_context import ENEMY_TEMPLATES
from world.data.world_tones import get_world_tone_key
from world.enemy_icons import get_enemy_icon_name

def _display_name(obj):
    display_name = getattr(getattr(obj, "db", None), "brave_display_name", None)
    if display_name:
        return str(display_name)
    key = getattr(obj, "key", "") or ""
    if not key:
        return ""
    return key.title()

def _chip(label, icon, tone="muted"):
    return {"label": label, "icon": icon, "tone": tone}

def _action(label, command, icon, *, tone=None, confirm=None, icon_only=False, aria_label=None, picker=None, no_icon=False):
    action = {"label": label, "icon": icon}
    if command:
        action["command"] = command
    if tone:
        action["tone"] = tone
    if confirm:
        action["confirm"] = confirm
    if icon_only:
        action["icon_only"] = True
    if aria_label:
        action["aria_label"] = aria_label
    if picker:
        action["picker"] = picker
    if no_icon:
        action["no_icon"] = True
    return action

def _item(
    text,
    *,
    icon=None,
    background_icon=None,
    badge=None,
    command=None,
    prefill=None,
    confirm=None,
    actions=None,
    picker=None,
    tooltip=None,
    detail=None,
    marker_icon=None,
    on_open_command=None,
    dismiss_bubble_speaker=None,
):
    item = {"text": text}
    if icon:
        item["icon"] = icon
    if badge:
        item["badge"] = badge
    if command:
        item["command"] = command
    if prefill:
        item["prefill"] = prefill
    if confirm:
        item["confirm"] = confirm
    if actions:
        item["actions"] = actions
    if picker:
        item["picker"] = picker
    if tooltip:
        item["tooltip"] = tooltip
    if detail:
        item["detail"] = detail
    if marker_icon:
        item["marker_icon"] = marker_icon
    if on_open_command:
        item["on_open_command"] = on_open_command
    if dismiss_bubble_speaker:
        item["dismiss_bubble_speaker"] = dismiss_bubble_speaker
    return item

def _line(text, *, icon=None):
    line = {"text": text}
    if icon:
        line["icon"] = icon
    return line

def _pair(label, value, icon=None):
    return {"label": label, "value": str(value), "icon": icon}

def _meter(label, current, maximum, *, tone="accent", meta=None, value=None):
    current_value = max(0, int(current or 0))
    maximum_value = max(1, int(maximum or 0))
    percent = max(0, min(100, int(round((current_value / maximum_value) * 100))))
    meter = {
        "label": label,
        "value": value or f"{current_value} / {maximum_value}",
        "percent": percent,
        "tone": tone,
    }
    if meta:
        meter["meta"] = dict(meta)
    return meter

def _resource_meter_tone(current, maximum):
    maximum_value = max(1, int(maximum or 0))
    current_value = max(0, int(current or 0))
    percent = current_value / maximum_value
    if percent <= 0.25:
        return "danger"
    if percent <= 0.6:
        return "warn"
    return "good"

def _hp_meter_tone(current, maximum):
    maximum_value = max(1, int(maximum or 0))
    current_value = max(0, int(current or 0))
    percent = current_value / maximum_value
    if percent <= 0.25:
        return "danger"
    if percent <= 0.5:
        return "warn"
    return "good"

def _enemy_icon(enemy):
    enemy = dict(enemy or {})
    template_key = str(enemy.get("template_key") or "").strip().lower()
    template = ENEMY_TEMPLATES.get(template_key, {})
    return str(enemy.get("icon") or get_enemy_icon_name(template_key, template))

def _combat_card_size_class(entry=None, *, enemy=False):
    if not enemy:
        return "normal"
    entry = dict(entry or {})
    template_key = str(entry.get("template_key") or "").strip().lower()
    template = ENEMY_TEMPLATES.get(template_key, {})
    tags = {str(tag).lower() for tag in template.get("tags", [])}
    rank = int(entry.get("rank") or 1)
    if "boss" in tags:
        return "boss"
    if rank >= 4 or {"captain", "commander", "elite"} & tags:
        return "elite"
    return "normal"

def _entry(
    title,
    *,
    meta=None,
    lines=None,
    summary=None,
    icon=None,
    background_icon=None,
    badge=None,
    command=None,
    prefill=None,
    confirm=None,
    actions=None,
    picker=None,
    chips=None,
    meters=None,
    size_class=None,
    tooltip=None,
    selected=False,
    combat_state=None,
    entry_ref=None,
    hide_icon=False,
    attachments=None,
    sidecars=None,
    cluster_ref=None,
):
    entry = {
        "title": title,
        "meta": meta,
        "lines": [line for line in (lines or []) if line],
        "summary": summary or "",
        "icon": icon,
        "badge": badge,
    }
    if background_icon:
        entry["background_icon"] = background_icon
    if hide_icon:
        entry["hide_icon"] = True
    if selected:
        entry["selected"] = True
    if combat_state:
        entry["combat_state"] = list(combat_state)
    if entry_ref:
        entry["entry_ref"] = str(entry_ref)
    if command:
        entry["command"] = command
    if prefill:
        entry["prefill"] = prefill
    if confirm:
        entry["confirm"] = confirm
    if actions:
        entry["actions"] = actions
    if picker:
        entry["picker"] = picker
    if chips:
        entry["chips"] = chips
    if meters:
        entry["meters"] = meters
    if tooltip:
        entry["tooltip"] = tooltip
    if size_class:
        entry["size_class"] = size_class
    if attachments:
        entry["attachments"] = list(attachments)
    if sidecars:
        entry["sidecars"] = list(sidecars)
    if cluster_ref:
        entry["cluster_ref"] = str(cluster_ref)
    return entry

def _picker_option(label, *, command=None, prefill=None, icon=None, meta=None, tone=None, picker=None, chat_open=False, chat_prompt=None):
    option = {"label": label}
    if command:
        option["command"] = command
    if prefill:
        option["prefill"] = prefill
    if icon:
        option["icon"] = icon
    if meta:
        option["meta"] = meta
    if tone:
        option["tone"] = tone
    if picker:
        option["picker"] = picker
    if chat_open:
        option["chat_open"] = True
    if chat_prompt:
        option["chat_prompt"] = chat_prompt
    return option

def _picker(title, *, subtitle=None, options=None, body=None, picker_id=None, title_icon=None):
    picker = {
        "title": title,
        "options": [option for option in (options or []) if option],
    }
    if picker_id:
        picker["picker_id"] = picker_id
    if title_icon:
        picker["title_icon"] = title_icon
    if subtitle:
        picker["subtitle"] = subtitle
    if body:
        picker["body"] = [line for line in body if line]
    return picker

def _section(label, icon, kind, items=None, lines=None, span=None, **extra):
    section = {
        "label": label,
        "icon": icon,
        "kind": kind,
        "items": items or [],
        "lines": lines or [],
    }
    if span:
        section["span"] = span
    if extra:
        section.update(extra)
    return section

def _make_view(
    eyebrow,
    title,
    *,
    eyebrow_icon,
    title_icon,
    wordmark=None,
    subtitle=None,
    chips=None,
    sections=None,
    actions=None,
    back=False,
    reactive=None,
    welcome_pages=None,
):
    view_actions = list(actions or [])
    back_action = _action("Close", "look", "close", tone="muted", aria_label="Close") if back else None
    return {
        "eyebrow": eyebrow,
        "eyebrow_icon": eyebrow_icon,
        "title": title,
        "title_icon": title_icon,
        "wordmark": wordmark or "",
        "subtitle": subtitle or "",
        "back_action": back_action,
        "chips": [chip for chip in (chips or []) if chip],
        "sections": sections or [],
        "actions": view_actions,
        "reactive": reactive or {},
        "welcome_pages": welcome_pages or [],
    }

def _reactive_view(source=None, *, scene="system", danger=None, boss=False):
    """Build semantic browser-reactivity metadata for a view."""

    reactive = {
        "scene": scene,
        "world_tone": get_world_tone_key(source),
    }
    source_id = getattr(source, "id", None)
    if source_id is not None:
        reactive["source_id"] = str(source_id)
    if danger:
        reactive["danger"] = danger
    if boss:
        reactive["boss"] = True
    return reactive

def _reactive_from_character(character, *, scene="system", danger=None, boss=False):
    """Convenience wrapper using the character's current room."""

    return _reactive_view(getattr(character, "location", None), scene=scene, danger=danger, boss=boss)
