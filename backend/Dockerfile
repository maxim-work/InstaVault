# Базовый образ
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Настраиваем Poetry (не создавать виртуальное окружение)
RUN poetry config virtualenvs.create false

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock* /app/

# Устанавливаем зависимости проекта
RUN poetry install --no-interaction --no-ansi --no-root

# Копируем весь проект
COPY . /app/

# Указываем команду по умолчанию
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]