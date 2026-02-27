# TODO: Finalize Dockerfile once backend is implemented
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Cloud Run expects port 8080
EXPOSE 8080

# TODO: Add health check and non-root user
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
