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

