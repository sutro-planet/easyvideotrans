# Use an official Anaconda runtime as a parent image
FROM continuumio/miniconda3

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Create a conda environment with the necessary packages
RUN conda create -n pvtvzhen python=3.8

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "pvtvzhen", "/bin/bash", "-c"]

# Install Flask
RUN pip install -r requirement.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "app.py"]

