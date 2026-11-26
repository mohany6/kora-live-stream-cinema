# -*- coding: utf-8 -*-
"""Syntax and structure tests for the serverless GitHub Actions cron workflow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "sync_and_publish.yml"

_KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_.-]+|\"[^\"]+\"|'[^']+'):(?:\s+(.*))?$")


def _strip_yaml_comment(line: str) -> str:
    """Strip an unquoted `#` comment from a YAML line."""
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single and (idx == 0 or line[idx - 1] != "\\"):
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or line[idx - 1].isspace():
                return line[:idx].rstrip()
    return line.rstrip()


def _parse_scalar(raw: str) -> Any:
    """Parse a scalar or inline flow list from YAML."""
    value = raw.strip()
    if value == "":
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _collect_block_scalar(
    raw_lines: list[str],
    idx: int,
    parent_indent: int,
) -> tuple[str, int]:
    """Read a `|` or `>` multiline scalar block."""
    block_lines: list[str] = []
    base_indent: int | None = None
    while idx < len(raw_lines):
        raw_line = raw_lines[idx]
        if raw_line.strip() == "":
            block_lines.append("")
            idx += 1
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent <= parent_indent:
            break
        if base_indent is None:
            base_indent = indent
        block_lines.append(raw_line[base_indent:])
        idx += 1
    while block_lines and block_lines[-1] == "":
        block_lines.pop()
    return "\n".join(block_lines), idx


def _parse_block(
    tokens: list[tuple[int, str, int]],
    raw_lines: list[str],
    idx: int,
    expected_indent: int,
) -> tuple[Any, int]:
    """Parse an indented YAML mapping or sequence starting at `idx`."""
    if idx >= len(tokens):
        return {}, idx

    _, first_text, _ = tokens[idx]
    if first_text == "-" or first_text.startswith("- "):
        return _parse_sequence(tokens, raw_lines, idx, expected_indent)
    return _parse_mapping(tokens, raw_lines, idx, expected_indent)


def _parse_sequence(
    tokens: list[tuple[int, str, int]],
    raw_lines: list[str],
    idx: int,
    seq_indent: int,
) -> tuple[list[Any], int]:
    items: list[Any] = []
    while idx < len(tokens):
        indent, text, line_no = tokens[idx]
        if indent < seq_indent:
            break
        if indent > seq_indent or not (text == "-" or text.startswith("- ")):
            break

        rest = text[1:].strip()
        idx += 1

        if not rest:
            if idx < len(tokens) and tokens[idx][0] > seq_indent:
                child, idx = _parse_block(tokens, raw_lines, idx, tokens[idx][0])
                items.append(child)
            else:
                items.append(None)
            continue

        match = _KEY_VALUE_RE.match(rest)
        if match:
            item_indent = seq_indent + 2
            entry: dict[str, Any] = {}
            key = str(_parse_scalar(match.group(1)))
            val_raw = (match.group(2) or "").strip()
            if val_raw in {"|", "|-", ">", ">-"}:
                entry[key], raw_idx = _collect_block_scalar(raw_lines, line_no + 1, seq_indent)
                while idx < len(tokens) and tokens[idx][2] < raw_idx:
                    idx += 1
            elif val_raw == "":
                if idx < len(tokens) and tokens[idx][0] > item_indent:
                    entry[key], idx = _parse_block(tokens, raw_lines, idx, tokens[idx][0])
                else:
                    entry[key] = None
            else:
                entry[key] = _parse_scalar(val_raw)

            if idx < len(tokens) and tokens[idx][0] > seq_indent:
                sub_indent = tokens[idx][0]
                more, idx = _parse_mapping(tokens, raw_lines, idx, sub_indent)
                entry.update(more)
            items.append(entry)
        else:
            items.append(_parse_scalar(rest))
    return items, idx


def _parse_mapping(
    tokens: list[tuple[int, str, int]],
    raw_lines: list[str],
    idx: int,
    map_indent: int,
) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while idx < len(tokens):
        indent, text, line_no = tokens[idx]
        if indent < map_indent:
            break
        if indent > map_indent:
            raise ValueError(f"Unexpected indentation at line {line_no + 1}: {text!r}")
        if text == "-" or text.startswith("- "):
            break

        match = _KEY_VALUE_RE.match(text)
        if not match:
            raise ValueError(f"Invalid YAML mapping entry at line {line_no + 1}: {text!r}")

        key = str(_parse_scalar(match.group(1)))
        val_raw = (match.group(2) or "").strip()
        idx += 1

        if val_raw in {"|", "|-", ">", ">-"}:
            mapping[key], raw_idx = _collect_block_scalar(raw_lines, line_no + 1, indent)
            while idx < len(tokens) and tokens[idx][2] < raw_idx:
                idx += 1
        elif val_raw == "":
            if idx < len(tokens) and (
                tokens[idx][0] > indent
                or (
                    tokens[idx][0] == indent
                    and (tokens[idx][1] == "-" or tokens[idx][1].startswith("- "))
                )
            ):
                mapping[key], idx = _parse_block(tokens, raw_lines, idx, tokens[idx][0])
            else:
                mapping[key] = None
        else:
            mapping[key] = _parse_scalar(val_raw)
    return mapping, idx


def _parse_workflow_yaml(content: str) -> dict[str, Any]:
    """Parse workflow YAML using PyYAML when present, else built-in strict parser."""
    raw_lines = content.splitlines()
    for line_no, raw_line in enumerate(raw_lines, start=1):
        leading = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
        if "\t" in leading:
            raise ValueError(f"Tab indentation is not allowed in YAML (line {line_no})")

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        yaml = None

    if yaml is not None:
        loaded = yaml.safe_load(content)
        assert isinstance(loaded, dict)
        return loaded

    tokens: list[tuple[int, str, int]] = []
    for line_no, raw_line in enumerate(raw_lines):
        cleaned = _strip_yaml_comment(raw_line)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        tokens.append((indent, cleaned.strip(), line_no))

    parsed, next_idx = _parse_mapping(tokens, raw_lines, 0, tokens[0][0])
    assert next_idx == len(tokens), f"Unparsed YAML tokens remaining at index {next_idx}"
    return parsed


def _load_workflow() -> tuple[str, dict[str, Any]]:
    assert WORKFLOW_PATH.exists(), f"Missing workflow file: {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    parsed = _parse_workflow_yaml(content)
    return content, parsed


def _get_triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    triggers = workflow.get("on")
    if triggers is None:
        triggers = workflow.get(True)
    assert isinstance(triggers, dict), "Workflow `on` triggers section must be a mapping"
    return triggers


def test_sync_and_publish_workflow_exists_and_valid_yaml() -> None:
    _, workflow = _load_workflow()
    assert workflow.get("name")
    assert workflow.get("permissions", {}).get("contents") == "write"
    assert "sync-and-publish" in workflow.get("jobs", {})


def test_workflow_triggers_schedule_dispatch_and_push() -> None:
    _, workflow = _load_workflow()
    triggers = _get_triggers(workflow)

    schedule = triggers.get("schedule")
    assert isinstance(schedule, list) and schedule, "Schedule trigger is required"
    crons = [entry.get("cron") for entry in schedule if isinstance(entry, dict)]
    assert "*/20 * * * *" in crons

    assert "workflow_dispatch" in triggers

    push_cfg = triggers.get("push")
    assert isinstance(push_cfg, dict)
    branches = push_cfg.get("branches", [])
    assert "main" in branches
    assert "master" in branches


def test_workflow_contains_required_steps_and_secrets() -> None:
    _, workflow = _load_workflow()
    job = workflow["jobs"]["sync-and-publish"]
    assert job["runs-on"] == "ubuntu-latest"
    assert "HAS_CLOUDFLARE_PAGES" in job.get("env", {})
    assert "secrets.CLOUDFLARE_API_TOKEN" in str(job["env"]["HAS_CLOUDFLARE_PAGES"])
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in str(job["env"]["HAS_CLOUDFLARE_PAGES"])

    steps = job["steps"]
    assert isinstance(steps, list) and len(steps) >= 8

    # Ensure no step uses secrets.* directly inside `if:` conditions (invalid in GitHub Actions)
    for step in steps:
        step_if = str(step.get("if", ""))
        assert "secrets." not in step_if, f"Step '{step.get('name')}' must not access secrets in 'if:' expression: {step_if}"

    uses_values = [step.get("uses", "") for step in steps]
    assert any(u.startswith("actions/checkout@v4") for u in uses_values)
    assert any(u.startswith("actions/setup-python@v5") for u in uses_values)
    assert any(u.startswith("actions/setup-node@v4") for u in uses_values)
    assert any(u.startswith("cloudflare/pages-action@v1") for u in uses_values)

    checkout_step = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@v4"))
    assert int(checkout_step["with"]["fetch-depth"]) == 0

    python_step = next(s for s in steps if s.get("uses", "").startswith("actions/setup-python@v5"))
    assert str(python_step["with"]["python-version"]) == "3.12"

    node_step = next(s for s in steps if s.get("uses", "").startswith("actions/setup-node@v4"))
    assert str(node_step["with"]["node-version"]) == "22"

    run_commands = "\n".join(str(step.get("run", "")) for step in steps)
    assert "pip install -r requirements.txt" in run_commands
    assert "scripts/export_static_streams.py" in run_commands
    assert "scripts/auto_blogger_publisher.py" in run_commands
    assert "npm ci" in run_commands
    assert "npm run build" in run_commands
    assert "[skip ci]" in run_commands
    assert "frontend/public/data/matches.json" in run_commands
    assert "data/matches.json" in run_commands
    assert "data/published_articles.json" in run_commands

    publish_step = next(
        s for s in steps if "auto_blogger_publisher.py" in str(s.get("run", ""))
    )
    publish_env = publish_step.get("env", {})
    for secret_name in (
        "BLOGGER_BLOG_ID",
        "BLOGGER_CLIENT_SECRETS",
        "BLOGGER_ACCESS_TOKEN",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "BLOGGER_PUBLISH_EMAIL",
    ):
        assert secret_name in publish_env
        assert f"secrets.{secret_name}" in str(publish_env[secret_name])

    cf_step = next(
        s for s in steps if s.get("uses", "").startswith("cloudflare/pages-action@v1")
    )
    assert cf_step["with"]["directory"] == "frontend/dist"
    assert "secrets.CLOUDFLARE_API_TOKEN" in str(cf_step["with"]["apiToken"])
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" in str(cf_step["with"]["accountId"])
    assert cf_step.get("if") == "env.HAS_CLOUDFLARE_PAGES == 'true'"

    artifact_step = next(
        s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@v4")
    )
    assert artifact_step.get("if") == "env.HAS_CLOUDFLARE_PAGES != 'true'"
