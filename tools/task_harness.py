#!/usr/bin/env python3
"""Synchronize project status, validate repository facts, and optionally publish changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "hana-ppt-skill"
STATE_PATH = REPO_ROOT / "project-state.json"
STATUS_PATH = REPO_ROOT / "docs" / "STATUS.md"
ASSETS_ROOT = SKILL_ROOT / "assets"
HARNESS_STATE_PATH = REPO_ROOT / ".git" / "hana-task-harness.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def render_status(state: dict[str, Any]) -> str:
    labels = {
        "completed": "완료",
        "in_progress": "진행 중",
        "candidate": "후보 완료",
        "not_started": "미착수",
    }
    lines = [
        "# 현재 프로젝트 상태",
        "",
        "<!-- 이 파일은 project-state.json에서 생성됩니다. 직접 편집하지 마세요. -->",
        "",
        f"- 갱신일: `{state['updated_at']}`",
        f"- 현재 단계: `{state['current_phase']}`",
        f"- 요약: {state['summary']}",
        "",
        "## 단계별 상태",
        "",
        "| 단계 | 상태 | 근거 | 남은 항목 |",
        "|---|---|---|---|",
    ]
    for phase in state["phases"]:
        evidence = "<br>".join(f"`{item}`" for item in phase.get("evidence", [])) or "-"
        missing = "<br>".join(phase.get("missing", [])) or "-"
        status = labels.get(phase["status"], phase["status"])
        lines.append(f"| {phase['label']} | {status} | {evidence} | {missing} |")
    refs = state["references"]
    lines.extend(
        [
            "",
            "## 레퍼런스 상태",
            "",
            f"- 스타일 학습 포함: {', '.join(f'`{x}`' for x in refs['style_learning'])}",
            "- 스타일 학습 제외: "
            + ", ".join(f"`{x}`" for x in refs["excluded_from_style_learning"]),
            f"- 주의: {refs['warning']}",
            "",
            "## 다음 작업",
            "",
        ]
    )
    lines.extend(f"{index}. {item}" for index, item in enumerate(state["next_actions"], 1))
    return "\n".join(lines) + "\n"


def sync_status() -> None:
    state = load_json(STATE_PATH)
    STATUS_PATH.write_text(render_status(state), encoding="utf-8", newline="\n")
    print(f"상태 문서 생성: {relative(STATUS_PATH)}")


def validate_state() -> list[str]:
    errors: list[str] = []
    state = load_json(STATE_PATH)
    allowed = {"completed", "in_progress", "candidate", "not_started"}
    for phase in state["phases"]:
        if phase["status"] not in allowed:
            errors.append(f"알 수 없는 단계 상태: {phase['id']}={phase['status']}")
        for evidence in phase.get("evidence", []):
            if not (REPO_ROOT / evidence).exists():
                errors.append(f"상태 근거 파일 없음: {evidence}")
    expected = render_status(state)
    actual = STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists() else ""
    if actual != expected:
        errors.append("docs/STATUS.md가 project-state.json과 다릅니다. sync를 실행하세요.")
    return errors


def validate_assets() -> list[str]:
    errors: list[str] = []
    manifest = load_json(ASSETS_ROOT / "asset-manifest.json")
    manifest_paths: set[str] = set()
    for asset in manifest["assets"]:
        manifest_paths.add(asset["path"])
        path = ASSETS_ROOT / asset["path"]
        if not path.is_file():
            errors.append(f"매니페스트 자산 없음: {asset['path']}")
            continue
        data = path.read_bytes()
        if len(data) != asset["size"]:
            errors.append(f"자산 크기 불일치: {asset['path']}")
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            errors.append(f"자산 해시 불일치: {asset['path']}")
    analysis = load_json(ASSETS_ROOT / "reference-analysis.json")
    baseline_paths = {item["path"] for item in analysis["baselines"]}
    actual_baselines = {
        relative(path).removeprefix("hana-ppt-skill/assets/")
        for path in (ASSETS_ROOT / "baselines").glob("*")
        if path.is_file()
    }
    if baseline_paths != actual_baselines:
        errors.append(
            "기준 이미지 목록 불일치: "
            f"JSON 전용={sorted(baseline_paths - actual_baselines)}, "
            f"파일 전용={sorted(actual_baselines - baseline_paths)}"
        )
    if not baseline_paths.issubset(manifest_paths):
        errors.append(f"매니페스트에 없는 기준 이미지: {sorted(baseline_paths - manifest_paths)}")
    sources = load_json(ASSETS_ROOT / "reference-decks" / "sources.json")
    excluded = {
        item["id"] for item in sources["documents"] if item.get("style_status") == "excluded-by-user"
    }
    used_sources = {item["source_id"] for item in analysis["baselines"]}
    if excluded & used_sources:
        errors.append(f"제외 레퍼런스가 기준 이미지에 포함됨: {sorted(excluded & used_sources)}")
    return errors


def validate_skill() -> list[str]:
    errors: list[str] = []
    required = [SKILL_ROOT / "SKILL.md", SKILL_ROOT / "agents" / "openai.yaml"]
    for path in required:
        if not path.is_file():
            errors.append(f"스킬 필수 파일 없음: {relative(path)}")
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n") or "name: hana-ppt-skill" not in skill_text:
        errors.append("SKILL.md frontmatter가 올바르지 않습니다.")
    return errors


def run_check() -> None:
    errors = validate_state() + validate_assets() + validate_skill()
    if errors:
        for error in errors:
            print(f"오류: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("검증 통과: 상태 문서, JSON, 자산, 기준 이미지와 스킬 구조가 동기화되었습니다.")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def begin() -> None:
    try:
        status = git("status", "--porcelain").stdout.strip()
    except FileNotFoundError as exc:
        raise SystemExit("git 실행 파일을 찾을 수 없습니다.") from exc
    if status:
        raise SystemExit(
            "작업 시작 전 Git 트리가 깨끗하지 않습니다. 기존 변경의 소유권을 확인하고 먼저 정리하세요.\n"
            + status
        )
    snapshot = {
        "head": git("rev-parse", "HEAD").stdout.strip(),
        "branch": git("branch", "--show-current").stdout.strip(),
    }
    if not snapshot["branch"]:
        raise SystemExit("detached HEAD에서는 자동 게시를 시작하지 않습니다.")
    HARNESS_STATE_PATH.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    print(f"작업 시작 기록: {snapshot['branch']}@{snapshot['head'][:12]}")


def install_skill(destination: str | None) -> None:
    target = (
        Path(destination).expanduser().resolve()
        if destination
        else (Path.home() / ".codex" / "skills" / "hana-ppt-skill").resolve()
    )
    if target == SKILL_ROOT.resolve():
        print("저장소의 스킬 폴더 자체가 대상이므로 설치를 생략합니다.")
        return
    if target.exists():
        marker = target / "SKILL.md"
        if not marker.is_file() or "name: hana-ppt-skill" not in marker.read_text(encoding="utf-8"):
            raise SystemExit(f"기존 대상이 하나증권 스킬로 확인되지 않아 덮어쓰지 않습니다: {target}")
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_ROOT, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"스킬 설치 완료: {target}")


def finish(message: str, no_push: bool) -> None:
    if not re.search(r"[가-힣]", message):
        raise SystemExit("커밋 메시지에는 한글을 포함해야 합니다.")
    if not HARNESS_STATE_PATH.is_file():
        raise SystemExit("작업 시작 기록이 없습니다. 깨끗한 Git 트리에서 begin을 먼저 실행하세요.")
    snapshot = load_json(HARNESS_STATE_PATH)
    current_head = git("rev-parse", "HEAD").stdout.strip()
    current_branch = git("branch", "--show-current").stdout.strip()
    if current_head != snapshot["head"] or current_branch != snapshot["branch"]:
        raise SystemExit("작업 중 HEAD 또는 브랜치가 변경되어 자동 게시를 중단합니다.")
    sync_status()
    run_check()
    try:
        status = git("status", "--porcelain").stdout.strip()
    except FileNotFoundError as exc:
        raise SystemExit("git 실행 파일을 찾을 수 없어 자동 커밋·푸시를 수행하지 못했습니다.") from exc
    if not status:
        print("변경 파일이 없어 커밋하지 않습니다.")
        return
    print("커밋 대상 변경:\n" + status)
    git("add", "-A")
    git("commit", "-m", message)
    branch = git("branch", "--show-current").stdout.strip()
    if not branch:
        raise SystemExit("현재 브랜치를 확인할 수 없습니다.")
    if not no_push:
        git("push", "--set-upstream", "origin", branch)
        print(f"푸시 완료: origin/{branch}")
    else:
        print(f"커밋 완료: {branch} (푸시 생략)")
    HARNESS_STATE_PATH.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("begin", help="깨끗한 Git 시작 상태를 기록합니다.")
    subparsers.add_parser("sync", help="project-state.json에서 docs/STATUS.md를 생성합니다.")
    subparsers.add_parser("check", help="상태·문서·자산·스킬 구조를 검증합니다.")
    install_parser = subparsers.add_parser("install", help="저장소의 스킬 정본을 Codex 스킬 폴더에 설치합니다.")
    install_parser.add_argument("--destination", help="기본 설치 경로 대신 사용할 대상 폴더")
    finish_parser = subparsers.add_parser("finish", help="동기화·검증·커밋·푸시를 실행합니다.")
    finish_parser.add_argument("--message", required=True, help="한글 커밋 메시지")
    finish_parser.add_argument("--no-push", action="store_true", help="커밋만 하고 푸시하지 않습니다.")
    args = parser.parse_args()
    if args.command == "begin":
        begin()
    elif args.command == "sync":
        sync_status()
    elif args.command == "check":
        run_check()
    elif args.command == "install":
        install_skill(args.destination)
    else:
        finish(args.message, args.no_push)


if __name__ == "__main__":
    main()
