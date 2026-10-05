# AssetGuard — полный редизайн Ledger, 2026-10-05

## Результат

Существующий продукт пересобран вокруг реестра и проверки расхождений.
Светлая композиция, синий акцент, Golos Text, спокойные поверхности, чёткое
название объекта и явное действие. Никаких демонстрационных данных в продукте.

Изменены все девять рабочих разделов: обзор, имущество, инциденты, кабинеты,
импорт/экспорт, сотрудники/доступ, подключение Agent, справка Agent и
проверка по фото. Пересобраны вход, карточки имущества/кабинета/инцидента,
добавлена карточка обнаруженного компьютера до связи. Формы и dialogs
используют общие стили, keyboard focus, состояние отправки и ошибки.

В реестре шесть столбцов, представления источников, поиск/фильтры, возврат с
сохранением контекста и ограниченная отрисовка 20 строк. Тип/количество группы
отделены от связи с компьютером. Аппаратные характеристики видны в карточке.
Onboarding после двух обязательных шагов скрыт; возвращается по кнопке.

Шрифты раньше были fallback без загруженного Inter. Сейчас реально
отрисовывается self-hosted Golos Text с кириллицей, реальные веса 400–700,
без synthetic bold, общий масштаб 32/22/18/15/14/13 px и tabular-nums.
Сравнение показывает поля «Было / Стало»; 0/нет сведений не трактуются как
физическое отсутствие. Переименование не называется доказанной заменой.

Движение: controls 150 ms, меню 200 ms, панели 260 ms; transform/opacity,
4–12 px, общий easing. Есть hover/pressed, открытие меню и drawer/dialog,
вкладки, раскрытия, skeleton и toast. Reduced motion отключает движение.

## Референсы и решения

