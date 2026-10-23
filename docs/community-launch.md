# StratAgent 0.9.0 community launch

## Positioning

**Give your coding agent a workspace built for your project.**

Use your current coding agent and model. Start by inspecting what the project
already has, keep a sufficient setup, and propose only justified additions with
reasons, alternatives and exact file changes. Provenance, drift checks and
recoverable updates carry that review forward. This is a developer preview;
packaging and tests do not establish adoption or task-quality superiority.

## English announcement — publish after public-asset verification

I'm releasing **StratAgent 0.9.0 — Developer Preview**.

Describe your project to your existing coding agent. StratAgent helps inspect the
agent environment already in the repository, explain what is needed and review
exact changes before installing anything. If the current setup is sufficient,
you can keep it with no search and no new environment files.

The new agent-first flow carries commands and session details for you. It supports
project-local skill integration, grounded needs/coverage assessments and gap-guided
research, building on ownership-aware updates, drift checks and recovery. No
additional LLM API key is needed; your coding host supplies the model.

There are documented output adapters for Claude Code, Codex, Antigravity and a
generic target. Actual host coverage varies. This preview does not automatically
launch agents or activate MCP servers, and does not claim certified host behavior
or measured task-quality gains.

Try it in a disposable project. Feedback on unnecessary recommendations, unclear
choices and setup friction will guide the next changes.

Release: https://github.com/etrkk5/stratagent/releases/tag/v0.9.0

Start: https://github.com/etrkk5/stratagent/blob/v0.9.0/docs/quickstart.md

## Türkçe duyuru — herkese açık paket doğrulamasından sonra yayımla

**StratAgent 0.9.0 geliştirici önizlemesini paylaşıyorum.**

Projeni mevcut kodlama ajanına tarif et. StratAgent, depodaki ajan ortamını
incelemeye, neyin gerekli olduğunu açıklamaya ve kurulacak dosya değişikliklerini
önceden değerlendirmeye yardımcı oluyor. Mevcut kurulum yeterliyse araştırma
yapmadan ve yeni ortam dosyası eklemeden koruyabiliyorsun.

Yeni akışta komutları ve oturum ayrıntılarını ajan taşıyor; sen ihtiyaçları,
gerekçeleri, alternatifleri ve değişiklikleri değerlendiriyorsun. Projeye özel
skill bağlantısı, mevcut ortam değerlendirmesi ve somut eksiklere yönelik araştırma;
sahiplik takibi, değişiklik kontrolü ve kurtarma akışıyla birlikte çalışıyor.
Ayrı bir LLM API anahtarı gerekmiyor; mevcut kodlama ortamındaki model kullanılıyor.

Claude Code, Codex, Antigravity ve genel çıktı hedefleri belgelenmiş durumda.
Gerçek host kapsamı değişiyor. Bu bir geliştirici önizlemesi; ajanları veya MCP
sunucularını otomatik başlatmıyor, her ortamda sertifikalı çalışma veya ölçülmüş
verim artışı iddia etmiyor.

İlk denemeyi geçici bir projede yapabilirsin. Gereksiz öneriler, anlaşılmayan
seçimler ve kurulumdaki pürüzler için geri bildirim arıyorum.

Sürüm: https://github.com/etrkk5/stratagent/releases/tag/v0.9.0

Başlangıç: https://github.com/etrkk5/stratagent/blob/v0.9.0/docs/quickstart.md

## Sharing sequence

1. Publish the preview and verify downloaded assets, provenance and installation.
2. Follow the [quickstart](quickstart.md) in a disposable project. A recorded
   natural-language demonstration must use an actual new host session; the
   automated no-addition fixture is synthetic and does not launch a model.
3. For a reproducible offline example, use the retained
   [0.8.0 walkthrough](demo-0.8.0.md). Label its date/version and synthetic scope.
4. Share these drafts on the maintainer's chosen channels only after explicit
   authorization. This document does not post or send anything. Use
   [private reporting](../SECURITY.md) for sensitive reports.

Keep the preview label. Waived field checks are not performed/passed. Do not claim
certified host/VS Code runtime support, completed human evaluation, adoption,
benchmark superiority or autonomous execution. PyPI remains a separate operation;
a website or hosted service is not required for this GitHub preview.
