# service1/Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Install Docker Compose
RUN apt-get update && \
    apt-get install -y curl && \
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
COPY . /app


# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8199 available to the world outside this container
EXPOSE 8199

# Define environment variable to avoid bytecode (.pyc) files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Run app.py when the container launches
CMD ["python", "service1.py"]
