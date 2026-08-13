#!/usr/bin/env python3
"""Keep the task flowchart colors synchronized with an Orca orchestration run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


STATUS_CLASSES = {
    "done": "classDef done fill:#dcfce7,stroke:#22c55e,stroke-width:1.5px,color:#14532d",
    "pending": "classDef pending fill:#f1f5f9,stroke:#94a3b8,stroke-width:1.5px,color:#334155",
    "in_progress": "classDef in_progress fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#92400e",
    "failed": "classDef failed fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b",
}

ORCA_TO_DIAGRAM = {
    "completed": "done",
    "dispatched": "in_progress",
    "failed": "failed",
}


def load_run_state(spec_dir: Path) -> tuple[str, dict[str, str]]:
    state_path = spec_dir / "sidecars" / "orca_run.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return state["run_id"], state["tasks_map"]


def fetch_orca_statuses(run_id: str, task_ids: dict[str, str]) -> dict[str, str]:
    result = subprocess.run(
        ["orca", "orchestration", "task-list", "--run", run_id, "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    if not payload.get("ok"):
        raise RuntimeError(
            payload.get("error", {}).get("message", "Orca task-list failed")
        )

    dotted_by_orca_id = {orca_id: dotted for dotted, orca_id in task_ids.items()}
    statuses: dict[str, str] = {}
    for task in payload["result"]["tasks"]:
        dotted = dotted_by_orca_id.get(task["id"])
        if dotted:
            statuses[dotted] = ORCA_TO_DIAGRAM.get(task["status"], "pending")
    return statuses


def update_flowchart(tasks_path: Path, statuses: dict[str, str]) -> bool:
    content = tasks_path.read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)(^## Stage and Dependency Overview\s*\n\s*```mermaid\s*\n)(.*?)(```(?=\n|$))",
        content,
    )
    if not match:
        raise RuntimeError(
            f"No Stage and Dependency Overview Mermaid block in {tasks_path}"
        )

    diagram = match.group(2)
    diagram = re.sub(
        r"(?m)^\s*classDef (?:done|pending|in_progress|failed)\b.*\n?",
        "",
        diagram,
    )
    definitions = "\n".join(f"  {line}" for line in STATUS_CLASSES.values())
    diagram = re.sub(
        r"(?m)^(flowchart\s+\w+\s*)$",
        rf"\1\n{definitions}",
        diagram,
        count=1,
    )

    for dotted_id, status in statuses.items():
        node_id = "n_" + dotted_id.replace(".", "_")
        diagram = re.sub(
            rf"(?m)^\s*class\s+{re.escape(node_id)}\s+\w+\s*$",
            f"  class {node_id} {status}",
            diagram,
        )

    diagram = diagram.rstrip() + "\n"
    updated = content[: match.start(2)] + diagram + content[match.end(2) :]
    if updated == content:
        return False

    temp_path = tasks_path.with_suffix(tasks_path.suffix + ".tmp")
    temp_path.write_text(updated, encoding="utf-8")
    os.replace(temp_path, tasks_path)
    return True


def sync_once(spec_dir: Path) -> bool:
    run_id, task_ids = load_run_state(spec_dir)
    statuses = fetch_orca_statuses(run_id, task_ids)
    changed = update_flowchart(spec_dir / "04_tasks.md", statuses)
    if changed:
        print(f"Updated flowchart from Orca run {run_id}", flush=True)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_dir", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=10.0)
    args = parser.parse_args()

    spec_dir = args.spec_dir.resolve()
    if not args.watch:
        sync_once(spec_dir)
        return 0

    print(f"Watching Orca task status every {args.interval:g}s", flush=True)
    while True:
        try:
            sync_once(spec_dir)
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
            print(f"Flowchart sync skipped: {exc}", file=sys.stderr, flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
