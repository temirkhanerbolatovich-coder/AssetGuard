# GLPI Agent minimal profile — configuration spike

Дата проверки: 2026-09-23  
Версия агента: GLPI Agent 1.19 for Windows x64

## Проверенный запуск

`collect-minimal-inventory.ps1` запускает официальный `glpi-agent.bat` с:

- profile fragment `glpi-agent-minimal-profile.cfg`;
- отдельными writable `--vardir` и `--local` путями под `C:\AssetGuardPhase0`;
- `--json --force`;
- без `--server`, credentials, TLS overrides и listener.

`--vardir` существенен для user-mode laboratory run: стандартная папка установки в `Program Files` недоступна на запись без повышения прав. Скрипт не изменяет постоянную конфигурацию установленного агента.

## Результат

Локальный результат был создан вне Git в `C:\AssetGuardPhase0\minimal-profile-spike\raw`. Его SHA-256: `11513157AB1BF1B8F9BB1FF24113755945F036DD271578B5CE49E727697D31AB`.

Наблюдались только следующие поля `content`:

`bios`, `controllers`, `cpus`, `drives`, `hardware`, `memories`, `monitors`, `operatingsystem`, `storages`, `versionclient`, `videos`.

Не присутствовали `accesslog`, `envs`, `licenseinfos`, `local_groups`, `local_users`, `processes`, `softwares` и `users`. Скрипт проверяет эти запреты до успешного завершения.

## Ограничение

Это доказательство локального collection profile, а не доказательство сетевого протокола. Gateway пока не реализует нативный GLPI Agent HTTP endpoint: он принимает только внутренний authenticated JSON ingestion contract.
