FROM python:3.12.12-slim
USER root
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
RUN python3 -m pip install --no-cache-dir \
    torch==2.6.0+cpu torchvision==0.21.0+cpu --index-url https://download.pytorch.org/whl/cpu
COPY requirements-learning.txt /tmp/requirements-learning.txt
RUN python3 -m pip install --no-cache-dir -r /tmp/requirements-learning.txt && python3 -m pip check
USER 10001:10001
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 HF_HOME=/tmp/huggingface
ENTRYPOINT ["python3"]
