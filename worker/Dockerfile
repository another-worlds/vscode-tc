# Grand Contract v1.0 — M6 GPU Worker Container
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Ubuntu 22.04 ships Python 3.10; get 3.12 from deadsnakes PPA
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3.12-distutils \
    ffmpeg libgl1 libglib2.0-0 \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer cached separately
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

COPY worker/ ./worker/

CMD ["python3", "-m", "worker.main"]
