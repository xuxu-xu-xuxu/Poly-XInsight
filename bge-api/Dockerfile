FROM python:3.10-slim
WORKDIR /app
# 安装 CPU 版 PyTorch（阿里云镜像防超时）
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu \
    -i https://mirrors.aliyun.com/pypi/simple
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY main.py .
CMD ["python3", "main.py"]