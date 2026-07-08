FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 预处理知识库
RUN python knowledge_base.py

EXPOSE ${PORT:-3000}

# 使用 shell 格式 CMD，支持读取 $PORT 环境变量
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-3000}
