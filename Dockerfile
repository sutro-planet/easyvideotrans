# Use an official Python runtime as a parent image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Disable interactive debian
ENV TZ=America/New_York \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install ffmpeg supervisor git -y

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set the working directory in the container to /app
WORKDIR /app

# Copy pyproject.toml and uv.lock to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev && /app/.venv/bin/python --version

# Add the current directory contents into the container at /app
COPY . /app

# Copy the supervisord configuration file
COPY configs/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set environment variables to configure Celery
ENV CELERY_BROKER_DOMAIN localhost
ENV CELERY_BROKER_URL pyamqp://guest@localhost:5672//
ENV CELERY_RESULT_BACKEND file:///app/celery_results
ENV CELERY_WORKER_PREFETCH_MULTIPLIER 1
ENV CELERY_TASK_ACKS_LATE true

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV FLASK_RUN_PORT 8080
ENV FLASK_APP app.py
ENV FLASK_DEBUG 0

ARG PYTVZHEN_STAGE=beta
ENV PYTVZHEN_STAGE ${PYTVZHEN_STAGE}

# Run supervisord to start both Flask and Celery
# Note: supervisord.conf should use uv run commands for Python processes
CMD ["/usr/bin/supervisord"]
