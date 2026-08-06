# FastAPI HVAC receptionist backend — for Coolify (or any Docker host).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The app reads DEEPSEEK_API_KEY from the environment (set it in Coolify, NOT here).
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
