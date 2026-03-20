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
    libxkbcommon-x11-0 \
    x11-apps \
    python3 \
    python3-pip \
    python3-dev \
    libglib2.0-0 
    # fonts-dejavu \
    # fontconfig \
    # libfontconfig1 \
    # && fc-cache -fv

RUN mkdir -p /usr/local/lib/python3.12/dist-packages/cv2/qt/fonts \
    && ln -sf /usr/share/fonts/truetype/dejavu/*.ttf /usr/local/lib/python3.12/dist-packages/cv2/qt/fonts/


RUN pip3 install --no-cache-dir eclipse-zenoh opencv-python --break-system-packages

COPY setup-kinect-sdk.sh /tmp/setup-kinect-sdk.sh
RUN chmod +x /tmp/setup-kinect-sdk.sh \
    && /tmp/setup-kinect-sdk.sh \
    && rm /tmp/setup-kinect-sdk.sh

