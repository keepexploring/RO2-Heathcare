FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["panel", "serve", "dashboard.py", "--address", "0.0.0.0", "--port", "5006", "--autoreload"]
