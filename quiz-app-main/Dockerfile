# ---------- Stage 1: base (dependencies) ----------
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: test (used by Jenkins "Test" stage) ----------
# The build fails here if any unit test fails.
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest -q

# ---------- Stage 3: production image ----------
FROM base AS production
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
COPY app.py ./
COPY data ./data
COPY templates ./templates
COPY static ./static
RUN useradd --create-home appuser
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
