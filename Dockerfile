FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn
RUN opentelemetry-bootstrap --action=install
WORKDIR /app
COPY ./ /app/
EXPOSE 8080
CMD ["opentelemetry-instrument", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]