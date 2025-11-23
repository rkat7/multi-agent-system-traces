import json
import shutil
from pathlib import Path
from typing import Iterable, List, Tuple, Dict

ROOT = Path(__file__).resolve().parent
EXP_IN = ROOT / "experiment-input"
EXP_OUT = ROOT / "experiment-output"
COMBINED = ROOT / "experiment-steps"
MANIFEST = ROOT / "manifest"


def reset_dirs():
    """Recreate output directories to ensure clean runs."""
    for path in [EXP_IN, EXP_OUT, COMBINED, MANIFEST]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def split_events(lines: List[str]) -> List[List[str]]:
    """Group contiguous non-empty lines into events."""
    events: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                events.append(current)
                current = []
        else:
            current.append(line)
    if current:
        events.append(current)
    return events


def classify_event(event_lines: List[str]) -> Tuple[List[str], List[str]]:
    """Split a single event into input vs output segments."""
    inputs: List[str] = []
    outputs: List[str] = []

    i = 0
    n = len(event_lines)
    in_code_block = False
    while i < n:
        line = event_lines[i]
        stripped = line.lstrip()

        if in_code_block:
            inputs.append(line)
            if stripped.startswith("```"):
                in_code_block = False
            i += 1
            continue

        if stripped.startswith("Action:") or stripped == "Action:":
            inputs.append(line)
            # Pull following fenced code block (if any) into inputs.
            j = i + 1
            if j < n and event_lines[j].strip().startswith("```"):
                while j < n:
                    inputs.append(event_lines[j])
                    if j > i and event_lines[j].strip().startswith("```"):
                        break
                    j += 1
                i = j + 1
                continue
            i += 1
            continue

        if "Subgoal:" in line or "Planner->" in line:
            inputs.append(line)
            i += 1
            continue

        if stripped.startswith("Final Answer:") or "Final Answer:" in line:
            outputs.append(line)
            i += 1
            continue

        if (
            "Response:" in line
            or stripped.startswith("Thought:")
            or stripped.startswith("Observation:")
            or "Navigator->Planner:" in line
            or "Editor->Planner:" in line
            or "Executor->Planner:" in line
        ):
            outputs.append(line)
            i += 1
            continue

        # Default: treat as output to avoid dropping trace content.
        outputs.append(line)
        i += 1

    return inputs, outputs


def write_lines(path: Path, lines: List[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    if lines:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def process_trajectory(
    run_id: str,
    origin: Path,
    lines: Iterable[str],
    source: str,
    manifest: List[Dict],
):
    events = split_events([ln.rstrip("\n") for ln in lines])
    run_in_dir = EXP_IN / run_id
    run_out_dir = EXP_OUT / run_id
    run_combined_dir = COMBINED / run_id
    run_in_dir.mkdir(parents=True, exist_ok=True)
    run_out_dir.mkdir(parents=True, exist_ok=True)
    run_combined_dir.mkdir(parents=True, exist_ok=True)

    for idx, event in enumerate(events):
        step_id = f"step{idx:04d}"
        input_lines, output_lines = classify_event(event)

        input_path = run_in_dir / f"{step_id}_input.txt"
        output_path = run_out_dir / f"{step_id}_output.txt"
        combined_path = run_combined_dir / f"{step_id}.txt"

        write_lines(input_path, input_lines)
        write_lines(output_path, output_lines)
        combined_content = []
        combined_content.append("### Input")
        combined_content.extend(input_lines if input_lines else ["<empty>"])
        combined_content.append("")
        combined_content.append("### Output")
        combined_content.extend(output_lines if output_lines else ["<empty>"])
        write_lines(combined_path, combined_content)

        manifest.append(
            {
                "step_id": step_id,
                "source": source,
                "origin": str(origin.relative_to(ROOT)),
                "input_file": str(input_path.relative_to(ROOT)),
                "output_file": str(output_path.relative_to(ROOT)),
                "combined_file": str(combined_path.relative_to(ROOT)),
                "input_lines": len(input_lines),
                "output_lines": len(output_lines),
            }
        )


def process_json_trace(path: Path, manifest: List[Dict]):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    run_id = data.get("instance_id") or path.stem
    run_in_dir = EXP_IN / run_id
    run_out_dir = EXP_OUT / run_id
    run_in_dir.mkdir(parents=True, exist_ok=True)
    run_out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "instance_id": run_id,
        "source_file": str(path.name),
        "has_note": "note" in data and data["note"] is not None,
        "human_annotated": path.name.endswith("_human.json"),
    }
    (run_in_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    if "problem_statement" in data:
        write_lines(run_in_dir / "problem_statement.txt", data["problem_statement"])
    other = data.get("other_data", {})
    if "hints_text" in other:
        write_lines(run_in_dir / "hints.txt", other["hints_text"])
    if "patch" in other:
        write_lines(run_in_dir / "patch.txt", other["patch"])

    trajectory = data.get("trajectory", [])
    process_trajectory(run_id, path, trajectory, "trajectory", manifest)

    final_lines = [ln for ln in trajectory if "Final Answer:" in ln]
    if final_lines:
        write_lines(run_out_dir / "final_answer.txt", final_lines)


def process_raw_log(path: Path, manifest: List[Dict]):
    run_id = path.stem
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    process_trajectory(run_id, path, lines, "raw_log", manifest)


def main():
    reset_dirs()
    manifest_entries: Dict[str, List[Dict]] = {}

    for json_file in sorted(ROOT.glob("*.json")):
        if json_file.name in {"README.md"}:
            continue
        run_id = json_file.stem
        manifest_entries[run_id] = []
        process_json_trace(json_file, manifest_entries[run_id])

    raw_dir = ROOT / "raw_trajs"
    if raw_dir.exists():
        for log_file in sorted(raw_dir.glob("*.log")):
            run_id = log_file.stem
            manifest_entries.setdefault(run_id, [])
            process_raw_log(log_file, manifest_entries[run_id])

    for run_id, entries in manifest_entries.items():
        manifest_path = MANIFEST / f"{run_id}.json"
        manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
