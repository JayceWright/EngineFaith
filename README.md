# Движок Веры (Engine of Faith)

Симулятор ИИ-агентов, которые общаются между собой для формирования культа.
<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/9d895081-bc4a-4ab1-b421-4b28608d6b11" />

## Стек технологий
- **Backend**: Python, FastAPI, Asyncio
- **База данных**: SQLite (через `aiosqlite`)
- **ИИ**: OpenAI Python client, настроенный на использование OpenRouter API (модель `openrouter/free`)

## Установка и запуск

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите сервер:
   ```bash
   uvicorn main:app --reload
   ```

## API Эндпоинты

- `GET /`: Приветственное сообщение.
- `GET /world`: Текущее состояние мира (список агентов и последние сообщения).
- `POST /agents`: Создание нового агента.
  - Тело запроса (JSON): `{"name": "Имя", "prompt": "Личность/инструкции", "faith_level": 0.5, "stress_level": 0.1}`

## Механика
Каждые 30 секунд запускается цикл мира, в котором случайный агент анализирует последние сообщения и генерирует свой ответ или действие.
