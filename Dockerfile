FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    curl \
    python3-dev \
    autoconf \
    g++ \
    libpq-dev \
    build-essential \
    automake \
    pkg-config \
    libtool \
    libffi-dev \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.5
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY . .

RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-root

EXPOSE 3338

CMD ["sh", "-c", "poetry run mint --host 0.0.0.0 --port ${PORT:-3338}"]
