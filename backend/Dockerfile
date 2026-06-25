FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY backend/ ./backend/
RUN mkdir -p uploads schemas downloads
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
