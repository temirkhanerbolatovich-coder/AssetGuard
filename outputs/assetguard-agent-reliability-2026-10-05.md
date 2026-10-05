# Agent 0.1.8 — приёмка непрерывного сбора и offline очереди

Дата: 2026-10-05. Прежний production application `0f67995`, docs HEAD `99f41d3`, schema `0026_telegram_notifications`. Изменение не затрагивает Vision, схему БД или UI.

## Причина

Gateway возвращал штатному GLPI `PROLOG_FREQ=24` в часах. `delaytime=60` не задаёт постоянный минутный обмен. Кроме того, native server target сначала выполняет PROLOG: без доступного сервера независимое накопление hardware history не обеспечивается. Проверено по установленному GLPI 1.19 и официальному исходному коду 1.20; [ADR-008](../docs/decisions/ADR-008-agent-durable-delivery.md).

## Реализация

SYSTEM task при загрузке/каждую минуту, локальный неизменённый GLPI hardware collector, default 300 s + 0–60 s до следующего сбора плюс scheduler delay, bounded FIFO 256 MiB/10000 files, атомарные envelopes и recovery/lock. ACK обязателен для удаления, lost ACK повторяет исходные байты. Initial/tick/reconnect jitter, batch максимум 3 с паузами, randomized capped retry, Retry-After, сохранение данных при revoke/corruption/quota. Новый PROLOG default 360 s, configurable 60–86400 s. [Контракт и настройка](../docs/features/agent-continuous-inventory.md).

Installer обновляет существующее подключение без нового ключа; сохраняет очередь. Исправлена совместимость обновления с выпущенным 0.1.6, у которого нет installer tag, но есть managed registry ACL marker. Выбранный HTTPS endpoint передаётся update helper. Точный адрес этого PC: `https://assetguard-temirkhan.duckdns.org/glpi-agent`.

## Локальная проверка

- Полный pytest из `backend`: **138 passed in 87.22 s**, включая **122 backend + 16 browser E2E**.
- После исправления native `ACCOUNTINFO` повторный полный набор: **138 passed in 88.02 s**. [Финальный application CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37264577308) на `fa22015a9fe091e8b6a68063c8af700fae1580a5` прошёл: 122 backend, 16 E2E, Secret scan, dependency audit, Compose и script validation.
- Тот же поставляемый runtime под **Windows PowerShell 5.1: 8 passed in 6.13 s**. Исправлены совместимость встроенных module paths при запуске из PS7, integer Unix deadlines и получение native process ExitCode через заранее открытый Handle.
- Реальный установленный GLPI **1.19** собрал XML без сетевого server target: **12190 bytes**, QUERY INVENTORY, нормализованный VERSIONCLIENT 1.19, запрещённых разделов **0**, capture timestamp присутствует. XML/идентификаторы сохранены только в закрытом локальном lab, не входят в Git/EXE/протокол.
- Проверены offline captures/FIFO, последующие циклы, batch limit, lost ACK/identical bytes, jitter/backoff/Retry-After, recover complete temp/state, lock, quota/corruption, auth rejection. Контролируемый HTTP server: HTML 200, redirect, 401, 429 и ответ >64 KiB не считаются ACK; только валидный XML удаляет отчёт. Redirect не выполняется.
- `node --check frontend/app.js`, PowerShell parser и итоговый `git diff --check` прошли. Inno Setup **6.7.3** собрал EXE 0.1.8; **NotSigned**, 2114556 bytes. Финальный SHA-256: `BCD24D903FDB7C03EACB51E38F3BE653938DD905B0683F360A0BC8B412D3F50F`.

## Реальная установка и production

Application source **`1e8725a173cb9c663d290f97e4f9b46f1eabfb15`**, [GitHub CI success](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37262701644): 122 backend + 16 E2E, pip check, dependency audit и Secret scan. Диагностическое исправление **`8407c3f1ccd6ec583ebc17315a6baef26a4e4671`**, [CI success](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37263411368), проверяет SYSTEM по SID и корректно работает с локализованным именем.

На этом Windows PC реально установлен **0.1.8 с GLPI 1.19**, сохранились прежние отдельные credentials и endpoint. SYSTEM task работает, native daemon **Stopped/Disabled**, runtime owner и DACL проверены: только SYSTEM/Administrators. Первый отчёт доставлен; к 04:19 UTC задание само выполнило **два сбора и две доставки**, LastTaskResult **0**. Первоначальный EXE не прошёл gateway в silent upgrade: старый 0.1.6 не имел tag, поэтому URL не подставлялся. Исправление managed legacy marker проверено повторной реальной установкой.

