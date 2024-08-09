FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

RUN apt-get update && \
  apt-get install -y --no-install-recommends software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.12 python3-pip && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /whisper-mercury-server

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY /faster-whisper-server /whisper-mercury-server/faster-whisper-server

CMD ["python3", "faster-whisper-server/main.py"]
