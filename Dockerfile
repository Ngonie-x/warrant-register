FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# (Optional but common) minimal OS deps; psycopg2-binary usually works without these,
# but this helps if you later switch to psycopg2 (non-binary) or add build deps.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

# IMPORTANT: change "config.wsgi" to your actual Django project package if different
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
