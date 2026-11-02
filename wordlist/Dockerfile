# syntax=docker/dockerfile:1
# Build from the repo root:  docker build -f wordlist/Dockerfile -t wordlist .
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.2 /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY wordlist/ ./wordlist/
WORKDIR /app/wordlist

ENV FLASK_APP=wordApp.py
EXPOSE 5000

CMD [ "uv", "run", "--no-sync", "flask", "run", "--host", "0.0.0.0" ]
