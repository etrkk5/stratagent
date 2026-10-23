# Use StratAgent with your coding agent

This guide covers the **0.9.0 developer preview**. The older 0.8.0 preview
retains its original commands. PyPI publication is deferred. You can also install
a verified wheel from the [release installation guide](publishing.md#verify-and-install).

## Install once

Clone the repository and install into its local environment:

```sh
git clone --branch v0.9.0 --depth 1 https://github.com/etrkk5/stratagent.git
cd stratagent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
stratagent --version
```

The tag selects the 0.9.0 source containing the fit workflow. On Windows use
`python` and `.venv\Scripts\Activate.ps1`; see [OS support](os-portability.md).
Your coding agent needs access to this installed CLI/environment in the intended
project. No additional LLM API key is needed; the existing host supplies the model.

## Connect it to your project

Tell the agent:

> Connect StratAgent to this project for the coding host we are using. Review the
> first-party skill files and explain the exact changes before adding them.
> Preserve my current files and permissions.

The agent previews `connect`, reviews its contents and applies the exact authorized
connection. This adds local skill instructions; host settings/MCP activation are
separate. Existing differing files are preserved. A refresh/new conversation may
be needed for the host to discover the skill. [Connection details](agent-first-experience.md).

## Describe the work

For example:

> Use StratAgent to prepare this project's agent environment. Build a small Python
> API with tests. No payments. Inspect what is already here and explain whether
> we need any additions. Show the reasons and changes before applying anything.

Or in Turkish:

> StratAgent ile bu projenin ajan ortamını hazırla. Testleri olan küçük bir Python
> API geliştireceğiz; ödeme sistemi istemiyorum. Önce mevcut ortamı incele. Ek bir
> şey gerekip gerekmediğini, gerekçesini ve değişecek dosyaları göster.

The agent carries the commands, JSON, session IDs and review digests. You answer
material project questions and review meaningful choices:

- If the current setup is enough, review its reasons and alternatives and choose
  to keep it. No new environment files are installed.
- If a capability is missing, review the actual outbound public search terms.
  The agent researches the gap, explains resource choices and presents the exact
  file changes for approval before installation.
- If evidence is incomplete, files conflict or an earlier plan is stale, the
  agent explains what needs attention and preserves the existing work.

After setup review, application work continues only when your task authorizes
it. An accepted setup is not a claim that the application has been built/tested.
See [assessment and no-change behavior](workspace-fit.md) and
[existing-environment scope](existing-environment.md) for current limits.
