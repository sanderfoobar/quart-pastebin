FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt clean && apt update
RUN apt install -y git build-essential wget curl ngrep unzip file ssh zip libjpeg8-dev zlib1g-dev python3 python3-dev python3-pip

WORKDIR /app
COPY paste /app/paste/
COPY requirements.txt .
COPY asgi.py .
COPY settings.py .

RUN CC="cc -mavx2" pip3 install -r requirements.txt

CMD ["hypercorn", "--access-logfile", "-", "--workers", "1", "--bind", "0.0.0.0:18200", "asgi:app"]
