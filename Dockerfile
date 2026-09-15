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

# The corpus is bind-mounted from the host and the agent writes into it, so the
# container user must match the host owner; 1000 is only this machine's default.
ARG KNOWMAN_UID=1000
ARG KNOWMAN_GID=1000
RUN groupadd --gid "${KNOWMAN_GID}" knowman \
	&& useradd --create-home --uid "${KNOWMAN_UID}" --gid "${KNOWMAN_GID}" knowman \
	&& chown -R knowman:knowman /app
USER knowman

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["uvicorn", "knowman.api:app", "--host", "0.0.0.0", "--port", "8000"]
