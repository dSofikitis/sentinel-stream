FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install --no-install-recommends -y build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["sentinel-detector"]
