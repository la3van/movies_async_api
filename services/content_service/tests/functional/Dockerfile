ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .

RUN python -m pip install \
    --no-cache-dir \
    -r requirements.txt
