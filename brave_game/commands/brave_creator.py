"""Creator-facing content commands for Brave."""

import json

from world.content import (
    ContentEditor,
    preview_character_config,
    preview_class,
    preview_dialogue,
    preview_encounter,
    preview_enemy,
    preview_forge_recipe,
    preview_item,
    preview_quest,
    preview_race,
    preview_readable,
    preview_room,
    preview_room_encounters,
)
from world.content.registry import reload_content_registry
from world.content.validation import validate_content_registry

from .brave import BraveCharacterCommand


def _parse_json_payload(raw_payload):
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc.msg} (line {exc.lineno}, column {exc.colno})") from exc


def _normalize_stage(stage):
    normalized = str(stage or "live").strip().lower()
    if normalized not in {"live", "draft"}:
        raise ValueError(f"Unknown content stage: {stage}")
    return normalized


def preview_content(kind, args, registry=None):
    normalized = str(kind or "").strip().lower()
    tokens = [str(token or "").strip() for token in (args or []) if str(token or "").strip()]

    if normalized == "room":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview room <room_id>")
        return preview_room(tokens[0], registry=registry)
    if normalized == "quest":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview quest <quest_key>")
        return preview_quest(tokens[0], registry=registry)
    if normalized == "class":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview class <class_key>")
        return preview_class(tokens[0], registry=registry)
    if normalized == "race":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview race <race_key>")
        return preview_race(tokens[0], registry=registry)
    if normalized == "character-config":
        if tokens:
            raise ValueError("Usage: content preview character-config")
        return preview_character_config(registry=registry)
    if normalized == "item":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview item <template_id>")
        return preview_item(tokens[0], registry=registry)
    if normalized == "encounter":
        if len(tokens) != 2:
            raise ValueError("Usage: content preview encounter <room_id> <encounter_key>")
        return preview_encounter(tokens[0], tokens[1], registry=registry)
    if normalized == "forge":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview forge <source_template_id>")
        return preview_forge_recipe(tokens[0], registry=registry)
    if normalized == "dialogue":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview dialogue <entity_id>")
        return preview_dialogue(tokens[0], registry=registry)
    if normalized == "readable":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview readable <entity_id>")
        return preview_readable(tokens[0], registry=registry)
    if normalized == "encounters":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview encounters <room_id>")
        return preview_room_encounters(tokens[0], registry=registry)
    if normalized == "enemy":
        if len(tokens) != 1:
            raise ValueError("Usage: content preview enemy <template_key>")
        return preview_enemy(tokens[0], registry=registry)

    raise ValueError(f"Unknown preview kind: {kind}")


