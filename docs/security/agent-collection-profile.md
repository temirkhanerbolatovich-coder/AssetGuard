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

## Правило до production

Нельзя запускать агент с full default payload против Gateway. Native `/glpi-agent` проверен только вместе с этим минимальным profile, `no-compression = 1`, HTTP Basic credentials и GLPI Agent 1.19. Перед production-отправкой нужны утверждение policy владельцем проекта, HTTPS trust и защищённое хранение agent credentials.

## Windows service deployment

`scripts/windows/install-assetguard-agent-service.ps1` ставит именно upstream GLPI Agent как автоматическую Windows-службу. На Windows служба читает настройки из защищённого раздела реестра `HKLM\SOFTWARE\GLPI-Agent`; установщик сохраняет endpoint и inventory secret там и оставляет доступ только `SYSTEM` и локальным Administrators. При удалении конфигурации исходный ACL реестра восстанавливается. Profile также отключает встроенный локальный HTTP server (`no-httpd = 1`), чтобы агент не открывал порт управления на компьютере.

Это не anti-tamper software: пользователь без administrator rights не может управлять службой, а Administrator сохраняет возможность остановить, удалить и аудировать её. Скрывать процесс или обходить права администратора не является целью AssetGuard.
