#!/usr/bin/env python3
"""Regenerate the package-ready manual from a clean GitBook main snapshot.

The raw product export stays on ``main``. Run this command from the optimized
``4.5`` branch after fetching the latest main branch:

  python -m pip install -r tools/requirements-avif.txt
  git fetch origin main
  python tools/refresh_manual_avif.py --source-ref origin/main --dry-run
  python tools/refresh_manual_avif.py --source-ref origin/main

The source snapshot is checked out into a temporary detached worktree. The
current ``docs/`` tree is replaced only after conversion and all gates pass.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


class RefreshError(RuntimeError):
    pass


def run_command(command, *, capture=True):
    kwargs = {
        "encoding": "utf-8",
        "errors": "replace",
        "text": True,
    }
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subprocess.run(command, **kwargs)
    if result.returncode:
        if capture:
            detail = (result.stderr or result.stdout).strip()
        else:
            detail = "see command output above"
        raise RefreshError(
            f"command failed ({result.returncode}): {' '.join(map(str, command))}\n{detail}"
        )
    return result.stdout.strip() if capture else ""


def run_git(repo, *args):
    return run_command(["git", "-C", str(repo), *map(str, args)])


def resolve_repo(script_path):
    root = run_git(script_path.parent, "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def is_within(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ensure_target(repo, target_branch, allow_dirty):
    branch = run_git(repo, "branch", "--show-current")
    if branch != target_branch:
        raise RefreshError(
            f"run from optimized branch {target_branch!r}; current branch is {branch!r}"
        )

    status = run_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status and not allow_dirty:
        preview = "\n".join(status.splitlines()[:20])
        raise RefreshError(
            "target worktree must be clean before replacing docs:\n" + preview
        )
    if status:
        print("[target] dirty worktree allowed because --dry-run does not replace docs")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(root):
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, file_hash(path))
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def compare_trees(current_docs, staged_docs):
    current = build_manifest(current_docs)
    staged = build_manifest(staged_docs)
    current_names = set(current)
    staged_names = set(staged)
    added = sorted(staged_names - current_names)
    removed = sorted(current_names - staged_names)
    changed = sorted(
        name for name in current_names & staged_names if current[name] != staged[name]
    )
    return current, staged, added, removed, changed


def tree_size(manifest):
    return sum(size for size, _digest in manifest.values())


def mib(size):
    return size / 2**20


def print_tree_diff(current, staged, added, removed, changed):
    print(
        "[diff] "
        f"files {len(current)} -> {len(staged)}  "
        f"size {mib(tree_size(current)):.2f} -> {mib(tree_size(staged)):.2f} MiB  "
        f"added={len(added)} removed={len(removed)} changed={len(changed)}"
    )
    for label, paths in (("added", added), ("removed", removed), ("changed", changed)):
        if paths:
            print(f"[diff] first {label}: {', '.join(paths[:10])}")


def optimize_snapshot(repo, staged_worktree, args):
    optimizer = repo / "tools" / "optimize_manual_avif.py"
    command = [
        sys.executable,
        str(optimizer),
        "--docs",
        str(staged_worktree / "docs"),
        "--quality",
        str(args.quality),
        "--subsampling",
        args.subsampling,
        "--speed",
        str(args.speed),
        "--budget-mib",
        str(args.budget_mib),
        "--delete-unreferenced",
    ]
    if args.cache_dir:
        command.extend(("--cache-dir", str(args.cache_dir)))
    run_command(command, capture=False)

    report_path = staged_worktree / "_avif_report.json"
    if not report_path.is_file():
        raise RefreshError(f"optimizer did not produce report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("broken_refs") != 0:
        raise RefreshError("optimizer report contains broken image references")
    if report.get("avif_decode_failures") != 0:
        raise RefreshError("optimizer report contains AVIF decode failures")
    if report.get("lightbox_runtime_failures") != 0:
        raise RefreshError("optimizer report contains unsafe lightbox links")
    if float(report.get("after_mib", args.budget_mib + 1)) > args.budget_mib:
        raise RefreshError("optimizer report exceeds the configured size budget")
    return report


def replace_docs(repo, staged_docs):
    target_docs = repo / "docs"
    token = uuid.uuid4().hex
    swap_root = repo / f".manual-refresh-{token}"
    incoming = swap_root / "incoming-docs"
    backup = swap_root / "previous-docs"

    swap_root.mkdir()
    target_moved = False
    target_installed = False
    try:
        shutil.copytree(staged_docs, incoming, copy_function=shutil.copy2)
        target_docs.rename(backup)
        target_moved = True
        try:
            incoming.rename(target_docs)
            target_installed = True
        except Exception:
            if not target_docs.exists() and backup.exists():
                backup.rename(target_docs)
            raise
    finally:
        # If restoration itself fails, retain the backup for manual recovery.
        if swap_root.exists() and target_docs.exists():
            shutil.rmtree(swap_root)
        elif target_moved and not target_installed:
            print(f"[recovery] previous docs retained at {backup}", file=sys.stderr)


def refresh(args):
    script_path = Path(__file__).resolve()
    repo = resolve_repo(script_path)
    ensure_target(repo, args.target_branch, allow_dirty=args.dry_run)

    target_docs = repo / "docs"
    if not (target_docs / "index.html").is_file():
        raise RefreshError(f"target docs tree is invalid: {target_docs}")

    source_commit = run_git(
        repo, "rev-parse", "--verify", f"{args.source_ref}^{{commit}}"
    )
    print(f"[source] {args.source_ref} -> {source_commit}")

    staging_root = args.staging_root.resolve() if args.staging_root else None
    if staging_root:
        staging_root.mkdir(parents=True, exist_ok=True)
        if is_within(staging_root, repo):
            raise RefreshError("--staging-root must be outside the target repository")

    if args.cache_dir:
        args.cache_dir = args.cache_dir.resolve()
        if is_within(args.cache_dir, repo):
            raise RefreshError("--cache-dir must be outside the target repository")
        args.cache_dir.mkdir(parents=True, exist_ok=True)

    temp_root = Path(
        tempfile.mkdtemp(
            prefix="stereomap-manual-refresh-",
            dir=str(staging_root) if staging_root else None,
        )
    ).resolve()
    staged_worktree = temp_root / "source"
    worktree_added = False
    primary_error = None
    cleanup_error = None

    try:
        run_git(repo, "worktree", "add", "--detach", staged_worktree, source_commit)
        worktree_added = True
        report = optimize_snapshot(repo, staged_worktree, args)
        staged_docs = staged_worktree / "docs"
        current, staged, added, removed, changed = compare_trees(
            target_docs, staged_docs
        )
        print_tree_diff(current, staged, added, removed, changed)

        if args.dry_run:
            print("[dry-run] validated staged output; target docs were not changed")
        elif not (added or removed or changed):
            print("[apply] optimized docs already match the selected main snapshot")
        else:
            replace_docs(repo, staged_docs)
            report.update(
                {"source_ref": args.source_ref, "source_commit": source_commit}
            )
            (repo / "_avif_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("[apply] replaced docs only after all conversion gates passed")
            print(run_git(repo, "status", "--short", "--", "docs"))
    except Exception as exc:
        primary_error = exc
    finally:
        if worktree_added:
            try:
                run_git(repo, "worktree", "remove", "--force", staged_worktree)
            except Exception as exc:
                cleanup_error = exc
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)

    if primary_error:
        if isinstance(primary_error, RefreshError):
            raise primary_error
        raise RefreshError(str(primary_error)) from primary_error
    if cleanup_error:
        raise RefreshError(f"temporary worktree cleanup failed: {cleanup_error}")


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source-ref", default="origin/main")
    parser.add_argument("--target-branch", default="4.5")
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--subsampling", default="4:4:4")
    parser.add_argument("--speed", type=int, default=6)
    parser.add_argument("--budget-mib", type=float, default=80.0)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="optional persistent content-addressed AVIF cache outside the repository",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build and validate a temporary optimized tree without replacing docs",
    )
    return parser.parse_args()


def main():
    try:
        refresh(parse_args())
    except RefreshError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
