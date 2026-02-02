FROM python:3.10-slim

# Install system dependencies for uldaq build
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential automake autoconf libtool \
    libusb-1.0-0-dev swig pkg-config ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build uldaq from source for multi-arch compatibility (ARM/x86)
WORKDIR /tmp
RUN git clone --depth 1 https://github.com/mccdaq/uldaq.git /tmp/uldaq_repo && \
    cd /tmp/uldaq_repo && \
    autoreconf -ivf && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/uldaq_repo

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["python", "main.py"]