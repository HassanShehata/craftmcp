FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    build-essential \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy and install Python requirements first
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY app .

# Install uv directly and persist to PATH
RUN curl -Ls https://astral.sh/uv/install.sh | bash && \
    cp /root/.local/bin/uv /usr/local/bin/

# Confirm uv installed
RUN uv --version

# Expose FastAPI port
EXPOSE 8000

# Python output unbuffered
ENV PYTHONUNBUFFERED=1

# Run FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "critical"]
