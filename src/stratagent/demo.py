"""Original, synthetic evidence for a reproducible network-free demo."""
import base64
from pathlib import Path

from .common import StratagentError, git_blob
from .service import Stratagent

MIT = '''MIT License

Copyright (c) 2026 Stratagent contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def sample_snapshot(kind="skill"):
    if kind == "skill":
        entry = "skills/python-review/SKILL.md"
        definition = "---\nname: python-review\ndescription: Review Python API testing and security boundaries.\nlicense: MIT\n---\n\nReview interfaces, invalid input handling, tests and data privacy.\nSee [review checklist](references/checklist.md).\n"
    else:
        entry = "agents/test-reviewer.md"
        definition = "---\nname: test-reviewer\ndescription: Review Python API testing and regression coverage.\ntools: Read, Grep, Glob\n---\n\nInspect the implementation and propose regression cases with evidence.\n"
    raw = {"LICENSE": MIT.encode(), entry: definition.encode()}
    if kind == "skill":
        raw["skills/python-review/references/checklist.md"] = b"# Review checklist\n\nCheck input validation, error handling and regression coverage.\n"
    return {"schema_version": 1, "repo": "stratagent-demo/original-examples", "commit": "d" * 40,
            "kind": kind, "entry": entry, "stars": 0, "origin": "demo-offline",
            "files": [{"path": p, "mode": "100644", "git_sha": git_blob(d), "data": base64.b64encode(d).decode()} for p, d in raw.items()]}


def demo(root, apply=False):
    path = Path(root)
    if path.is_symlink():
        raise StratagentError("Demo destination cannot be a symlink.")
    if not path.exists():
        path.mkdir(parents=True)
    forge = Stratagent(path)
    forge.init("Build a Python API agent for data analysis, testing and security review", ["claude", "codex", "generic"])
    candidates = [forge.import_snapshot(sample_snapshot(kind)) for kind in ("skill", "subagent")]
    previews = [forge.install(c["id"]) for c in candidates]
    config = forge.configure()
    results = []
    if apply:
        # Only original fixtures created above, explicitly requested with --apply.
        forge.allow("stratagent-demo/original-examples")
        results = [forge.install(c["id"], p["approval"], True) for c, p in zip(candidates, previews)]
        config = forge.configure()
        results.append(forge.configure(config["approval"], True))
    return {"demo": "offline-original-fixtures", "synthetic_commit": True,
            "workspace": str(forge.ws.root), "applied": apply,
            "candidates": candidates, "install_previews": previews, "configuration_preview": config,
            "results": results, "verification": forge.verify(),
            "note": "These are original demo files, not downloaded GitHub content. No agent or external code was executed."}
