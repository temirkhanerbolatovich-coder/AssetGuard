# Phase 0: наблюдение локального GLPI Agent inventory

- **Дата:** 2026-09-23
- **Agent:** GLPI Agent 1.19, upstream Windows x64
- **Режим:** локальный `glpi-inventory --json`, без server URL и без сетевой отправки
- **Raw artifact:** `C:\AssetGuardPhase0\raw\inventory-full-20260923.json` (вне репозитория и Git)
- **Размер:** 494 724 bytes
- **SHA-256:** `258845EC82B9E4FABD4D3EE5C1B16A407C263EB5586BF7A411439EAD22D11F8B`

## Наблюдаемый envelope

Верхний уровень JSON: `action`, `content`, `deviceid`, `itemtype`. Значение `itemtype` — Computer.

## Подтверждённые категории

| Категория | Наблюдение на тестовой машине | Поля, важные для MVP |
| --- | ---: | --- |
| `memories` | 2 observations | `capacity`, `numslots`, `serialnumber`, `speed`, `type`, `formfactor` |
| `storages` | 1 observation | `serial`, `model`, `disksize`, `interface`, `firmware`, `type` |
| `hardware` | 1 object | `uuid`, `chassis_type`, `memory` |
| `cpus` | 1 observation | категория присутствует |
| `monitors` | 1 observation | `manufacturer`, `serial`, `base64` |
| `controllers`, `drives` | 22 и 3 observations | категории присутствуют |

Это подтверждает, что normalizer MVP может начать с RAM и storage, используя наблюдаемые serial/slot/size поля, а identity endpoint — с hardware UUID. Значения полей намеренно не включены в документацию.

## Privacy finding

Полный default inventory также содержит `accesslog`, `envs`, `licenseinfos`, `local_groups`, `local_users`, `processes`, `softwares`, `users`. Они не нужны для AssetGuard MVP и не должны отправляться на будущий Gateway. До сетевого ingestion обязателен отдельный agent collection profile с allowlist hardware-категорий.

## Ограничения наблюдения

- Это один Windows endpoint и один полный scan, не доказательство поведения на всех моделях оборудования.
- Не проверены direct HTTP protocol, retry, authentication, partial inventory и hostname/reinstall behavior.
- Поля могут меняться с версией collector; версия и fixtures должны оставаться pinned.

## Последующий результат gateway foundation

После этого наблюдения реализован и проверен internal AssetGuard gateway на sanitized GLPI-shaped fixture: PostgreSQL сохраняет JSONB evidence с source/version/type/hash; повтор того же idempotency key не создаёт новую запись, а тот же ключ с иным payload возвращает conflict. Реальный default full scan пока не отправлялся в Gateway, потому что сначала должен быть применён privacy allowlist collector-а.
