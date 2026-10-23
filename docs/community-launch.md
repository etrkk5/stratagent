# StratAgent 0.8.0 community launch

## Positioning

**Describe your project. Design its agent workspace. Approve what gets installed.**

StratAgent is a local, platform-agnostic agent workspace architect. An existing
coding host/model helps interpret a project, propose public research and compare
roles/resources. StratAgent binds that work to reviewed sources, an inspectable
blueprint and exact authorization before generating workspace files. Provenance,
drift checks and recoverable updates carry the review forward.

Lead with the project-to-workspace outcome. Source provenance supports that
outcome; it is not a claim of guaranteed safety. StratAgent does not build the
requested application, launch agents or activate MCP servers automatically.

## English announcement — publish after the release is visible

I'm releasing **StratAgent 0.8.0 — Developer Preview**: describe your project,
design its agent workspace, and review exactly what gets installed.

Start with your project's responsibilities, roles, dependencies and exclusions.
Use your existing coding host/model to research current skill and MCP candidates,
compare options and produce a reviewable workspace blueprint. StratAgent previews
the file changes, requires exact approval and records source commits and hashes.

The local CLI includes ownership-aware updates/removal, drift verification,
transaction recovery and offline health checks. It renders configurations for
Claude Code, Codex, Antigravity and a generic target; native host coverage varies
and the setup guide explains those limits. No separate LLM API key is needed for
the existing-host flow; your host's access and usage limits still apply.

The preview ships with reproducible-build evidence, checksums and Python-distribution
SBOMs. Its release workflow verifies signed GitHub provenance before publication.
It remains a developer preview, with no universal safety or host-certification claim.

Try the two-minute offline demo, then a disposable project. I'd like feedback on
role allocation, missing resources and setup friction.

Release: https://github.com/etrkk5/stratagent/releases/tag/v0.8.0

Demo/setup: https://github.com/etrkk5/stratagent#try-it-locally

## Türkçe duyuru — sürüm görünür olduktan sonra yayımla

**StratAgent 0.8.0 geliştirici önizlemesini paylaşıyorum.** Projeni tarif et,
ajan çalışma alanını tasarla, kurulacak değişiklikleri inceleyip onayla.

Başlangıç noktası projenin ihtiyacı: roller, sorumluluklar, bağımlılıklar ve kapsam
dışında kalacak işler. Mevcut kodlama ortamındaki modelle güncel skill ve MCP
adaylarını araştırıp seçenekleri karşılaştırabiliyorsun. StratAgent, ortaya çıkan
planın dosya değişikliklerini gösteriyor; açık onayından sonra uyguluyor ve kaynak
commit'lerini/dosya özetlerini kaydediyor.

Yerel CLI; kullanıcı dosyalarını koruyan güncelleme ve kaldırma, değişiklik kontrolü,
işlem kurtarma ve çevrimdışı sağlık kontrolü içeriyor. Claude Code, Codex,
Antigravity ve genel çıktı hedefleri var. Yerel host doğrulaması her ortam için
aynı düzeyde değil; rehberde sınırlar açık. Mevcut modelinle kullanımda ayrı bir
LLM API anahtarı gerekmiyor; host hesabının kullanım koşulları geçerli.

Bu bir geliştirici önizlemesi. Ajanları veya üçüncü taraf MCP sunucularını otomatik
başlatmıyor; bütün kaynakların güvenli olduğunu iddia etmiyor. Paketlerle birlikte
derleme kanıtı, bütünlük dosyaları ve Python dağıtım bağımlılık envanteri geliyor.

İlk deneme için iki dakikalık çevrimdışı örnek hazır. Rol dağılımının projene
uygunluğu, eksik kaynaklar ve kurulumdaki zor noktalar için geri bildirim arıyorum.

Sürüm: https://github.com/etrkk5/stratagent/releases/tag/v0.8.0

Demo/kurulum: https://github.com/etrkk5/stratagent#try-it-locally

## Demo and sharing sequence

1. Make the release visible and verify a downloaded asset's attestation.
2. Follow the [recorded offline walkthrough](demo-0.8.0.md): preview → explicit
   apply → 46-output verification → read-only health. Label it a synthetic offline
   fixture, not live research or a native host recording.
3. For a model/project video, follow [orchestration](orchestration.md) and
   [host setup](host-setup.md), recording an actual new session first. Historical
   [Codex evidence](pilot-validation.md) retains its original date/version.
4. Share these drafts on the maintainer's chosen channels. This document does not
   post or send anything. Route sensitive reports to [private reporting](../SECURITY.md).

Keep the developer-preview label. P5 field checks remain waived, not performed.
Do not claim certified Claude/Antigravity/VS Code runtime support, completed human
evaluation, adoption, benchmark superiority, autonomous execution or production-grade
security. `plan` is a disclosed rule-based fallback; existing-host orchestration
uses the user's model. A website, hosted service and PyPI publication are not
prerequisites for this GitHub preview.
