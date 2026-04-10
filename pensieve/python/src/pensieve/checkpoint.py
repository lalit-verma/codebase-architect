"""Checkpoint/resume for the analyze pipeline.

Stores intermediate outputs under agent-docs/.checkpoints/ so that
reruns skip already-completed work when inputs haven't changed.

Fingerprint: SHA256(structure.json) + SHA256(graph.json) + model +
stage_version. If any of these change, all checkpoints are invalidated.

Stage outputs:
  - Stage 2: subsystem_map.json (SubsystemMap serialized)
  - Stage 3: selections/{name}.json (FileSelection per subsystem)
  - Stage 4: docs/{name}.md (SubsystemDoc markdown per subsystem)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

# Bump this when prompts or pipeline logic changes materially.
# Forces re-generation even if structure/graph haven't changed.
STAGE_VERSION = "v1"


def _sha256_file(path: Path) -> str:
    """SHA256 hex digest of a file's contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _sanitize_name(name: str) -> str:
    """Sanitize a subsystem name for use as a filename.

    Includes a short hash of the original name to prevent collisions
    between distinct names that sanitize to the same string
    (e.g., "A/B", "A B", "A_B" all sanitize to "a_b" without the hash).
    """
    safe = name.lower().replace(" ", "_").replace("/", "_")
    safe = "".join(c for c in safe if c.isalnum() or c in ("_", "-"))
    # Add a short hash of the ORIGINAL name to disambiguate collisions
    h = hashlib.sha256(name.encode("utf-8")).hexdigest()[:6]
    return f"{safe}_{h}"


class AnalyzeCheckpoint:
    """Manages checkpoint state for the analyze pipeline."""

    def __init__(self, output_dir: Path, model: str) -> None:
        self._checkpoint_dir = output_dir / ".checkpoints"
        self._model = model
        self._fingerprint: dict | None = None
        self._valid = False

    def _compute_fingerprint(self, structure_path: Path, graph_path: Path) -> dict:
        return {
            "structure_hash": _sha256_file(structure_path),
            "graph_hash": _sha256_file(graph_path),
            "model": self._model,
            "stage_version": STAGE_VERSION,
        }

    def validate(self, structure_path: Path, graph_path: Path) -> bool:
        """Check if existing checkpoints match current inputs.

        Returns True if checkpoints are valid and can be reused.
        Returns False if checkpoints are stale (caller should clear).
        """
        self._fingerprint = self._compute_fingerprint(structure_path, graph_path)

        fp_path = self._checkpoint_dir / "fingerprint.json"
        if not fp_path.exists():
            self._valid = False
            return False

        try:
            saved = json.loads(fp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._valid = False
            return False

        self._valid = saved == self._fingerprint
        return self._valid

    def save_fingerprint(self, structure_path: Path, graph_path: Path) -> None:
        """Save the current fingerprint."""
        self._fingerprint = self._compute_fingerprint(structure_path, graph_path)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        fp_path = self._checkpoint_dir / "fingerprint.json"
        fp_path.write_text(
            json.dumps(self._fingerprint, indent=2) + "\n",
            encoding="utf-8",
        )

    def clear(self) -> None:
        """Remove all checkpoint data."""
        import shutil
        if self._checkpoint_dir.exists():
            shutil.rmtree(self._checkpoint_dir)

    # --- Stage 2: Subsystem map ---

    def has_subsystem_map(self) -> bool:
        return self._valid and (self._checkpoint_dir / "subsystem_map.json").exists()

    def load_subsystem_map(self) -> dict | None:
        """Load cached subsystem map. Returns None if not available."""
        path = self._checkpoint_dir / "subsystem_map.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_subsystem_map(self, smap_data: dict) -> None:
        """Save subsystem map checkpoint."""
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        path = self._checkpoint_dir / "subsystem_map.json"
        path.write_text(json.dumps(smap_data, indent=2) + "\n", encoding="utf-8")

    # --- Stage 3: File selections ---

    def has_selection(self, subsystem_name: str) -> bool:
        if not self._valid:
            return False
        safe = _sanitize_name(subsystem_name)
        return (self._checkpoint_dir / "selections" / f"{safe}.json").exists()

    def load_selection(self, subsystem_name: str) -> dict | None:
        safe = _sanitize_name(subsystem_name)
        path = self._checkpoint_dir / "selections" / f"{safe}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_selection(self, subsystem_name: str, selection_data: dict) -> None:
        sel_dir = self._checkpoint_dir / "selections"
        sel_dir.mkdir(parents=True, exist_ok=True)
        safe = _sanitize_name(subsystem_name)
        path = sel_dir / f"{safe}.json"
        path.write_text(json.dumps(selection_data, indent=2) + "\n", encoding="utf-8")

    # --- Stage 4: Subsystem docs ---

    def has_doc(self, subsystem_name: str) -> bool:
        if not self._valid:
            return False
        safe = _sanitize_name(subsystem_name)
        return (self._checkpoint_dir / "docs" / f"{safe}.md").exists()

    def load_doc(self, subsystem_name: str) -> str | None:
        safe = _sanitize_name(subsystem_name)
        path = self._checkpoint_dir / "docs" / f"{safe}.md"
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def save_doc(self, subsystem_name: str, markdown: str) -> None:
        doc_dir = self._checkpoint_dir / "docs"
        doc_dir.mkdir(parents=True, exist_ok=True)
        safe = _sanitize_name(subsystem_name)
        path = doc_dir / f"{safe}.md"
        path.write_text(markdown, encoding="utf-8")
