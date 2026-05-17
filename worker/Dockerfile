# Grand Contract v1.0 — M6 GPU Worker Container
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3-pip \
    ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer cached separately
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY worker/ ./worker/

CMD ["python3", "-m", "worker.main"]
