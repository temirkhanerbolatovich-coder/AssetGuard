# AssetGuard — финальная локальная UI-приёмка

Дата: 2026-10-06. Проверена совокупность этапов упрощения навигации, обзора,
реестра, инцидентов, кабинетов, администрирования, форм и состояний интерфейса.

## Результат

Из `backend` выполнен полный набор с включёнными browser E2E:

```powershell
$env:ASSETGUARD_RUN_BROWSER_E2E='1'
.\.venv\Scripts\python.exe -m pytest -q
# 145 passed in 121.94s
```

Отдельно перед полным прогоном прошли:

- 16/16 сценариев `test_dashboard.py` и `test_ui_acceptance.py`;
- 124 backend-теста при штатно отключённых 21 browser E2E;
- `node --check frontend/app.js`;
- `git diff --check` без ошибок, только предупреждения Git о будущей нормализации
  LF/CRLF в рабочей копии Windows.

## Проверенные сценарии

- вход, восстановление сессии, выход, ошибки и повтор загрузки;
- обзор, приоритетные задачи и завершённый onboarding;
- поиск, фильтры, страницы, пустая выдача и возврат в реестр;
- добавление и редактирование имущества, QR и связь с Agent;
- технические и физические инциденты, сравнение и решения;
- структура школы, карточка кабинета, обход и акт;
- импорт Excel/PDF, preview, ошибки строк и сохранение выбора;
- сотрудники, права, ключи Agent, восстановление и Telegram;
- роли ADMIN, VIEWER, LOCATION_MANAGER и INVENTORY_CLERK;
- tenant/location isolation, клавиатура, контраст, reduced motion и reflow.

## Снимки

- `asset-create-desktop.png`, `asset-create-mobile.png`
- `asset-detail-desktop.png`, `asset-detail-mobile.png`
- `incident-detail-desktop.png`, `incident-decision-mobile.png`

Дополнительные снимки overview, registry, data exchange, locations и rooms
созданы тем же синтетическим E2E-сценарием и сохранены в этой папке.

## Ограничения

- Application commit `f4f56e7` опубликован в GitHub и принят на действующем
  Oracle Cloud production 2026-10-06. Отдельного Render deployment у проекта
  нет; новый второй production-контур не создавался.
- Автоматическая проверка не заменяет NVDA/VoiceOver, Firefox/Safari, zoom 400%
  и модерируемый usability-тест с сотрудниками школы.
- Production Vision остаётся выключенным из-за ресурсов; его модель и pipeline
  в этом этапе не изменялись.
