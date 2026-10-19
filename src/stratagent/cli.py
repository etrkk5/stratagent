"""JSON-first command interface, suitable for shell scripts and review tools."""
import argparse
import json
import sys
import time

from . import __version__
from .common import StratagentError
from .demo import demo
from .hosts import DEFAULT_TARGETS, catalog
from .mcp import serve
from .planner import analyze
from .project import inspect_project
from .service import Stratagent
from .workspace import Workspace


def parser():
    root = argparse.ArgumentParser(prog="stratagent", description="StratAgent: a project-aware agent workspace architect. Discover, review and approve skills and MCP proposals.")
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--workspace", default=".", help="Existing project directory")
    root.add_argument("--log-json", action="store_true", help="Emit structured command events to stderr, without prompts, credentials or file contents")
    commands = root.add_subparsers(dest="command", required=True)
    for name, help_text in {
        "init": "Analyze a prompt and initialize a workspace (no external code)",
        "plan": "Analyze a prompt without writing files",
        "platforms": "List adapter capabilities and portable export support without reading a workspace",
        "decision-request": "Export grounded context and a provider-independent architectural decision schema",
        "blueprint": "Review or approve one plan for architecture, selected skills and inert MCP proposals",
        "discover": "Find pinned GitHub definitions and cache review evidence",
        "discover-mcp": "Search the official MCP Registry and cache metadata review (no execution)",
        "inspect-mcp": "Review MCP provenance, transport options and policy findings",
        "configure-mcp": "Preview or approve inert Claude/Codex/Antigravity MCP proposal files",
        "inspect": "Read candidate findings and optional untrusted file contents",
        "recommend": "Suggest eligible reviewed resources for each task; does not approve",
        "allow": "Explicitly allow one exact repository in this workspace",
        "install": "Preview an installation; --apply requires an exact approval digest",
        "configure": "Preview or apply generated task configurations",
        "verify": "Verify hashes of all locked outputs",
        "status": "Show workspace, candidates, policy and verification",
        "serve": "Run a read-only MCP server over stdio",
        "demo": "Create an offline demo with original synthetic examples",
    }.items():
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--workspace", default=argparse.SUPPRESS, help="Project directory (demo may create it)")
        sub.add_argument("--log-json", action="store_true", default=argparse.SUPPRESS, help="Emit structured events to stderr")
        if name in ("init", "plan"):
            sub.add_argument("prompt")
        if name == "init":
            sub.add_argument("--platforms", default=",".join(DEFAULT_TARGETS), help="Comma-separated adapter IDs; see stratagent platforms")
            sub.add_argument("--no-scan-project", action="store_true", help="Use only the prompt; skip bounded local manifest inspection")
        if name == "plan":
            sub.add_argument("--scan-project", action="store_true", help="Include bounded local manifest evidence from --workspace; writes nothing")
        if name == "discover-mcp":
            sub.add_argument("--query", help="Public server-name search; defaults to a detected project domain")
            sub.add_argument("--limit", type=int, default=6)
        if name in ("inspect-mcp", "configure-mcp"):
            sub.add_argument("candidate_id")
        if name == "configure-mcp":
            sub.add_argument("--option", type=int, default=0, help="Transport option index from inspect-mcp")
        if name == "blueprint":
            sub.add_argument("--decisions", help="Workspace-relative JSON proposal from your model or human review; no model API is called")
        if name == "discover":
            sub.add_argument("--repo", action="append", help="Exact owner/repo (repeatable); skips repository search")
            sub.add_argument("--limit", type=int, default=6)
        if name in ("inspect", "install"):
            sub.add_argument("candidate_id")
        if name in ("inspect", "inspect-mcp"):
            sub.add_argument("--content", action="store_true", help="Include all cached untrusted text for human review")
        if name == "allow":
            sub.add_argument("repo")
        if name in ("install", "configure", "configure-mcp", "blueprint"):
            mode = sub.add_mutually_exclusive_group()
            mode.add_argument("--dry-run", action="store_true", help="Default; write nothing")
            mode.add_argument("--apply", action="store_true", help="Write only after matching --approve")
            sub.add_argument("--approve", help="Full SHA-256 approval from the current dry-run")
            sub.add_argument("--content", action="store_true", help="Include exact generated file contents in the dry-run for review")
        if name == "demo":
            sub.add_argument("--apply", action="store_true", help="Activate only the bundled original demo and task configs")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    started = time.monotonic()

    def event(name, exit_code=None):
        if args.log_json:
            payload = {"schema_version": 1, "tool": "StratAgent", "event": name, "command": args.command,
                       "duration_ms": round((time.monotonic() - started) * 1000)}
            if exit_code is not None:
                payload["exit_code"] = exit_code
            print(json.dumps(payload, sort_keys=True), file=sys.stderr)

    event("command.started")
    try:
        if args.command == "platforms":
            result = catalog()
        elif args.command == "plan":
            result = analyze(args.prompt, inspect_project(Workspace(args.workspace)) if args.scan_project else None)
        elif args.command == "demo":
            result = demo(args.workspace, args.apply)
        elif args.command == "serve":
            serve(args.workspace)
            event("command.completed", 0)
            return 0
        else:
            forge = Stratagent(args.workspace)
            if args.command == "init":
                result = forge.init(args.prompt, args.platforms.split(","), not args.no_scan_project)
            elif args.command == "discover":
                result = forge.discover(args.repo, args.limit)
            elif args.command == "inspect":
                result = forge.inspect(args.candidate_id, args.content)[0]
            elif args.command == "discover-mcp":
                result = forge.discover_mcp(args.query, args.limit)
            elif args.command == "inspect-mcp":
                result = forge.inspect_mcp(args.candidate_id, args.content)[0]
            elif args.command == "allow":
                result = forge.allow(args.repo)
            elif args.command == "recommend":
                result = forge.recommend()
            elif args.command == "decision-request":
                result = forge.decision_request()
            elif args.command in ("install", "configure", "configure-mcp", "blueprint"):
                if args.approve and not args.apply:
                    raise StratagentError("--approve must be used with --apply; dry-run writes nothing.")
                if args.content and args.apply:
                    raise StratagentError("--content is for dry-run review; remove --apply to inspect generated files.")
                if args.command == "install":
                    result, files = forge.preview(args.candidate_id) if args.content else (forge.install(args.candidate_id, args.approve, args.apply), None)
                elif args.command == "configure-mcp":
                    result, files = forge.preview_mcp(args.candidate_id, args.option) if args.content else (forge.configure_mcp(args.candidate_id, args.option, args.approve, args.apply), None)
                elif args.command == "blueprint":
                    decisions = forge.ws.read(args.decisions) if args.decisions else None
                    result, files = forge.preview_blueprint(decisions) if args.content else (forge.blueprint(decisions, args.approve, args.apply), None)
                else:
                    result, files = forge.preview_config() if args.content else (forge.configure(args.approve, args.apply), None)
                if files is not None:
                    result["file_contents"] = {path: data.decode("utf-8") for path, data in sorted(files.items())}
            elif args.command == "verify":
                result = forge.verify()
            else:
                result = forge.status()
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        exit_code = 3 if args.command == "verify" and not result["ok"] else 0
        if args.command in ("discover", "discover-mcp") and not result["candidates"]:
            exit_code = 4
        event("command.completed", exit_code)
        return exit_code
    except StratagentError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        event("command.failed", 2)
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({"error": "Invalid or inaccessible local/API data. Check the workspace and input schema."}), file=sys.stderr)
        event("command.failed", 2)
        return 2
    except KeyboardInterrupt:
        event("command.interrupted", 130)
        return 130
