"""JSON-first command interface, suitable for shell scripts and review tools."""
import argparse
import json
import sys

from . import __version__
from .common import StratagentError
from .demo import demo
from .mcp import serve
from .planner import analyze
from .service import Stratagent


def parser():
    root = argparse.ArgumentParser(prog="stratagent", description="A reviewable supply chain for agent skills. Discover, inspect and approve portable workspaces.")
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--workspace", default=".", help="Existing project directory")
    commands = root.add_subparsers(dest="command", required=True)
    for name, help_text in {
        "init": "Analyze a prompt and initialize a workspace (no external code)",
        "plan": "Analyze a prompt without writing files",
        "discover": "Find pinned GitHub definitions and cache review evidence",
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
        if name in ("init", "plan"):
            sub.add_argument("prompt")
        if name == "init":
            sub.add_argument("--platforms", default="claude,codex", help="Comma-separated claude,codex,generic")
        if name == "discover":
            sub.add_argument("--repo", action="append", help="Exact owner/repo (repeatable); skips repository search")
            sub.add_argument("--limit", type=int, default=6)
        if name in ("inspect", "install"):
            sub.add_argument("candidate_id")
        if name == "inspect":
            sub.add_argument("--content", action="store_true", help="Include all cached untrusted text for human review")
        if name == "allow":
            sub.add_argument("repo")
        if name in ("install", "configure"):
            mode = sub.add_mutually_exclusive_group()
            mode.add_argument("--dry-run", action="store_true", help="Default; write nothing")
            mode.add_argument("--apply", action="store_true", help="Write only after matching --approve")
            sub.add_argument("--approve", help="Full SHA-256 approval from the current dry-run")
        if name == "demo":
            sub.add_argument("--apply", action="store_true", help="Activate only the bundled original demo and task configs")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            result = analyze(args.prompt)
        elif args.command == "demo":
            result = demo(args.workspace, args.apply)
        elif args.command == "serve":
            serve(args.workspace)
            return 0
        else:
            forge = Stratagent(args.workspace)
            if args.command == "init":
                result = forge.init(args.prompt, args.platforms.split(","))
            elif args.command == "discover":
                result = forge.discover(args.repo, args.limit)
            elif args.command == "inspect":
                result = forge.inspect(args.candidate_id, args.content)[0]
            elif args.command == "allow":
                result = forge.allow(args.repo)
            elif args.command == "recommend":
                result = forge.recommend()
            elif args.command in ("install", "configure"):
                if args.approve and not args.apply:
                    raise StratagentError("--approve must be used with --apply; dry-run writes nothing.")
                result = forge.install(args.candidate_id, args.approve, args.apply) if args.command == "install" else forge.configure(args.approve, args.apply)
            elif args.command == "verify":
                result = forge.verify()
            else:
                result = forge.status()
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        if args.command == "verify" and not result["ok"]:
            return 3
        if args.command == "discover" and not result["candidates"]:
            return 4
        return 0
    except StratagentError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({"error": "Invalid or inaccessible local/API data. Check the workspace and input schema."}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
