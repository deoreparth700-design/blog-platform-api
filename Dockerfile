FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=5000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY frontend/ ./frontend/

EXPOSE 5000

CMD ["python", "-m", "src.server"]
