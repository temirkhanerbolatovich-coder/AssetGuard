# Agent 0.1.8 — приёмка непрерывного сбора и offline очереди

Дата: 2026-10-05. Прежний production application `0f67995`, docs HEAD `99f41d3`, schema `0026_telegram_notifications`. Изменение не затрагивает Vision, схему БД или UI.

## Причина

Gateway возвращал штатному GLPI `PROLOG_FREQ=24` в часах. `delaytime=60` не задаёт постоянный минутный обмен. Кроме того, native server target сначала выполняет PROLOG: без доступного сервера независимое накопление hardware history не обеспечивается. Проверено по установленному GLPI 1.19 и официальному исходному коду 1.20; [ADR-008](../docs/decisions/ADR-008-agent-durable-delivery.md).

## Реализация

SYSTEM task при загрузке/каждую минуту, локальный неизменённый GLPI hardware collector, default 300 s + 0–60 s до следующего сбора плюс scheduler delay, bounded FIFO 256 MiB/10000 files, атомарные envelopes и recovery/lock. ACK обязателен для удаления, lost ACK повторяет исходные байты. Initial/tick/reconnect jitter, batch максимум 3 с паузами, randomized capped retry, Retry-After, сохранение данных при revoke/corruption/quota. Новый PROLOG default 360 s, configurable 60–86400 s. [Контракт и настройка](../docs/features/agent-continuous-inventory.md).

Installer обновляет существующее подключение без нового ключа; сохраняет очередь. Исправлена совместимость обновления с выпущенным 0.1.6, у которого нет installer tag, но есть managed registry ACL marker. Выбранный HTTPS endpoint передаётся update helper. Точный адрес этого PC: `https://assetguard-temirkhan.duckdns.org/glpi-agent`.

## Локальная проверка

- Полный pytest из `backend`: **138 passed in 87.22 s**, включая **122 backend + 16 browser E2E**.
- Тот же поставляемый runtime под **Windows PowerShell 5.1: 8 passed in 6.13 s**. Исправлены совместимость встроенных module paths при запуске из PS7, integer Unix deadlines и получение native process ExitCode через заранее открытый Handle.
- Реальный установленный GLPI **1.19** собрал XML без сетевого server target: **12190 bytes**, QUERY INVENTORY, нормализованный VERSIONCLIENT 1.19, запрещённых разделов **0**, capture timestamp присутствует. XML/идентификаторы сохранены только в закрытом локальном lab, не входят в Git/EXE/протокол.
- Проверены offline captures/FIFO, последующие циклы, batch limit, lost ACK/identical bytes, jitter/backoff/Retry-After, recover complete temp/state, lock, quota/corruption, auth rejection. Контролируемый HTTP server: HTML 200, redirect, 401, 429 и ответ >64 KiB не считаются ACK; только валидный XML удаляет отчёт. Redirect не выполняется.
- `node --check frontend/app.js`, PowerShell parser и `git diff --check` прошли. Inno Setup **6.7.3** собрал EXE 0.1.8; **NotSigned**. Финальный SHA-256: `446C08011DC450856FA9C8117EFB45F713CC21C0FA970F13EC088B23792801E1`.

## Реальная установка и production

Состояние этой части будет дополнено результатами фактической установки/выкладки. Первоначальный EXE не прошёл проверку gateway в silent upgrade: старый 0.1.6 не имел tag, поэтому текущий URL не подставлялся. Ошибка исправлена по metadata установленного Agent; повторный installer зарегистрировал новый режим и отключил native daemon. Подтверждение первой доставки и ACL/readiness ещё проверяется. До server deployment публичный `/health/ready` возвращает ready, running image и Git HEAD совпадают с прежней принятой версией.

## Оставшиеся границы

Полная fleet-приёмка нового 0.1.8 на 3–5 реальных PC, reboot/физическое отключение сети, signing, публикация стабильного installer и автоматический update/rollback пока не закрыты. Неотправленные отчёты ограничены quota, при заполнении новые сборы приостанавливаются. Server snapshot timestamp пока равен receipt time: capture time сохраняется в XML, но не является временем offline UI timeline. Частые captures требуют измерения хранения/retention и лимита общего NAT перед массовым rollout. Другие PC автоматически не обновлены; старый сохранённый deadline изменится только при следующем успешном контакте.
