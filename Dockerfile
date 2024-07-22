# Use an official NVIDIA runtime with CUDA and Miniconda as a parent image
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime AS base

# Disable interactive debian
ENV TZ=America/New_York \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install ffmpeg supervisor git -y

# Set the working directory in the container to /app
WORKDIR /app

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt


FROM base AS final

# Add the current directory contents into the container at /app
COPY . /app

# Copy the supervisord configuration file
COPY configs/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV FLASK_RUN_PORT 8080
ENV FLASK_APP app.py
ENV FLASK_DEBUG 0

ARG PYTVZHEN_STAGE=beta
ENV PYTVZHEN_STAGE=${PYTVZHEN_STAGE}

# Run supervisord to start both Flask and Celery
CMD ["/usr/bin/supervisord"]
