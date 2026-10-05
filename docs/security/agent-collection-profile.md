# GLPI Agent: privacy-профиль AssetGuard MVP

## Цель

До первой отправки inventory на AssetGuard Gateway collector должен передавать только технические категории, необходимые для контроля актива и hardware changes.

Configuration spike от 2026-09-23 подтверждён на установленном GLPI Agent 1.19: `glpi-agent --list-categories` выводит поддерживаемые имена категорий, а `--no-category=CATEGORY` отключает конкретную категорию. MVP использует явный denylist ниже; локальный запуск выполняется скриптом `scripts/windows/collect-minimal-inventory.ps1` и не имеет server target. Результат и ограничение spike зафиксированы в `docs/integration/glpi-agent-minimal-profile-spike.md`.

## Разрешённый минимум MVP

- hardware и BIOS/SMBIOS identity (`hardware`, `bios`);
- CPU (`cpu`);
- RAM (`memory`, в JSON GLPI Agent — `memories`);
- internal storage (`storage`, в JSON — `storages`), controllers и drives;
- GPU/video (`video`);
- network identity в минимально необходимом объёме (`network`);
- monitor identity/EDID при наличии (`monitor`);
- agent/version metadata.

## Запрещённые по умолчанию категории

- processes (`process`);
- users, local users, local groups, access log (`user`, `local_user`, `local_group`, `accesslog`);
- environment variables (`environment`);
- software, license information и product keys (`software`, `licenseinfo`);
- printers, USB/peripheral details (`printer`, `usb`, `input`, `sound`, `modem`, `port`);
- user files, browser history, arbitrary registry и любые custom collection sources.

## Правило для pilot и production

Нельзя запускать агент с full default payload против Gateway. Native `/glpi-agent` проверен только вместе с этим минимальным profile, `no-compression = 1`, HTTP Basic credentials и GLPI Agent 1.19/1.20. Для постоянной отправки обязательны утверждение policy владельцем проекта, HTTPS trust, отдельный credential устройства и его защищённое хранение. Legacy shared credential допускается только как временный migration fallback.

## Windows service deployment

Installer 0.1.8 использует неизменённый GLPI Agent как локальный collector; сетевую службу отключает после регистрации SYSTEM-задания `AssetGuard inventory delivery`. Локальный профиль без server target сохраняет аппаратный XML в защищённую очередь. Runtime scripts/data также защищены DACL и владельцем Administrators. [Контракт и ограничения](../features/agent-continuous-inventory.md). Uploader читает настройки из защищённого раздела реестра `HKLM\SOFTWARE\GLPI-Agent`; установщик сохраняет endpoint и inventory secret там и оставляет доступ только `SYSTEM` и локальным Administrators. При удалении конфигурации исходный ACL реестра восстанавливается. Profile также отключает встроенный локальный HTTP server (`no-httpd = 1`), чтобы агент не открывал порт управления на компьютере.

Это не anti-tamper software: пользователь без administrator rights не может управлять службой, а Administrator сохраняет возможность остановить, удалить и аудировать её. Скрывать процесс или обходить права администратора не является целью AssetGuard.