Контролируемый lab использовал **настоящий GLPI collector и настоящую HTTPS delivery на production**: три offline captures в закрытой отдельной очереди, затем первая подтверждённая сервером попытка намеренно возвращена worker как lost ACK. Следующий цикл повторил те же байты и отправил оставшиеся отчёты. **4 HTTP attempts → 3 raw inventories + 3 snapshots, один прежний endpoint, все PROCESSED**; подтверждено read-only SQL по трём различным SHA-256. Очередь опустела. Сетевое отсутствие и сроки моделировались в lab; физический адаптер ПК не отключался. Это не заменяет reboot/physical network fleet test.

Дополнительный read-only SQL 04:46 UTC подтвердил **шесть автоматических отчётов**, отдельно от трёх lab captures. Receipt times UTC: `04:14:46`, `04:19:51`, `04:25:49`, `04:30:54`, `04:37:00`, `04:42:35`. Интервалы **305.56, 358.00, 304.33, 366.09, 335.78 секунд** подтверждают постоянный обмен с jitter и задержкой scheduler, а не только первоначальный запуск.

Первый readiness report дал **13/14**: только проверка имени SYSTEM ошиблась на русской Windows (`СИСТЕМА`). Исправлен resolver постоянного SID `S-1-5-18`; перевод локализованной учётной записи и отличие текущего non-SYSTEM пользователя проверены на этом PC. Финальный EXE содержит исправление. **Повторная установка этого диагностического патча отменена Windows на UAC**; он пока не применён к установленной копии readiness helper. Ошибка проверки не означает остановку рабочего task. Полная readiness приёмка финального EXE не заявляется.

Перед серверной выкладкой encrypted R2 backup `assetguard-production-20261005-042627.sql.agbackup` и isolated restore завершились success: schema 0026, assets 216, endpoints 11. Результат server rollout записывается ниже.

Первый server rollout на `1e8725a` подтвердил health/ready, публичные frontend hashes, 63 admin operations/auth boundaries, schema 0026 и **реальный HTTPS PROLOG 360 s**. Приёмка остановилась на installer metadata: нативный local XML передаёт `CONTENT/ACCOUNTINFO {KEYNAME: TAG, KEYVALUE: ...}`, а прежняя UI projection читала только `CONTENT/TAG`. Read-only диагностика подтвердила linked asset, PROCESSED inventory и наличие ACCOUNTINFO. Исправление добавляет чтение этого штатного формата без изменения immutable payload; native integration tests 1.19/1.20 проверяют версию 0.1.8. Итог повторной выкладки приведён ниже.

**Финальная server acceptance прошла 04:57:22 UTC / 09:57:22 Asia/Qyzylorda.** Application `fa22015a9fe091e8b6a68063c8af700fae1580a5`, image `sha256:f53b7cc604ee757aae2e051c644519fca4f82f64417db675d08fea2a8a0ab297`; предыдущий runtime сохранён как `assetguard-api:rollback-prefa22015-20261005`. PostgreSQL и Caddy containers не пересоздавались. Health/ready, публичные frontend hashes, 63 операции, закрытая авторизация и существующий room workspace проверены. Реальный authenticated HTTPS PROLOG возвращает **360 s**. UI/API projection видит **installer 0.1.8 / upstream 1.19**, последний принятый автоматический inventory `04:55:02 UTC`, статус PROCESSED.

Снимок данных при приёмке: **216 assets, 11 endpoints, 65 raw inventories / 65 snapshots**, 17 credentials, schema 0026; **5 online / 6 stale**, identity conflicts **0**, failed ingest **0**. Telegram **3 SENT / pending 0 / retrying 0**; прежнее разрешённое test event остаётся SENT с одной попыткой и тем же message id. Новых тестовых Telegram-сообщений этот этап не создавал. Installed monitor соответствует source byte-for-byte. Pre-final R2 backup `assetguard-production-20261005-045342.sql.agbackup` и restore прошли; post-final backup/restore проверяется отдельно.

**Post-final R2 backup/restore PASS:** объект `assetguard-production-20261005-045806.sql.agbackup`, backup и restore `Result=success / ExecMainStatus=0`; изолированное восстановление завершено **04:59:06 UTC**, schema 0026, 216 assets / 11 endpoints. Running image совпал с принятой candidate. Все четыре timers — monitor, notifications, backup, restore rehearsal — **active**. Source docs обновлены отдельно от application image; массовая публикация installer не выполнялась.

## Оставшиеся границы

Полная fleet-приёмка нового 0.1.8 на 3–5 реальных PC, reboot/физическое отключение сети, signing, публикация стабильного installer и автоматический update/rollback пока не закрыты. Неотправленные отчёты ограничены quota, при заполнении новые сборы приостанавливаются. Server snapshot timestamp пока равен receipt time: capture time сохраняется в XML, но не является временем offline UI timeline. Частые captures требуют измерения хранения/retention и лимита общего NAT перед массовым rollout. Другие PC автоматически не обновлены; старый сохранённый deadline изменится только при следующем успешном контакте.
