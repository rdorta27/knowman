FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY schema ./schema
COPY corpus ./corpus
COPY eval ./eval
COPY prompts ./prompts
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 knowman && chown -R knowman:knowman /app
USER knowman

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["uvicorn", "knowman.api:app", "--host", "0.0.0.0", "--port", "8000"]
