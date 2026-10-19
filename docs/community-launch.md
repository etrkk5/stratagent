# StratAgent: community positioning

## Core positioning

**A reviewable supply chain for agent skills.**

StratAgent treats reusable agent instructions as software dependencies. It connects discovery, source inspection, explicit approval and portable workspace configuration through a verifiable record of what was installed.

The product's technical center is the approval boundary: source commits, file contents, destination paths and rendered outputs are bound into one deterministic installation plan. This is the main idea to lead with when introducing the project.

## Short repository description

CLI-first agent workspace assembly: discover GitHub skills and sub-agents, review provenance and policy findings, and generate approved Claude Code/Codex configurations with pinned commits, exact-hash approval and a lockfile.

## Project introduction

StratAgent is a CLI-first toolkit for assembling agent workspaces from GitHub skills and sub-agent definitions. It ranks candidates using transparent relevance, documentation, security and license signals, then turns approved resources into portable configurations for Claude Code, Codex and Agent Skills-compatible environments. Every skill installation is bound to an immutable source commit and an exact approval digest, with file hashes and provenance recorded in a lockfile. A read-only MCP server makes discovery and inspection available to coding agents while keeping installation authority in the local CLI. Version 0.2 adds local project evidence, specialist role planning and official MCP Registry metadata review with inert host proposals.

## Community launch post

**Agent dependencies deserve a lockfile.**

I'm building **StratAgent**, a CLI-first toolkit for assembling agent workspaces from reusable skills and sub-agent definitions.

The workflow starts with a project request and produces an inspectable task plan. StratAgent then discovers relevant definitions on GitHub, evaluates their documentation structure, security signals and licenses, and previews exactly what would be installed for Claude Code or Codex.

The part I care most about is making each installation reviewable:

- Immutable source commits and verified Git blobs.
- Repository allowlists plus approval of the exact installation plan.
- SHA-256 hashes for source files and generated outputs.
- A provenance lockfile and a command to detect content drift.
- A read-only MCP surface that preserves the CLI's installation boundary.

The working Python release has no third-party runtime dependencies, includes an offline demo and has an offline regression suite. See `docs/validation.md` for exact local results and the distinction between previous CI evidence and the current development branch.

Planning is currently deterministic, imports are restricted to documentation bundles, and coding-agent processes are not launched automatically. Those boundaries are explicit so the current behavior is easy to inspect.

I'd value feedback from skill authors and developers maintaining agent workflows, especially on provenance, license edge cases and portability between coding environments.

## Technical discussion angle

The interesting question is how to make reused agent instructions auditable throughout workspace assembly. StratAgent answers this with content-bound approvals, a conservative import policy, pure platform renderers and a shared service layer exposed through the CLI and read-only MCP. Future semantic planning and runtime delegation can be added behind these same approval boundaries.

## Editorial rules

Lead with the installation model and show a reproducible demo. State that quality/security scores are transparent heuristics. Use real validation results. Avoid claims of autonomous execution, production-grade security, guaranteed safety, semantic planning, market leadership or adoption until there is evidence for them. Use a repository link only after a public repository actually exists.
