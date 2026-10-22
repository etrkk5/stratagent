"""Opt-in real-host evaluation, never an installer or automatic query approver."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import stratagent
from stratagent.common import StratagentError
from stratagent.orchestration import Orchestrator
from stratagent.service import Stratagent

CASES = {
    "en-retrieval": "Build a small Qdrant retrieval API with privacy. Use synthetic data in tests. No payments.",
    "tr-analytics": "DuckDB ile CSV veri kalitesi raporu üreten bir Python aracı geliştir. Testler çevrimdışı çalışmalı. Web arayüzü ve ödeme olmasın.",
    "en-browser": "Build Playwright browser regression checks for a web dashboard with accessibility and privacy checks. Do not add payment functionality.",
    "tr-events": "Rust ve NATS JetStream ile olay işleyen bir API geliştir. OpenTelemetry ile gözlemlenebilirlik ve hata testleri gerekli. Ödeme entegrasyonu olmasın.",
    "en-dashboard": "Build a SvelteKit dashboard and PostgreSQL API for staff with authentication and privacy. No payment integration.",
    "tr-questions": "Bir müşteri destek asistanı geliştirmek istiyorum; veri kaynağı ve dağıtım ortamı henüz kararlaştırılmadı.",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Disposable test directory; raw logs remain here, never publish them unchecked")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--phase", choices=["research", "compare", "refine", "clarify"], required=True)
    parser.add_argument("--codex", default=shutil.which("codex"), help="Explicit installed Codex CLI path; test adapter only, not a product dependency")
    parser.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()
    if not args.codex or not 10 <= args.timeout <= 180:
        raise StratagentError("An installed test host and timeout between 10 and 180 seconds are required.")
    root = Path(args.workspace).absolute()
    root.mkdir(parents=True, exist_ok=True)
    driver = Orchestrator(Stratagent(root))
    receipt = root / "host-evaluation-session.json"
    if receipt.exists():
        recorded = json.loads(receipt.read_text())
        if recorded["case"] != args.case:
            raise StratagentError("Test directory belongs to another original case; use a fresh directory.")
        session_id = recorded["session_id"]
    else:
        if args.phase not in ("research", "clarify"):
            raise StratagentError("Start a research/clarification phase first.")
        started = driver.start(CASES[args.case], ["generic"], model_turns=8, search_rounds=3, network_requests=240, seconds=3600)
        session_id = started["session"]["id"]
        receipt.write_text(json.dumps({"case": args.case, "session_id": session_id}))
    current = driver.request(session_id)
    expected = "research-needed" if args.phase in ("research", "clarify") else "comparison-needed"
    if current["session"]["state"] != expected:
        raise StratagentError(f"Test phase needs {expected}; no model call made.")
    actions = {"research": "research", "compare": "decide", "refine": "refine", "clarify": "clarify"}
    instruction = (
        "This is a real integration evaluation of StratAgent, not a coding task. "
        "Use only its two scoped MCP tools; no shell, files, web or other tools. "
        "Call stratagent_session_request, reason about the actual project and current evidence, "
        f"then submit one valid action={actions[args.phase]} response with the exact request_id. "
        "Respect exclusions and retain independent testing and security/privacy review. "
        "Never approve, search, install, activate or claim source safety. "
        "For research/refine choose at most two specific public GitHub query families and one public Registry query, "
        "with repository/definition/Registry-result budgets of two each; quote literal project evidence. "
        "Use project technology names, not a static favorite catalog. "
        "For compare, explain observed coverage, gaps and ineligible sources; bind useful eligible sources only when justified and cited. "
        "For refine, use the actual observed gaps to improve the queries; this is a test-directed refinement branch, not a benchmark of autonomous action selection. "
        "For clarify, ask 1–3 concrete missing project/resource questions and stop without proposing queries. "
        "Stop once the proposal is saved and summarize its state in one sentence."
    )
    command = [args.codex, "exec", "--ignore-user-config", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "--json", "-C", str(root),
               "-c", 'approval_policy="never"', "-c", "mcp_servers.stratagent.command=" + json.dumps(sys.executable),
               "-c", "mcp_servers.stratagent.args=" + json.dumps(["-m", "stratagent", "serve", "--workspace", str(root), "--orchestration", session_id]),
               "-c", "mcp_servers.stratagent.env.PYTHONPATH=" + json.dumps(str(Path(stratagent.__file__).resolve().parent.parent)),
               "-c", "mcp_servers.stratagent.required=true", instruction]
    logs = root / "host-evaluation-logs"
    logs.mkdir(exist_ok=True)
    prefix = f"{current['session']['revision']:03}-{args.phase}"
    started_at = time.monotonic()
    with (logs / (prefix + ".jsonl")).open("x") as output, (logs / (prefix + ".stderr")).open("x") as errors:
        process = subprocess.run(command, stdout=output, stderr=errors, timeout=args.timeout)
    calls = []
    for line in (logs / (prefix + ".jsonl")).read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "mcp_tool_call":
                if item.get("tool") not in ("stratagent_session_request", "stratagent_session_submit"):
                    raise StratagentError("Evaluation used an unexpected tool; do not count this as a scoped bridge pass.")
                calls.append(item["tool"])
            elif item.get("type") not in ("agent_message", "reasoning"):
                raise StratagentError("Evaluation used an unexpected host action; inspect local logs before claiming a pass.")
    if not {"stratagent_session_request", "stratagent_session_submit"} <= set(calls):
        raise StratagentError("Evaluation did not exercise both scoped session tools.")
    result = driver.status(session_id)
    summary = {"case": args.case, "phase": args.phase, "exit_code": process.returncode, "seconds": round(time.monotonic() - started_at, 1),
               "workspace": str(root), "session_id": session_id, "state": result["session"]["state"], "usage": result["session"]["usage"],
               "runs": result["session"]["runs"], "scoped_tool_calls": len(calls), "installed_outputs": len(driver.service.lock()["installations"])}
    print(json.dumps(summary, ensure_ascii=True))
    target = "review-required" if args.phase == "compare" else ("clarification-needed" if args.phase == "clarify" else "awaiting-search-approval")
    if process.returncode or result["session"]["state"] != target:
        raise StratagentError("Host evaluation did not reach its expected proposal checkpoint; inspect local logs, do not auto-retry or bypass validation.")


if __name__ == "__main__":
    try:
        main()
    except (StratagentError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error) if isinstance(error, StratagentError) else "Host evaluation failed or timed out; inspect local artifacts before retrying."}), file=sys.stderr)
        raise SystemExit(2)
