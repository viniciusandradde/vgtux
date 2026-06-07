FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY portal.py .
COPY portal.html .
COPY icon-192.png icon-512.png ./
EXPOSE 8080
CMD ["uvicorn", "portal:app", "--host", "0.0.0.0", "--port", "8080"]
