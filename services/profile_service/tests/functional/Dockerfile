ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim
WORKDIR /app
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
COPY tests/functional/requirements.txt test-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r test-requirements.txt
COPY src src
COPY alembic alembic
COPY pytest.ini .
COPY tests tests
CMD ["pytest", "-q"]