[Linear](https://linear.app/docs/filters): компактные фильтры и ориентация.
[Vercel Geist](https://vercel.com/geist/typography): читаемая шкала текста.
[Superlist](https://www.superlist.com/): ясное главное действие и раскрытие деталей.
[Pentagram](https://www.pentagram.com/): композиция, ритм, выразительные названия.
[Stripe](https://stripe.com/): иерархия формы и результата действия.
[IBM Carbon](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines):
рабочая таблица, поиск и страницы. [Подробное исследование и адаптация](../../docs/features/ui-ledger-redesign.md).
Awwwards был недоступен при обращениях; награды не заявляются.

Одна гарнитура, self-hosted subsets 77 456 байт; native dialogs и существующий
vanilla JS/CSS. Новый UI route использует существующие защищённые API.
Новых зависимостей, миграций, изменения классификации или Agent/Telegram/Vision
нет. Роли и tenant/location boundaries сохранены.

## Проверка

Локальный полный набор: **122 backend + 21 browser E2E = 143**.
Полный набор прошёл за 111.81 s; `node --check`, `git diff --check` и `pip check` прошли. После правки текстов/QR выполнен дополнительный браузерный прогон: 21 passed за 67.83 s. Финальная версия `1f7ff56` прошла GitHub CI: [run 37276595514](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37276595514), test/dependency audit и Secret scan — success. Дополнительные проверки формы, границ навигации, нормализации названия RAM и обоих полей серийного номера прошли локально; реальная Vision-модель в этом push не запускалась.

Реальные сценарии в isolated PostgreSQL: поиск по имени/номеру, фильтры и
страницы, открытие/возврат, добавление, server error и повтор с сохранённым
вводом, защита повторного submit, редактирование, связь компьютера с записью,
прямые ссылки, технический/физический инцидент и разрешённое решение,
обход и PDF-акт, подробности кабинета, Excel/PDF import/export, четыре роли
и две организации. Проверены пустые/длинные/несвязанные данные, loading,
error/retry, keyboard, dialogs/focus restore, контраст, оба режима motion.

Ширины: 360, 390, 768, 1024, 1280, 1440, 1920 px; дополнительно старые проверки
320 px и коротких экранов. Настоящий Chromium zoom 200%: zoom 2,
innerWidth 720 при viewport 1440, DPR 2. Все страницы доступны без
горизонтальной прокрутки всей страницы. Границы переключения меню дополнительно проверяются на 1120, 1199 и 1200 px: меню доступно, header не занимает весь экран. Полная WCAG-сертификация не заявляется.

### Лабораторная производительность

| Записей | Cold / warm workspace | Строк DOM | CLS | Long tasks |
| --- | --- | --- | --- | --- |
| 1000 | 256 / 238 ms | 20 | 0.0000 | 0 |
| 216 | 256 / 128 ms | 20 | 0.0022 | 0 |

Chromium 153, localhost, viewport 1366×900, без throttling. LCP относится к
начальному документу входа, не к authenticated workspace. Это ограниченная
проверка отзывчивости реестра; production capacity и медленная сеть требуют
самостоятельных измерений. [Машинные результаты](performance/capacity-1000.json),
[контраст](contrast.json).

## Снимки

Все снимки содержат только disposable test data; личные данные production
не сохранялись. Оценены desktop/mobile композиции, перенос длинного имени,
порядок навигации, comparison и форма после ошибки.

- [Реестр](screens/registry-desktop.png), [телефон](screens/devices-mobile.png).
- [Обзор](screens/overview-desktop.png), [вход](screens/login-desktop.png).
- [Имущество](screens/asset-desktop.png), [компьютер Agent](screens/computer-hardware-desktop.png).
- [Инцидент](screens/incident-detail-desktop.png), [решение на телефоне](screens/incident-decision-mobile.png).
- [Добавление](screens/create-desktop.png), [ошибка](screens/create-error-desktop.png), [zoom 200%](screens/create-zoom-200.png).
- [Связывание](screens/link-desktop.png), [кабинет](screens/room-desktop.png).
- [Импорт/экспорт](screens/data-exchange-desktop.png), [Agent](screens/agent-credentials-desktop.png), [доступ](screens/location-access-desktop.png).

## Production: финальная выкладка 2026-10-05, 07:22 UTC

Публичный [AssetGuard](https://assetguard-temirkhan.duckdns.org/#devices)
развёрнут из application commit **1f7ff561a0d675a004d53af6c700d621cf281106**.
Image **sha256:3845a31ad23301ea307d796d8930f357d0f56ab87848e3da534121e51e49f3a9**.
Первичная сборка 12443e4 использует штатный Dockerfile без Vision; финальный
слой на ранее проверенном образе 84c3b34 копирует backend/frontend из 1f7ff56. Runtime backend, зависимости,
инфраструктура и scripts между ними не менялись; тесты/оформление обновлены.
На финальном образе pip check прошёл. Database и Caddy containers не пересоздавались.
Сохранён предыдущий image для rollback; свежие encrypted R2 backup и isolated
restore завершились успешно до выкладки, 06:29 и 06:31 UTC соответственно.

- Public `/health`, `/health/ready` — 200. Index/JS/CSS побайтно совпали с
  committed Git blobs и файлам образа; Windows working-tree CRLF не считается
  production checksum. Три WOFF2 доступны и совпали с образом.
- Schema 0026, 63 защищённые admin operations; проверенные без входа маршруты
  вернули 401, авторизованное чтение — 200. Реальные room workspace и история
  доступны. Physical incidents на production отсутствуют; полный workflow
  проверен в isolated E2E, пустые production данные не подменялись.
- На финальной проверке 220 assets / 11 endpoints; при первой выкладке было
  216 assets. Приёмка не создавала и не редактировала записи; причина изменения
  количества отдельно не исследовалась. Agent 0.1.8 / GLPI 1.19 продолжает
  присылать обработанные данные, последний отчёт 07:16:51 UTC. На момент
  проверки 5 online / 6 stale, failed ingest 0. Native public PROLOG — 360 s.
- Telegram: 3 SENT, pending/retrying 0; прежний controlled test имеет одну
  попытку и тот же receipt. Новый тест не отправлялся. Monitor/notifications
  timers после выкладки снова active.
- Read-only браузерная приёмка прошла на публичном HTTPS: все девять рабочих
  разделов, реальные имущество/компьютер с пятью группами оборудования,
  карточка существующего технического инцидента с семью строками сравнения,
  возврат в нужную страницу реестра, контраст, keyboard focus, отмена dialog
  с возвратом фокуса, mobile/breakpoint reflow. **0 admin mutations**;
  фактически отрисован custom Golos Text, без synthetic weights.
- Проверены 13 viewport configurations, включая 1120/1199/1200 и короткие
  экраны. Cold workspace — один финальный sample 2424 ms, без throttling; сравнение
  производительности на медленной сети этим числом не подменяется.
  [Результат браузера без личных данных](production-browser.json).

Снимки внешних референсов остаются локальными исследовательскими файлами;
в frontend и Git включены только собственные UI-снимки и исследование со ссылками.

## Оставшиеся ограничения

- NVDA, Safari/Firefox, browser zoom 400%, usability с сотрудниками и
  репрезентативная медленная сеть не проверены.
- У ручной позиции list API не содержит времени последнего обхода: указано
  «По обходу»; журнал находится в кабинете.
- Списки ещё загружаются целиком; серверная пагинация и межсессионные
  сохранённые представления требуют отдельного server/product изменения.
- Производственный Vision остаётся выключен, как до редизайна. Модель не менялась.
- Fleet/signing/публикация нового Agent остаются отдельной задачей.

[Дизайн-система](../../docs/product/ui-design-system.md),
[функция](../../docs/features/ui-ledger-redesign.md),
[методика приёмки](../../docs/testing/ui-acceptance.md).
