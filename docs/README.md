# Документация AssetGuard

Дата сверки: **27 сентября 2026 года**. Каноническое описание строится от текущего кода, migrations, tests и deployment configuration. При противоречии приоритет имеют executable tests и документы из раздела «Актуальные».

## Начать отсюда

1. [Текущий статус и полный чек-лист](product/current-project-checklist.md)
2. [Обзор архитектуры](architecture/overview.md) и [потоки данных](architecture/data-flow.md)
3. [Реализованные возможности](features/README.md) и [API boundaries](api/README.md)
4. [Модель безопасности](security/security-model.md)
5. [Стратегия тестирования](testing/testing-strategy.md)
6. [Развёртывание](deployment/README.md) и [production recovery](operations/production-deployment.md)
7. [Production roadmap](product/production-readiness-roadmap.md) и [технический долг](technical-debt.md)
8. [Changelog](../CHANGELOG.md)

## Актуальные документы

| Раздел | Документ | Назначение |
| --- | --- | --- |
| Architecture | [overview](architecture/overview.md), [data flow](architecture/data-flow.md), [module boundaries](architecture/module-boundaries.md), [source layout](architecture/source-layout.md) | Компоненты, зависимости, данные и структура кода |
| API | [API README](api/README.md) | Реализованные HTTP boundaries и важные контракты |
| Domain | [glossary](domain/glossary.md), [inventory operating model](product/inventory-operating-model.md) | Термины и правила учёта |
| Features | [features](features/README.md) | Карта подтверждённых возможностей |
| Security | [security model](security/security-model.md), [route matrix](security/admin-route-access-matrix.md), [Agent profile](security/agent-collection-profile.md) | Authentication, authorization, данные Agent и известные риски |
| Testing | [testing strategy](testing/testing-strategy.md) | Локальные и CI-проверки |
| Deployment | [deployment](deployment/README.md), [local demo](operations/local-demo-guide.md), [free demo](operations/free-deployment.md), [production](operations/production-deployment.md) | Запуск и восстановление окружений |
| Operations | [observability](operations/observability.md), [fleet pilot](operations/agent-fleet-pilot.md), [PDF/OCR](operations/pdf-import-ocr.md), [Windows scripts](../scripts/windows/README.md) | Эксплуатационные runbook |
| Product | [current checklist](product/current-project-checklist.md), [roadmap](product/production-readiness-roadmap.md), [UX workflow](product/ux-workflow.md), [UI system](product/ui-design-system.md) | Текущее состояние и следующие этапы |
| Decisions | [ADR registry](decisions/README.md) | Принятые архитектурные и security-решения |

## Исторические и справочные материалы

Эти документы сохраняют контекст требований, исследований или уже завершённых этапов. Они не являются инструкцией по текущему production-развёртыванию:

- [`ASSETGUARD_MVP_v0.1_REQUIREMENTS.md`](../ASSETGUARD_MVP_v0.1_REQUIREMENTS.md) — исходные требования;
- [`ASSETGUARD_MVP_v0.1_ANALYSIS.md`](../ASSETGUARD_MVP_v0.1_ANALYSIS.md) — анализ до реализации;
- [`ASSETGUARD_TECHNICAL_RESEARCH.md`](../ASSETGUARD_TECHNICAL_RESEARCH.md) — исследование вариантов foundation;
- [MVP completion checklist](product/mvp-completion-checklist.md) — фиксация завершения demo MVP;
- [pilot release plan](product/pilot-release-plan.md) — план к Idea Battle;
- [dashboard data audit](product/dashboard-data-audit.md) и [frontend redesign audit](product/frontend-redesign-audit.md) — входные данные завершённого UX-этапа;
- [pitch guide](product/pitch-guide.md) и [demo scenario](product/demo-scenario.md) — демонстрационные материалы;
- [Vision requirements](product/assetguard-vision-requirements.md) и [первичный Vision analysis](architecture/assetguard-vision-integration-analysis.md) — исходный scope Vision;
- [integration spikes](integration/) — наблюдения и решения по GLPI Agent;
- [legacy quality note](quality/test-strategy.md) — ранняя стратегия, заменённая актуальной [testing strategy](testing/testing-strategy.md).

ADR не переписываются после принятия. Новое решение оформляется следующим ADR и при необходимости помечает старое как `Superseded`.

## Правила поддержки документации

- Обновляйте README, checklist, runbook и тестовые числа в одном коммите с изменением поведения.
- Не заменяйте проверенный факт планом и не называйте ручной сценарий автоматизированным.
- Для секретов указывайте только имя переменной или способ хранения, никогда значение.
- Сохраняйте даты ручных проверок: они являются свидетельством конкретного запуска, а не гарантией текущего состояния.
- Перед merge проверяйте относительные Markdown-ссылки и `git diff --check`.
