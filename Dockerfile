# Use an official NVIDIA runtime with CUDA and Miniconda as a parent image
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

RUN apt-get update && apt-get install ffmpeg -y

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV FLASK_RUN_PORT 8080
ENV FLASK_APP app.py
ENV FLASK_DEBUG 0

ARG PYTVZHEN_STAGE=beta
ENV PYTVZHEN_STAGE=${PYTVZHEN_STAGE}

# Run app.py when the container launches
CMD [ "/bin/bash", "-c", "python -m flask run --host=0.0.0.0" ]