def mutate_content(kind, target, raw_payload, *, write=False, editor=None, stage="live", author="system"):
    normalized = str(kind or "").strip().lower()
    key = str(target or "").strip()
    editor = editor or ContentEditor()
    payload = _parse_json_payload(raw_payload)
    stage = _normalize_stage(stage)

    if normalized in {"room", "exit", "entity"}:
        if not isinstance(payload, dict):
            raise ValueError(f"{normalized.title()} payload must be a JSON object.")
        data = dict(payload)
        if key:
            data.setdefault("id", key)
        if not data.get("id"):
            raise ValueError(f"{normalized.title()} payload requires an id.")
        if normalized == "room":
            return editor.upsert_room(data, write=write, stage=stage, author=author)
        if normalized == "exit":
            return editor.upsert_exit(data, write=write, stage=stage, author=author)
        return editor.upsert_entity(data, write=write, stage=stage, author=author)

    if normalized == "item":
        if not key:
            raise ValueError("Item updates require a template id.")
        if not isinstance(payload, dict):
            raise ValueError("Item payload must be a JSON object.")
        return editor.upsert_item(key, payload, write=write, stage=stage, author=author)

    if normalized == "race":
        if not key:
            raise ValueError("Race updates require a race key.")
        if not isinstance(payload, dict):
            raise ValueError("Race payload must be a JSON object.")
        return editor.upsert_race(key, payload, write=write, stage=stage, author=author)

    if normalized == "class":
        if not key:
            raise ValueError("Class updates require a class key.")
        if not isinstance(payload, dict):
            raise ValueError("Class payload must be a JSON object.")
        return editor.upsert_class(key, payload, write=write, stage=stage, author=author)

    if normalized == "character-config":
        if not isinstance(payload, dict):
            raise ValueError("Character-config payload must be a JSON object.")
        return editor.upsert_character_config(payload, write=write, stage=stage, author=author)

    if normalized == "quest":
        if not key:
            raise ValueError("Quest updates require a quest key.")
        if not isinstance(payload, dict):
            raise ValueError("Quest payload must be a JSON object.")
        region = None
        add_starting = False
        quest_data = dict(payload)
        if "quest" in quest_data:
            region = quest_data.get("region")
            add_starting = bool(quest_data.get("add_starting"))
            quest_data = dict(quest_data.get("quest") or {})
        return editor.upsert_quest(key, quest_data, region=region, add_starting=add_starting, write=write, stage=stage, author=author)

    if normalized == "dialogue":
        if not key:
            raise ValueError("Dialogue updates require an entity id.")
        if not isinstance(payload, list):
            raise ValueError("Dialogue payload must be a JSON list of rule objects.")
        return editor.upsert_dialogue_rules(key, payload, write=write, stage=stage, author=author)

    if normalized == "read":
        if not key:
            raise ValueError("Read-response updates require an entity id.")
        if not isinstance(payload, str):
            raise ValueError("Read-response payload must be a JSON string.")
        return editor.upsert_static_read_response(key, payload, write=write, stage=stage, author=author)

    if normalized == "enemy":
        if not key:
            raise ValueError("Enemy updates require a template key.")
        if not isinstance(payload, dict):
            raise ValueError("Enemy payload must be a JSON object.")
        return editor.upsert_enemy_template(key, payload, write=write, stage=stage, author=author)

    if normalized == "encounters":
        if not key:
            raise ValueError("Encounter-table updates require a room id.")
        if not isinstance(payload, list):
            raise ValueError("Encounter-table payload must be a JSON list.")
        return editor.upsert_room_encounters(key, payload, write=write, stage=stage, author=author)

    if normalized == "forge":
        if not key:
            raise ValueError("Forge updates require a source template id.")
        if not isinstance(payload, dict):
            raise ValueError("Forge payload must be a JSON object.")
        return editor.upsert_forge_recipe(key, payload, write=write, stage=stage, author=author)

    raise ValueError(f"Unknown mutation kind: {kind}")


def remove_content(kind, target, *, write=False, editor=None, stage="live", author="system"):
    normalized = str(kind or "").strip().lower()
    key = str(target or "").strip()
    editor = editor or ContentEditor()
    stage = _normalize_stage(stage)

    if normalized == "room":
        if not key:
            raise ValueError("Room removal requires a room id.")
        return editor.delete_room(key, write=write, stage=stage, author=author)
    if normalized == "exit":
        if not key:
            raise ValueError("Exit removal requires an exit id.")
        return editor.delete_exit(key, write=write, stage=stage, author=author)
    if normalized == "entity":
        if not key:
            raise ValueError("Entity removal requires an entity id.")
        return editor.delete_entity(key, write=write, stage=stage, author=author)
    if normalized == "item":
        if not key:
            raise ValueError("Item removal requires a template id.")
        return editor.delete_item(key, write=write, stage=stage, author=author)
    if normalized == "race":
        if not key:
            raise ValueError("Race removal requires a race key.")
        return editor.delete_race(key, write=write, stage=stage, author=author)
    if normalized == "class":
        if not key:
            raise ValueError("Class removal requires a class key.")
        return editor.delete_class(key, write=write, stage=stage, author=author)
    if normalized == "quest":
        if not key:
            raise ValueError("Quest removal requires a quest key.")
        return editor.delete_quest(key, write=write, stage=stage, author=author)
    if normalized == "dialogue":
        if not key:
            raise ValueError("Dialogue removal requires an entity id.")
        return editor.delete_dialogue_rules(key, write=write, stage=stage, author=author)
    if normalized == "read":
        if not key:
            raise ValueError("Read-response removal requires an entity id.")
        return editor.delete_static_read_response(key, write=write, stage=stage, author=author)
    if normalized == "enemy":
        if not key:
            raise ValueError("Enemy removal requires a template key.")
        return editor.delete_enemy_template(key, write=write, stage=stage, author=author)
    if normalized == "encounters":
        if not key:
            raise ValueError("Encounter-table removal requires a room id.")
        return editor.delete_room_encounters(key, write=write, stage=stage, author=author)
    if normalized == "forge":
        if not key:
            raise ValueError("Forge removal requires a source template id.")
        return editor.delete_forge_recipe(key, write=write, stage=stage, author=author)

    raise ValueError(f"Unknown removal kind: {kind}")


