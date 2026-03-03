FROM mcr.microsoft.com/devcontainers/base:noble

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    build-essential \
    cmake \
    git \
    ninja-build \
    pkg-config \
    libusb-1.0-0-dev \
    libturbojpeg0-dev \
    libgl1-mesa-dev \
    libsoundio-dev \
    libx11-dev \
    libxcursor-dev \
    libxinerama-dev \
    libxrandr-dev \
    libusb-1.0-0 \
    uuid-dev \
    eclipse-zenoh

COPY setup-kinect-sdk.sh /tmp/setup-kinect-sdk.sh
RUN chmod +x /tmp/setup-kinect-sdk.sh \
    && /tmp/setup-kinect-sdk.sh \
    && rm /tmp/setup-kinect-sdk.sh