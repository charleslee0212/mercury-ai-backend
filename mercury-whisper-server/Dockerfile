FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

EXPOSE 8000

RUN apt-get update && \
  apt-get install -y --no-install-recommends software-properties-common curl && \
  add-apt-repository ppa:deadsnakes/ppa && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.12 python3.12-distutils && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /whisper-mercury-server

COPY requirements.txt .

# Download and install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
  python3.12 get-pip.py && \
  rm get-pip.py

# Install project dependencies
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

COPY ./server ./server

CMD ["python3.12", "server/src/main.py"]
# Run container: docker run --gpus=all -p 8000:8000 -v ~/charl/Desktop/whisper-mercury-server/SSL:/whisper-mercury-server/SSL -v ~/charl/.cache/huggingface:/root/.cache/huggingface charleslee0212/mercury-server-test:dev
# docker run --network host --gpus=all charleslee0212/mercury-server-test:dev