def list_content_history(*, domain=None, stage=None, limit=20, editor=None):
    editor = editor or ContentEditor()
    return editor.list_history(domain=domain, stage=_normalize_stage(stage) if stage else None, limit=limit)


def revert_content(entry_id, *, write=False, stage=None, editor=None, author="system"):
    editor = editor or ContentEditor()
    return editor.revert_history(entry_id, stage=_normalize_stage(stage) if stage else None, write=write, author=author)


def publish_content(domain=None, *, editor=None, author="system"):
    editor = editor or ContentEditor()
    normalized_domain = None if domain in (None, "", "all") else str(domain).strip().lower()
    return editor.publish_stage(normalized_domain, author=author)


def _render_json_block(payload):
    return json.dumps(payload, indent=2, sort_keys=True)


def _command_usage_lines():
    return [
        "Usage:",
        "  content preview room <room_id>",
        "  content upsert[/write][/draft] <kind> <target> = {json}",
        "  content remove[/write][/draft] <kind> <target>",
        "  content history [domain] [stage]",
        "  content revert[/write][/draft] <entry_id>",
        "  content publish [domain|all]",
        "  content validate",
        "  content reload",
        "",
        "Use /write to persist. Use /draft to write to draft packs instead of live packs.",
    ]


class CmdContent(BraveCharacterCommand):
    key = "content"
    aliases = ["creator", "contenttool"]
    locks = "cmd:perm(Developer)"
    help_category = "Builder"

    def func(self):
        raw = (self.args or "").strip()
        if not raw:
            self.msg("\n".join(_command_usage_lines()))
            return

        tokens = raw.split()
        action = tokens[0].lower()

        try:
            if action == "preview":
                self._handle_preview(tokens[1:])
                return
            if action == "upsert":
                self._handle_upsert()
                return
            if action == "remove":
                self._handle_remove(tokens[1:])
                return
            if action == "history":
                self._handle_history(tokens[1:])
                return
            if action == "revert":
                self._handle_revert(tokens[1:])
                return
            if action == "publish":
                self._handle_publish(tokens[1:])
                return
            if action == "validate":
                self._handle_validate()
                return
            if action == "reload":
                self._handle_reload()
                return
        except ValueError as exc:
            self.msg(str(exc))
            return

        self.msg("Unknown content action.\n" + "\n".join(_command_usage_lines()))

    def _stage_from_switches(self):
        return "draft" if "draft" in {switch.lower() for switch in self.switches} else "live"

    def _author(self):
        caller = getattr(self, "caller", None)
        return getattr(caller, "key", None) or getattr(caller, "name", None) or "system"

    def _handle_preview(self, tokens):
        if not tokens:
            raise ValueError("Usage: content preview <room|quest|class|race|character-config|item|encounter|forge|dialogue|readable|encounters|enemy> ...")
        kind = tokens[0]
        payload = preview_content(kind, tokens[1:])
        if payload is None:
            self.msg(f"No {kind} preview found for that target.")
            return
        self.msg(_render_json_block(payload))

    def _handle_upsert(self):
        if self.rhs is None:
            raise ValueError("Usage: content upsert[/write][/draft] <kind> <target> = {json}")
        lhs_tokens = [token for token in (self.lhs or "").split() if token]
        if len(lhs_tokens) < 2:
            raise ValueError("Usage: content upsert[/write][/draft] <kind> <target> = {json}")
        kind = lhs_tokens[1]
        target = lhs_tokens[2] if len(lhs_tokens) > 2 else ""
        switches = {switch.lower() for switch in self.switches}
        write = "write" in switches
        stage = self._stage_from_switches()
        mutation = mutate_content(kind, target, self.rhs, write=write, stage=stage, author=self._author())
        self.msg(self._render_mutation_lines(mutation, write, verb="Persisted to disk." if write else "Dry run only. Use /write to persist."))

    def _handle_remove(self, tokens):
        if len(tokens) < 2:
            raise ValueError("Usage: content remove[/write][/draft] <kind> <target>")
        switches = {switch.lower() for switch in self.switches}
        write = "write" in switches
        stage = self._stage_from_switches()
        mutation = remove_content(tokens[0], tokens[1], write=write, stage=stage, author=self._author())
        self.msg(self._render_mutation_lines(mutation, write, verb="Persisted removal to disk." if write else "Dry run only. Use /write to persist removal."))

    def _handle_history(self, tokens):
        domain = tokens[0] if tokens else None
        stage = tokens[1] if len(tokens) > 1 else None
        entries = list_content_history(domain=domain, stage=stage, limit=12)
        if not entries:
            self.msg("No content history entries found.")
            return
        lines = []
        for entry in entries:
            lines.append(f"{entry['entry_id']} | {entry['domain']} | {entry['stage']} | {entry['action']} | {entry.get('target') or '-'} | {entry.get('author') or 'system'}")
        self.msg("\n".join(lines))

    def _handle_revert(self, tokens):
        if not tokens:
            raise ValueError("Usage: content revert[/write][/draft] <entry_id>")
        switches = {switch.lower() for switch in self.switches}
        write = "write" in switches
        stage = self._stage_from_switches() if "draft" in switches else None
        mutation = revert_content(tokens[0], write=write, stage=stage, author=self._author())
        self.msg(self._render_mutation_lines(mutation, write, verb="Revert persisted to disk." if write else "Dry-run revert only. Use /write to persist."))

    def _handle_publish(self, tokens):
        domain = tokens[0] if tokens else None
        mutations = publish_content(domain, author=self._author())
        if not mutations:
            self.msg("No draft pack changes were available to publish.")
            return
        registry = reload_content_registry()
        errors = validate_content_registry(registry)
        lines = [f"Published {len(mutations)} domain(s) from draft to live."]
        for mutation in mutations:
            lines.append(f"- {mutation.domain}: {mutation.path}")
        if errors:
            lines.append("Validation after publish found issues:")
            lines.extend(f"- {entry}" for entry in errors)
        else:
            lines.append("Validation passed after reload.")
        self.msg("\n".join(lines))

    def _render_mutation_lines(self, mutation, write, *, verb):
        lines = [f"{mutation.domain} [{mutation.stage}] -> {mutation.path}", verb]
        if mutation.entry_id:
            lines.append(f"History entry: {mutation.entry_id}")
        if mutation.history_path:
            lines.append(f"History path: {mutation.history_path}")
        if write and mutation.stage == "live":
            registry = reload_content_registry()
            errors = validate_content_registry(registry)
            if errors:
                lines.append("Validation after write found issues:")
                lines.extend(f"- {entry}" for entry in errors)
            else:
                lines.append("Validation passed after reload.")
        if mutation.diff:
            lines.extend(["", mutation.diff.rstrip()])
        else:
            lines.extend(["", "No diff generated."])
        return "\n".join(lines)

    def _handle_validate(self):
        errors = validate_content_registry(reload_content_registry())
        if errors:
            self.msg("Content validation failed:\n" + "\n".join(f"- {entry}" for entry in errors))
            return
        self.msg("Content validation passed.")

    def _handle_reload(self):
        reload_content_registry()
        self.msg("Content registry reloaded from pack files.")
