# Движок Веры (Engine of Faith)

Симулятор ИИ-агентов, которые общаются между собой для формирования культа.

## Стек технологий
- **Backend**: Python, FastAPI, Asyncio
- **База данных**: SQLite (через `aiosqlite`)
- **ИИ**: OpenAI Python client, настроенный на использование OpenRouter API (модель `openrouter/free`)

## Настройка API ключа
Для работы проекта необходимо установить переменную окружения `OPENROUTER_API_KEY`:
```bash
export OPENROUTER_API_KEY='ваш_ключ_здесь'
```
В коде ключ считывается в файле `main.py` (строка 21):
```python
api_key=os.environ.get("OPENROUTER_API_KEY", "dummy_key")
```

## Выбор модели
Выбор модели ИИ происходит в файле `main.py` в методе `think_and_speak` класса `CultAgent` (строка 53):
```python
response = await openai_client.chat.completions.create(
    model="openrouter/free", # Здесь можно изменить модель
    ...
)
```

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
