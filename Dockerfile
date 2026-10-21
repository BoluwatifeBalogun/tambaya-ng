FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY start.sh /app/start.sh
# Strip Windows line endings in case the repo was checked out on Windows with autocrlf.
RUN sed -i 's/\r$//' /app/start.sh
EXPOSE 8000
CMD ["sh", "/app/start.sh"]
