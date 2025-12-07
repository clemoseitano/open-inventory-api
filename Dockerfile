# Pull base image
FROM python:3.13-slim

# Install OS-level dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
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

# Expose port
EXPOSE 8000

# Copy entrypoint and make executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create a non-root user
RUN useradd --system --create-home --shell /usr/sbin/nologin app_user

RUN mkdir -p /code/staticfiles

RUN mkdir -p /code/media

# Create a directory for PaddleOCR models to ensure the user can write to it
# Paddle defaults to ~/.paddleocr, so we create it in the user's home
RUN mkdir -p /home/app_user/.paddleocr
RUN mkdir -p /home/app_user/.paddlex

# Set ownership. 
# We give app_user ownership of staticfiles, media, and the home directory
RUN chown -R app_user:app_user /code/staticfiles
RUN chown -R app_user:app_user /code/media
RUN chown -R app_user:app_user /home/app_user

# Switch to the non-root user
USER app_user

# Run application
CMD ./entrypoint.sh