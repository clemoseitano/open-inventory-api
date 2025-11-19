# Pull base image
FROM python:3.13-slim


# Install OS-level dependencies for libraries like python-magic and opencv-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*
# Set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ENV_PATH .docker.env

# Set work directory
WORKDIR /code

RUN pip install --upgrade pip

# Install dependencies
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000

# Copy entrypoint script and grant execution permissions
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a non-root user
RUN useradd --system --create-home --shell /usr/sbin/nologin app_user

# Make sure the static directory exists, then set ownership
RUN mkdir -p /code/discovery/static
RUN mkdir -p /code/media

RUN chown -R app_user:app_user /code/discovery/static
RUN chown -R app_user:app_user /code/media

# Switch to the non-root user
USER app_user

# Run application
CMD ./entrypoint.sh