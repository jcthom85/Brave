"""Durable Codex agent run records for Creator workflows."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import re
from pathlib import Path

from world.content.editor import PACK_PATHS


RUN_STATUSES = ("planned", "validated", "dry_run", "applied", "verified", "reviewed", "publish_blocked", "published", "failed")
_RUN_ID_RE = re.compile(r"[^a-z0-9_.-]+")


class AgentRunStore:
    """Persist full Codex authoring runs as JSON records."""

    def __init__(self, root=None):
        self.root = Path(root or self.default_root())
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, *, instructions, scope=None, mutations=None, plan=None, author="codex-cli"):
        now = _now()
        run_id = self._build_run_id(now, instructions)
        payload = {
            "run_id": run_id,
            "created_at": now,
            "updated_at": now,
            "author": author or "codex-cli",
            "status": "planned",
            "instructions": str(instructions or "").strip(),
            "scope": scope or {},
            "plan": plan or {},
            "mutations": mutations or [],
            "validation": None,
            "dry_run": None,
            "apply": None,
            "verify": None,
            "publish": None,
            "review_notes": [],
        }
        if not payload["instructions"]:
            raise ValueError("Agent run requires instructions.")
        self._write(payload)
        return payload

    def list(self, *, limit=20):
        entries = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            entries.append(payload)
            if len(entries) >= limit:
                break
        return entries

    def get(self, run_id):
        path = self._path(run_id)
        if not path.exists():
            raise KeyError(f"Unknown agent run: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, run_id, *, status=None, **fields):
        payload = self.get(run_id)
        if status:
            if status not in RUN_STATUSES:
                raise ValueError(f"Unknown agent run status: {status}")
            payload["status"] = status
        for key, value in fields.items():
            payload[key] = value
        payload["updated_at"] = _now()
        self._write(payload)
        return payload

    def append_review_note(self, run_id, note, *, author="human"):
        payload = self.get(run_id)
        notes = list(payload.get("review_notes") or [])
        notes.append({"timestamp": _now(), "author": author or "human", "note": str(note or "").strip()})
        return self.update(run_id, status="reviewed", review_notes=notes)

    def _write(self, payload):
        self._path(payload["run_id"]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _path(self, run_id):
        safe_id = _RUN_ID_RE.sub("-", str(run_id or "").lower()).strip("-")
        if not safe_id:
            raise KeyError("Agent run id is required.")
        return self.root / f"{safe_id}.json"

    @staticmethod
    def _build_run_id(timestamp, instructions):
        slug = _RUN_ID_RE.sub("-", str(instructions or "agent-run").lower()).strip("-")
        return f"{timestamp.replace(':', '').replace('-', '').replace('.', '')[:21]}-{slug[:48] or 'agent-run'}"

    @staticmethod
    def default_root():
        first_path = next(iter(PACK_PATHS.values()))
        return Path(first_path).parent / ".agent-runs"


def _now():
    return datetime.now(timezone.utc).isoformat()


def run_summary(payload):
    return {
        "run_id": payload.get("run_id"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "author": payload.get("author"),
        "status": payload.get("status"),
        "instructions": payload.get("instructions"),
        "mutation_count": len(payload.get("mutations") or []),
        "touched_domains": ((payload.get("validation") or {}).get("touched_domains") or (payload.get("apply") or {}).get("touched_domains") or []),
    }


def clone_run_payload(payload):
    return deepcopy(payload)
