"""
Kirov Dynamics — CI Heartbeat Triage
=====================================
Scans all repositories for the Raphasha27 account and reports:
  - Failing / errored workflow runs
  - Open Dependabot PRs
  - Security vulnerability alerts
  - Repos with no CI workflow configured

Usage (local):
    GITHUB_TOKEN=ghp_xxx python triage_heartbeat.py

Usage (GitHub Actions):
    The GITHUB_TOKEN secret is provided automatically.
"""

import os
import sys
import datetime
import requests

# ─────────────────────────── Config ───────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME      = "Raphasha27"
API           = "https://api.github.com"
HEADERS       = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
# Repos to skip (forks / archived / irrelevant)
SKIP_REPOS = {
    "mochi-motion",
    "Fire4s-End-End-AI-Solutions",
}

# ─────────────────────────── Helpers ──────────────────────────

def gh_get(path: str, params: dict = None) -> list | dict | None:
    """Paginated GET against the GitHub API. Returns full list for list endpoints."""
    url = f"{API}{path}"
    results = []
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 403:
            print(f"  ⛔ 403 Forbidden on {path} — check token scopes or billing.")
            return None
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
            # follow Link header for pagination
            link = resp.headers.get("Link", "")
            next_url = None
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
            url = next_url
            params = None  # params are already encoded in next_url
        else:
            return data
    return results


def get_repos() -> list[dict]:
    repos = gh_get(f"/users/{USERNAME}/repos", params={"type": "owner", "per_page": 100})
    if not repos:
        return []
    return [r for r in repos if not r.get("archived") and r["name"] not in SKIP_REPOS]


def get_latest_run(repo_name: str) -> dict | None:
    """Returns the latest workflow run for a repo (any workflow)."""
    data = gh_get(f"/repos/{USERNAME}/{repo_name}/actions/runs", params={"per_page": 1})
    if not data or not isinstance(data, dict):
        return None
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def get_open_dependabot_prs(repo_name: str) -> list[dict]:
    prs = gh_get(f"/repos/{USERNAME}/{repo_name}/pulls", params={"state": "open", "per_page": 100})
    if not prs:
        return []
    return [pr for pr in prs if pr.get("user", {}).get("login") == "dependabot[bot]"]


def get_security_alerts(repo_name: str) -> list[dict]:
    alerts = gh_get(f"/repos/{USERNAME}/{repo_name}/vulnerability-alerts")
    # This endpoint returns 204 (no body) if enabled+no alerts, 404 if disabled
    # gh_get returns None on 404
    if alerts is None:
        return []
    return alerts if isinstance(alerts, list) else []


def has_ci_workflow(repo_name: str) -> bool:
    workflows = gh_get(f"/repos/{USERNAME}/{repo_name}/actions/workflows")
    if not workflows or not isinstance(workflows, dict):
        return False
    return workflows.get("total_count", 0) > 0


def get_workflow_hardening(repo_name: str) -> dict:
    """Checks if workflows have workflow_dispatch and triggers on main."""
    workflows = gh_get(f"/repos/{USERNAME}/{repo_name}/actions/workflows")
    if not workflows or not isinstance(workflows, dict):
        return {"has_dispatch": False, "has_main": False}
    
    wf_list = workflows.get("workflows", [])
    has_dispatch = False
    has_main = False
    
    for wf in wf_list:
        path = wf.get("path")
        if not path: continue
        # Get workflow file content
        content_data = gh_get(f"/repos/{USERNAME}/{repo_name}/contents/{path}")
        if content_data and isinstance(content_data, dict):
            import base64
            content = base64.b64decode(content_data.get("content", "")).decode("utf-8", errors="ignore")
            if "workflow_dispatch:" in content:
                has_dispatch = True
            if "main" in content and "branches:" in content:
                has_main = True
                
    return {"has_dispatch": has_dispatch, "has_main": has_main}

# ─────────────────────────── Report ───────────────────────────

ICON = {
    "ok":      "✅",
    "fail":    "❌",
    "warn":    "⚠️ ",
    "skip":    "⏭️ ",
    "info":    "ℹ️ ",
    "pending": "🔄",
    "lock":    "🔐",
}

def status_icon(conclusion: str, status: str) -> str:
    if status in ("in_progress", "queued", "waiting"):
        return ICON["pending"]
    mapping = {
        "success":   ICON["ok"],
        "neutral":   ICON["ok"],
        "skipped":   ICON["skip"],
        "failure":   ICON["fail"],
        "timed_out": ICON["fail"],
        "cancelled": ICON["warn"],
        "action_required": ICON["warn"],
    }
    return mapping.get(conclusion or "", ICON["warn"])


