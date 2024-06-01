# Use an official NVIDIA runtime with CUDA and Miniconda as a parent image
FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Install Miniconda
RUN apt-get update && apt-get install -y wget
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
RUN bash ~/miniconda.sh -b -p $HOME/miniconda
ENV PATH="/root/miniconda/bin:${PATH}"
RUN conda init bash

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Create a conda environment with the necessary packages
RUN conda create -n pvtvzhen python=3.9

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "pvtvzhen", "/bin/bash", "-c"]

# Install dependencies
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y
RUN conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV FLASK_RUN_PORT 8080
ENV FLASK_APP app.py
ENV FLASK_DEBUG 1

# Run app.py when the container launches
CMD [ "/bin/bash", "-c", "source activate pvtvzhen && python3 -m flask run --host=0.0.0.0" ]
