# Technical spike: GLPI Agent

## Цель

Проверить жизнеспособность прямого приёма inventory без модификации GLPI Agent и зафиксировать наблюдаемый контракт. Это не разработка production-интеграции.

## Вопросы, на которые обязан ответить spike

1. Как агент выполняет HTTP(S) submission и какие обязательные endpoint/headers/ответы требуются?
2. Как выглядят полный и частичный inventory payload, какие версии участвуют?
3. Как устроены authentication, сертификаты, retry и idempotency?
4. Какие идентификаторы endpoint доступны: SMBIOS UUID, BIOS/chassis/motherboard serial, agent ID, Machine GUID, MAC?
5. Доступны ли RAM module serial/slot/capacity, storage serial/WWN, monitor EDID?
6. Как агент выражает missing category, empty field, collector error и hostname change?
7. Каковы payload limits и ресурсные параметры?

## Артефакты spike

- sanitized full payload;
- sanitized partial payload;
- таблица полей и semantic mapping;
- transcript request/response без secrets;
- наблюдения retry/error behavior;
- решение `direct viable` или `use GLPI API sidecar` с обоснованием.

## Критерий выбора

Прямой путь принимается, только если его можно поддерживать без имитации недокументированного поведения GLPI Server. Иначе выбирается sidecar с GLPI 11 API.

## Результат 2026-09-23

Решение: **direct viable для version-locked GLPI Agent 1.19 inventory task**.

- неизменённый upstream agent отправил `application/xml` POST `PROLOG` на точный configured URL;
- HTTP Basic challenge с realm и credentials `assetguard`/inventory secret поддержан агентом;
- XML reply `<RESPONSE>SEND</RESPONSE>` инициировал второй POST `INVENTORY`;
- в uncompressed privacy-limited прогоне размеры составили 169 bytes для PROLOG и 14,339 bytes для INVENTORY;
- payload содержит `REQUEST/DEVICEID`, `QUERY`, `CONTENT` и повторяемые hardware sections;
- реальный end-to-end против `/glpi-agent` создал один immutable `PROCESSED` RawInventory и один `ONLINE` endpoint в disposable PostgreSQL database;
- исходный XML и SHA-256 сохраняются в evidence, а отсутствие RAM/storage sections безопасно классифицируется как `PARTIAL`.

Не заявляется универсальная совместимость: compression, CONTACT/native JSON planning, retry timing, non-inventory tasks и будущие версии агента требуют отдельных contract tests. Production acceptance дополнительно проверяет HTTPS trust, secret storage и повторную доставку после сетевого сбоя.
