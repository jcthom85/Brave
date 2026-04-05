"""History helpers for Brave creator content mutations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path


_HISTORY_ID_RE = re.compile(r"[^a-z0-9_.-]+")


class ContentHistoryStore:
    """Persist content mutation history as JSON snapshots."""

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def record(self, *, domain, stage, action, target, path, diff, before, after, author="system", extra=None):
        timestamp = datetime.now(timezone.utc)
        entry_id = self._build_entry_id(timestamp, domain, action, target)
        payload = {
            "entry_id": entry_id,
            "timestamp": timestamp.isoformat(),
            "domain": domain,
            "stage": stage,
            "action": action,
            "target": target,
            "path": path,
            "author": author or "system",
            "diff": diff,
            "before": before,
            "after": after,
        }
        if extra:
            payload["extra"] = extra
        entry_path = self.root / f"{entry_id}.json"
        entry_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload, entry_path

    def list_entries(self, *, domain=None, stage=None, limit=20):
        entries = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if domain and payload.get("domain") != domain:
                continue
            if stage and payload.get("stage") != stage:
                continue
            entries.append(payload)
            if len(entries) >= limit:
                break
        return entries

    def get(self, entry_id):
        path = self.root / f"{entry_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown content history entry: {entry_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _build_entry_id(timestamp, domain, action, target):
        suffix = _HISTORY_ID_RE.sub("-", f"{domain}-{action}-{target or 'global'}".lower()).strip("-")
        return f"{timestamp.strftime('%Y%m%d%H%M%S%f')}-{suffix[:72]}"
