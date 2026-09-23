# Windows operations

Upstream GLPI Agent устанавливается отдельно: AssetGuard не модифицирует и не форкает collector. Скрипты каталога покрывают локальную demo-эксплуатацию:

- `new-local-env.ps1` — создаёт локальные secrets;
- `start-demo.ps1` — поднимает PostgreSQL, миграции и API;
- `collect-minimal-inventory.ps1` — собирает privacy-limited JSON;
- `send-minimal-inventory.ps1` — отправляет его в authenticated gateway;
- `install-background-demo.ps1` / `uninstall-background-demo.ps1` — управляют demo Scheduled Tasks;
- `backup-database.ps1` / `restore-database.ps1` — создают и восстанавливают SQL backup.

Скрипты не отключают TLS, не записывают secrets в исходники и не меняют baseline автоматически.

Для локального Vision demo Python environment должен быть установлен с extras `backend[dev,vision]`. Модель загружается при первом scan; demo-изображения находятся в `demo/vision/`.
