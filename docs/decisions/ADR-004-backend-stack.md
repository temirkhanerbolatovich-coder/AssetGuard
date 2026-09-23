# ADR-004: Python 3.12 + FastAPI + PostgreSQL для MVP backend

- **Статус:** принято для MVP
- **Дата:** 2026-09-23

## Контекст

ТЗ фиксирует modular monolith и PostgreSQL, но не язык/framework. На лабораторной машине доступны Python 3.12, Docker и Node; требуется маленький проверяемый HTTP ingress без микросервисной инфраструктуры.

## Решение

Backend — Python 3.12 + FastAPI. PostgreSQL запускается отдельным локальным контейнером; production DB не публикуется наружу. API, доменная логика и PostgreSQL infrastructure остаются модулями единого процесса.

## Последствия

- Быстрый строготипизированный HTTP boundary и автодокументация для admin API.
- Нативная совместимость с JSON payload workflow GLPI Agent.
- `RawInventory` будет проектироваться под PostgreSQL/JSONB, а не под SQLite fallback.
- Docker daemon должен быть запущен для локальной database integration-проверки.