def run_triage():
    now = datetime.datetime.now(datetime.timezone.utc)
    print()
    print("━" * 60)
    print(f"  🏛️  KIROV DYNAMICS — CI HEARTBEAT TRIAGE")
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("━" * 60)

    if not GITHUB_TOKEN:
        print("\n  ⛔  GITHUB_TOKEN is not set. Exiting.\n")
        sys.exit(1)

    repos = get_repos()
    if not repos:
        print("\n  ⛔  Could not fetch repositories. Check your token.\n")
        sys.exit(1)

    print(f"\n  📦  Scanning {len(repos)} repositories...\n")

    failing_ci   = []
    pending_ci   = []
    no_ci        = []
    open_dep_prs = []
    all_green    = []

    for repo in repos:
        name = repo["name"]
        sys.stdout.write(f"  ⏳ {name:<45}\r")
        sys.stdout.flush()

        run    = get_latest_run(name)
        dep_prs = get_open_dependabot_prs(name)
        hardened = get_workflow_hardening(name)

        if dep_prs:
            open_dep_prs.append((name, dep_prs))

        if run is None:
            status_str = f"{name}"
            if not has_ci_workflow(name):
                no_ci.append(status_str)
            else:
                no_ci.append(f"{status_str} (no runs)")
            continue

        conclusion = run.get("conclusion") or ""
        run_status = run.get("status") or ""
        icon       = status_icon(conclusion, run_status)
        run_url    = run.get("html_url", "")
        branch     = run.get("head_branch", "?")

        # Hardening info
        h_tag = ""
        if hardened["has_dispatch"]: h_tag += " ⚙️"
        if hardened["has_main"]: h_tag += " ⚠️(main)"

        if run_status in ("in_progress", "queued", "waiting"):
            pending_ci.append((name, icon, run_status, branch, run_url, h_tag))
        elif conclusion in ("failure", "timed_out", "action_required"):
            failing_ci.append((name, icon, conclusion, branch, run_url, h_tag))
        elif conclusion in ("success", "neutral", "skipped"):
            all_green.append((name, h_tag))
        else:
            failing_ci.append((name, icon, conclusion or run_status, branch, run_url, h_tag))

    # ── Print sections ──────────────────────────────────────────
    print(" " * 55)  # clear spinner line

    # GREEN
    print(f"\n  {ICON['ok']}  GREEN ({len(all_green)}):")
    if all_green:
        for name, h_tag in all_green:
            print(f"       • {name:<40} {h_tag}")
    else:
        print("       (none)")

    # PENDING
    if pending_ci:
        print(f"\n  {ICON['pending']}  IN PROGRESS ({len(pending_ci)}):")
        for name, icon, state, branch, url, h_tag in pending_ci:
            print(f"       {icon} {name:<40} [{branch}] {h_tag}")
            print(f"            {url}")

    # FAILING
    if failing_ci:
        print(f"\n  {ICON['fail']}  FAILING ({len(failing_ci)}):")
        for name, icon, conclusion, branch, url, h_tag in failing_ci:
            print(f"       {icon} {name:<40} [{branch}] → {conclusion} {h_tag}")
            print(f"            {url}")

    # NO CI
    if no_ci:
        print(f"\n  {ICON['info']}  NO CI CONFIGURED ({len(no_ci)}):")
        for name in no_ci:
            print(f"       • {name}")

    # DEPENDABOT
    if open_dep_prs:
        total_prs = sum(len(prs) for _, prs in open_dep_prs)
        print(f"\n  {ICON['lock']}  OPEN DEPENDABOT PRs ({total_prs}):")
        for name, prs in open_dep_prs:
            for pr in prs:
                print(f"       • [{name}] PR #{pr['number']} — {pr['title'][:60]}")
                print(f"            {pr['html_url']}")

    # ── Summary ─────────────────────────────────────────────────
    total        = len(repos)
    pct_green    = round(len(all_green) / total * 100) if total else 0
    health_emoji = "🟢" if pct_green >= 90 else ("🟡" if pct_green >= 70 else "🔴")

    # Hardening stats
    count_dispatch = sum(1 for _, h in all_green if "⚙️" in h) + \
                     sum(1 for _, _, _, _, _, h in failing_ci if "⚙️" in h) + \
                     sum(1 for _, _, _, _, _, h in pending_ci if "⚙️" in h)
    count_main = sum(1 for _, h in all_green if "⚠️" in h) + \
                 sum(1 for _, _, _, _, _, h in failing_ci if "⚠️" in h) + \
                 sum(1 for _, _, _, _, _, h in pending_ci if "⚠️" in h)

    print()
    print("━" * 60)
    print(f"  {health_emoji}  HEALTH: {pct_green}% green  |  "
          f"{len(all_green)} ✅  {len(failing_ci)} ❌  {len(pending_ci)} 🔄  {len(no_ci)} ℹ️")
    print(f"  🛡️  HARDENING: {count_dispatch} ⚙️ (dispatch)  |  {count_main} ⚠️ (main triggers)")
    print(f"  📬  Dependabot PRs waiting: "
          f"{sum(len(p) for _, p in open_dep_prs)}")
    print("━" * 60)
    print()

    # Exit code — non-zero if any failures exist
    if failing_ci:
        sys.exit(1)


if __name__ == "__main__":
    run_triage()
