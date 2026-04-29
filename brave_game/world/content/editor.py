"""Editor-facing helpers for Brave content packs.

These helpers provide the stable mutation layer for creator tools. They
load JSON packs, apply structured updates, emit diffs, maintain per-write
history, and can persist either to the live packs or draft pack copies.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import unified_diff
import json
from pathlib import Path

from world.content.history import ContentHistoryStore
from world.content.registry import (
    CHARACTERS_PACK_PATH,
    DIALOGUE_PACK_PATH,
    ENCOUNTERS_PACK_PATH,
    ITEMS_PACK_PATH,
    QUESTS_PACK_PATH,
    SYSTEMS_PACK_PATH,
    WORLD_PACK_PATH,
    build_content_registry_from_payloads,
)


PACK_PATHS = {
    "characters": CHARACTERS_PACK_PATH,
    "items": ITEMS_PACK_PATH,
    "quests": QUESTS_PACK_PATH,
    "world": WORLD_PACK_PATH,
    "encounters": ENCOUNTERS_PACK_PATH,
    "dialogue": DIALOGUE_PACK_PATH,
    "systems": SYSTEMS_PACK_PATH,
}


@dataclass(frozen=True)
class ContentMutation:
    domain: str
    path: str
    diff: str
    payload: dict
    stage: str = "live"
    entry_id: str = ""
    history_path: str = ""


class ContentPublishValidationError(ValueError):
    """Raised when draft content cannot be promoted without breaking live validation."""

    def __init__(self, errors, *, domains):
        self.errors = list(errors)
        self.domains = list(domains)
        super().__init__("Content publish failed validation.")


class ContentEditor:
    """Structured editor for Brave's JSON pack domains."""

    def __init__(self, pack_paths=None, draft_pack_paths=None, history_root=None):
        self.pack_paths = {key: Path(path) for key, path in (pack_paths or PACK_PATHS).items()}
        self.draft_pack_paths = draft_pack_paths or self._build_default_draft_paths(self.pack_paths)
        self.draft_pack_paths = {key: Path(path) for key, path in self.draft_pack_paths.items()}
        self.history = ContentHistoryStore(history_root or self._default_history_root())

    def load_pack(self, domain, *, stage="live"):
        path = self._path_for(domain, stage=stage)
        if stage == "draft" and not path.exists():
            live_path = self._path_for(domain, stage="live")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(live_path.read_text(encoding="utf-8"), encoding="utf-8")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_pack(self, domain, payload, *, stage="live"):
        path = self._path_for(domain, stage=stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._serialize(payload), encoding="utf-8")
        return str(path)

    def diff_pack(self, domain, payload, *, stage="live"):
        path = self._path_for(domain, stage=stage)
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        after = self._serialize(payload)
        return "".join(
            unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
            )
        )

    def apply_pack_update(self, domain, updater, *, write=False, stage="live", author="system", action="update", target=""):
        payload = self.load_pack(domain, stage=stage)
        updated = updater(deepcopy(payload))
        persisted = self._stamp_payload(updated, author=author, action=action, target=target, stage=stage) if write else updated
        diff = self.diff_pack(domain, persisted if write else updated, stage=stage)
        entry_id = ""
        history_path = ""
        if write:
            self.write_pack(domain, persisted, stage=stage)
            history_entry, recorded_path = self.history.record(
                domain=domain,
                stage=stage,
                action=action,
                target=target,
                path=str(self._path_for(domain, stage=stage)),
                diff=diff,
                before=payload,
                after=persisted,
                author=author,
            )
            entry_id = history_entry["entry_id"]
            history_path = str(recorded_path)
        return ContentMutation(domain=domain, path=str(self._path_for(domain, stage=stage)), diff=diff, payload=persisted if write else updated, stage=stage, entry_id=entry_id, history_path=history_path)

    def list_history(self, *, domain=None, stage=None, limit=20):
        return self.history.list_entries(domain=domain, stage=stage, limit=limit)

    def revert_history(self, entry_id, *, stage=None, write=False, author="system"):
        entry = self.history.get(entry_id)
        target_stage = stage or entry.get("stage") or "live"
        domain = entry["domain"]
        target_payload = deepcopy(entry.get("before") or {})
        if not isinstance(target_payload, dict):
            raise ValueError("History entry does not contain a valid pack snapshot.")
        persisted = self._stamp_payload(target_payload, author=author, action="revert", target=entry_id, stage=target_stage) if write else target_payload
        diff = self.diff_pack(domain, persisted if write else target_payload, stage=target_stage)
        new_entry_id = ""
        history_path = ""
        if write:
            before_payload = self.load_pack(domain, stage=target_stage)
            self.write_pack(domain, persisted, stage=target_stage)
            history_entry, recorded_path = self.history.record(
                domain=domain,
                stage=target_stage,
                action="revert",
                target=entry_id,
                path=str(self._path_for(domain, stage=target_stage)),
                diff=diff,
                before=before_payload,
                after=persisted,
                author=author,
                extra={"reverted_entry_id": entry_id},
            )
            new_entry_id = history_entry["entry_id"]
            history_path = str(recorded_path)
        return ContentMutation(domain=domain, path=str(self._path_for(domain, stage=target_stage)), diff=diff, payload=persisted if write else target_payload, stage=target_stage, entry_id=new_entry_id, history_path=history_path)

    def publish_stage(self, domain=None, *, author="system"):
        domains = [domain] if domain else list(self.pack_paths)
        plans = []
        candidate_payloads = {
            current_domain: self.load_pack(current_domain, stage="live")
            for current_domain in self.pack_paths
        }
        for current_domain in domains:
            draft_path = self._path_for(current_domain, stage="draft")
            if not draft_path.exists():
                continue
            live_before = self.load_pack(current_domain, stage="live")
            live_before_text = self._path_for(current_domain, stage="live").read_text(encoding="utf-8")
            draft_payload = self.load_pack(current_domain, stage="draft")
            persisted = self._stamp_payload(draft_payload, author=author, action="publish", target=current_domain, stage="live")
            diff = self.diff_pack(current_domain, persisted, stage="live")
            candidate_payloads[current_domain] = persisted
            plans.append(
                {
                    "domain": current_domain,
                    "live_before": live_before,
                    "live_before_text": live_before_text,
                    "persisted": persisted,
                    "diff": diff,
                    "path": self._path_for(current_domain, stage="live"),
                }
            )

        if not plans:
            return []

        from world.content.validation import validate_content_registry

        candidate_registry = build_content_registry_from_payloads(
            candidate_payloads,
            source_paths={key: self._path_for(key, stage="live") for key in self.pack_paths},
        )
        errors = validate_content_registry(candidate_registry)
        if errors:
            raise ContentPublishValidationError(errors, domains=[plan["domain"] for plan in plans])

        mutations = []
        recorded_paths = []
        try:
            for plan in plans:
                self.write_pack(plan["domain"], plan["persisted"], stage="live")
            for plan in plans:
                history_entry, recorded_path = self.history.record(
                    domain=plan["domain"],
                    stage="live",
                    action="publish",
                    target=plan["domain"],
                    path=str(plan["path"]),
                    diff=plan["diff"],
                    before=plan["live_before"],
                    after=plan["persisted"],
                    author=author,
                    extra={"source_stage": "draft"},
                )
                recorded_paths.append(recorded_path)
                mutations.append(ContentMutation(domain=plan["domain"], path=str(plan["path"]), diff=plan["diff"], payload=plan["persisted"], stage="live", entry_id=history_entry["entry_id"], history_path=str(recorded_path)))
        except Exception:
            for plan in plans:
                plan["path"].write_text(plan["live_before_text"], encoding="utf-8")
            for recorded_path in recorded_paths:
                try:
                    recorded_path.unlink()
                except FileNotFoundError:
                    pass
            raise
        return mutations

    def upsert_room(self, room_data, *, write=False, stage="live", author="system"):
        room_data = dict(room_data)
        room_data.setdefault("safe", False)
        room_id = room_data["id"]

        def updater(payload):
            rooms = list(payload.get("rooms", []))
            for index, existing in enumerate(rooms):
                if existing.get("id") == room_id:
                    rooms[index] = room_data
                    break
            else:
                rooms.append(room_data)
                rooms.sort(key=lambda entry: entry.get("id", ""))
            payload["rooms"] = rooms
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="upsert", target=room_id)

    def upsert_exit(self, exit_data, *, write=False, stage="live", author="system"):
        exit_id = exit_data["id"]

        def updater(payload):
            exits = list(payload.get("exits", []))
            for index, existing in enumerate(exits):
                if existing.get("id") == exit_id:
                    exits[index] = exit_data
                    break
            else:
                exits.append(exit_data)
                exits.sort(key=lambda entry: entry.get("id", ""))
            payload["exits"] = exits
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="upsert", target=exit_id)

    def upsert_entity(self, entity_data, *, write=False, stage="live", author="system"):
        entity_id = entity_data["id"]

        def updater(payload):
            entities = list(payload.get("entities", []))
            for index, existing in enumerate(entities):
                if existing.get("id") == entity_id:
                    entities[index] = entity_data
                    break
            else:
                entities.append(entity_data)
                entities.sort(key=lambda entry: entry.get("id", ""))
            payload["entities"] = entities
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="upsert", target=entity_id)

    def upsert_item(self, template_id, item_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            templates = dict(payload.get("item_templates", {}))
            templates[template_id] = item_data
            payload["item_templates"] = dict(sorted(templates.items()))
            return payload

        return self.apply_pack_update("items", updater, write=write, stage=stage, author=author, action="upsert", target=template_id)

    def upsert_race(self, race_key, race_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            races = dict(payload.get("races", {}))
            races[race_key] = race_data
            payload["races"] = dict(sorted(races.items()))
            return payload

        return self.apply_pack_update("characters", updater, write=write, stage=stage, author=author, action="upsert", target=race_key)

    def upsert_class(self, class_key, class_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            classes = dict(payload.get("classes", {}))
            classes[class_key] = class_data
            payload["classes"] = dict(sorted(classes.items()))
            return payload

        return self.apply_pack_update("characters", updater, write=write, stage=stage, author=author, action="upsert", target=class_key)

    def upsert_character_config(self, config_data, *, write=False, stage="live", author="system"):
        allowed = {
            "primary_stats",
            "starting_race",
            "starting_class",
            "max_level",
            "vertical_slice_classes",
            "xp_for_level",
            "ability_library",
            "implemented_ability_keys",
            "passive_ability_bonuses",
        }

        def updater(payload):
            for key, value in config_data.items():
                if key in allowed:
                    payload[key] = value
            return payload

        return self.apply_pack_update("characters", updater, write=write, stage=stage, author=author, action="upsert", target="character-config")

    def upsert_quest(self, quest_key, quest_data, *, region=None, add_starting=False, write=False, stage="live", author="system"):
        def updater(payload):
            quests = dict(payload.get("quests", {}))
            quest_regions = dict(payload.get("quest_regions", {}))
            starting_quests = list(payload.get("starting_quests", []))
            quests[quest_key] = quest_data
            if region is not None:
                quest_regions[quest_key] = region
            if add_starting and quest_key not in starting_quests:
                starting_quests.append(quest_key)
            payload["quests"] = dict(sorted(quests.items()))
            payload["quest_regions"] = dict(sorted(quest_regions.items()))
            payload["starting_quests"] = starting_quests
            return payload

        return self.apply_pack_update("quests", updater, write=write, stage=stage, author=author, action="upsert", target=quest_key)

    def upsert_dialogue_rules(self, entity_id, rules, *, write=False, stage="live", author="system"):
        def updater(payload):
            talk_rules = dict(payload.get("talk_rules", {}))
            talk_rules[entity_id] = list(rules)
            payload["talk_rules"] = dict(sorted(talk_rules.items()))
            return payload

        return self.apply_pack_update("dialogue", updater, write=write, stage=stage, author=author, action="upsert", target=entity_id)

    def upsert_static_read_response(self, entity_id, text, *, write=False, stage="live", author="system"):
        def updater(payload):
            responses = dict(payload.get("static_read_responses", {}))
            responses[entity_id] = text
            payload["static_read_responses"] = dict(sorted(responses.items()))
            return payload

        return self.apply_pack_update("dialogue", updater, write=write, stage=stage, author=author, action="upsert", target=entity_id)

    def upsert_enemy_template(self, template_key, template_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            templates = dict(payload.get("enemy_templates", {}))
            templates[template_key] = template_data
            payload["enemy_templates"] = dict(sorted(templates.items()))
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="upsert", target=template_key)

    def upsert_room_encounters(self, room_id, encounters, *, write=False, stage="live", author="system"):
        def updater(payload):
            room_encounters = dict(payload.get("room_encounters", {}))
            room_encounters[room_id] = list(encounters)
            payload["room_encounters"] = dict(sorted(room_encounters.items()))
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="upsert", target=room_id)

    def upsert_roaming_party(self, party_key, party_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            parties = [dict(entry) for entry in payload.get("roaming_parties", [])]
            next_party = dict(party_data)
            next_party["key"] = party_key
            for index, existing in enumerate(parties):
                if existing.get("key") == party_key:
                    parties[index] = next_party
                    break
            else:
                parties.append(next_party)
            parties.sort(key=lambda entry: entry.get("key", ""))
            payload["roaming_parties"] = parties
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="upsert", target=party_key)

    def upsert_portal(self, portal_key, portal_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            portals = dict(payload.get("portals", {}).get("portals", {}))
            portal_labels = dict(payload.get("portals", {}).get("portal_status_labels", {}))
            portals[portal_key] = portal_data
            payload.setdefault("portals", {})["portals"] = dict(sorted(portals.items()))
            payload["portals"]["portal_status_labels"] = dict(sorted(portal_labels.items()))
            return payload

        return self.apply_pack_update("systems", updater, write=write, stage=stage, author=author, action="upsert", target=portal_key)

    def upsert_forge_recipe(self, source_template_id, recipe_data, *, write=False, stage="live", author="system"):
        def updater(payload):
            forging = dict(payload.get("forging", {}))
            recipes = dict(forging.get("forge_recipes", {}))
            recipes[source_template_id] = recipe_data
            forging["forge_recipes"] = dict(sorted(recipes.items()))
            payload["forging"] = forging
            return payload

        return self.apply_pack_update("systems", updater, write=write, stage=stage, author=author, action="upsert", target=source_template_id)

    def delete_room(self, room_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            payload["rooms"] = [room for room in payload.get("rooms", []) if room.get("id") != room_id]
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="remove", target=room_id)

    def delete_exit(self, exit_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            payload["exits"] = [entry for entry in payload.get("exits", []) if entry.get("id") != exit_id]
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="remove", target=exit_id)

    def delete_entity(self, entity_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            payload["entities"] = [entry for entry in payload.get("entities", []) if entry.get("id") != entity_id]
            return payload

        return self.apply_pack_update("world", updater, write=write, stage=stage, author=author, action="remove", target=entity_id)

    def delete_item(self, template_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            templates = dict(payload.get("item_templates", {}))
            templates.pop(template_id, None)
            payload["item_templates"] = dict(sorted(templates.items()))
            return payload

        return self.apply_pack_update("items", updater, write=write, stage=stage, author=author, action="remove", target=template_id)

    def delete_race(self, race_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            races = dict(payload.get("races", {}))
            races.pop(race_key, None)
            payload["races"] = dict(sorted(races.items()))
            return payload

        return self.apply_pack_update("characters", updater, write=write, stage=stage, author=author, action="remove", target=race_key)

    def delete_class(self, class_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            classes = dict(payload.get("classes", {}))
            classes.pop(class_key, None)
            payload["classes"] = dict(sorted(classes.items()))
            if payload.get("starting_class") == class_key:
                payload["starting_class"] = next(iter(payload["classes"]), "")
            return payload

        return self.apply_pack_update("characters", updater, write=write, stage=stage, author=author, action="remove", target=class_key)

    def delete_quest(self, quest_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            quests = dict(payload.get("quests", {}))
            quest_regions = dict(payload.get("quest_regions", {}))
            starting_quests = [entry for entry in payload.get("starting_quests", []) if entry != quest_key]
            quests.pop(quest_key, None)
            quest_regions.pop(quest_key, None)
            payload["quests"] = dict(sorted(quests.items()))
            payload["quest_regions"] = dict(sorted(quest_regions.items()))
            payload["starting_quests"] = starting_quests
            return payload

        return self.apply_pack_update("quests", updater, write=write, stage=stage, author=author, action="remove", target=quest_key)

    def delete_dialogue_rules(self, entity_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            talk_rules = dict(payload.get("talk_rules", {}))
            talk_rules.pop(entity_id, None)
            payload["talk_rules"] = dict(sorted(talk_rules.items()))
            return payload

        return self.apply_pack_update("dialogue", updater, write=write, stage=stage, author=author, action="remove", target=entity_id)

    def delete_static_read_response(self, entity_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            responses = dict(payload.get("static_read_responses", {}))
            responses.pop(entity_id, None)
            payload["static_read_responses"] = dict(sorted(responses.items()))
            return payload

        return self.apply_pack_update("dialogue", updater, write=write, stage=stage, author=author, action="remove", target=entity_id)

    def delete_enemy_template(self, template_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            templates = dict(payload.get("enemy_templates", {}))
            templates.pop(template_key, None)
            payload["enemy_templates"] = dict(sorted(templates.items()))
            overrides = dict(payload.get("enemy_temperament_overrides", {}))
            overrides.pop(template_key, None)
            payload["enemy_temperament_overrides"] = dict(sorted(overrides.items()))
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="remove", target=template_key)

    def delete_room_encounters(self, room_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            room_encounters = dict(payload.get("room_encounters", {}))
            room_encounters.pop(room_id, None)
            payload["room_encounters"] = dict(sorted(room_encounters.items()))
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="remove", target=room_id)

    def delete_roaming_party(self, party_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            payload["roaming_parties"] = [entry for entry in payload.get("roaming_parties", []) if entry.get("key") != party_key]
            return payload

        return self.apply_pack_update("encounters", updater, write=write, stage=stage, author=author, action="remove", target=party_key)

    def delete_portal(self, portal_key, *, write=False, stage="live", author="system"):
        def updater(payload):
            portals_block = dict(payload.get("portals", {}))
            portals = dict(portals_block.get("portals", {}))
            portals.pop(portal_key, None)
            portals_block["portals"] = dict(sorted(portals.items()))
            payload["portals"] = portals_block
            return payload

        return self.apply_pack_update("systems", updater, write=write, stage=stage, author=author, action="remove", target=portal_key)

    def delete_forge_recipe(self, source_template_id, *, write=False, stage="live", author="system"):
        def updater(payload):
            forging = dict(payload.get("forging", {}))
            recipes = dict(forging.get("forge_recipes", {}))
            recipes.pop(source_template_id, None)
            forging["forge_recipes"] = dict(sorted(recipes.items()))
            payload["forging"] = forging
            return payload

        return self.apply_pack_update("systems", updater, write=write, stage=stage, author=author, action="remove", target=source_template_id)

    def _path_for(self, domain, *, stage="live"):
        try:
            if stage == "live":
                return self.pack_paths[domain]
            if stage == "draft":
                return self.draft_pack_paths[domain]
            raise KeyError(stage)
        except KeyError as exc:
            raise KeyError(f"Unknown content domain or stage: {domain} ({stage})") from exc

    def _default_history_root(self):
        first_path = next(iter(self.pack_paths.values()))
        return first_path.parent / ".history"

    @staticmethod
    def _build_default_draft_paths(pack_paths):
        return {key: path.parent / "drafts" / path.name for key, path in pack_paths.items()}

    @staticmethod
    def _serialize(payload):
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    @staticmethod
    def _stamp_payload(payload, *, author, action, target, stage):
        stamped = deepcopy(payload)
        stamped["_meta"] = {
            "last_modified_at": datetime.now(timezone.utc).isoformat(),
            "last_modified_by": author or "system",
            "last_action": action,
            "last_target": target,
            "stage": stage,
        }
        return stamped
