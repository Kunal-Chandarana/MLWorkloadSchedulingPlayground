FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scheduler code
COPY scheduler.py .
COPY config.py .
COPY metrics.py .
COPY config.yaml .
COPY policies/ ./policies/

# Run scheduler
CMD ["python", "-u", "scheduler.py"]

