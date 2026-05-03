# Build context is the repo root (compose `context: ../..`) so we can
# pip-install the actual generator + detector packages and run their
# real logic from inside this container.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install --no-install-recommends -y build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY services/generator /tmp/generator
COPY services/detector  /tmp/detector
RUN pip install --no-cache-dir /tmp/generator /tmp/detector \
 && rm -rf /tmp/generator /tmp/detector

COPY services/demo-seed/seed.py /app/seed.py
COPY sigma /sigma

ENTRYPOINT ["python", "/app/seed.py"]
