#!/bin/bash
set -e

echo "--- 0. Installing missing dependencies ---"
sudo apt-get update
sudo apt-get install -y libudev-dev libusb-1.0-0-dev python3 python3-pip

SDK_ROOT="/tmp/Azure-Kinect-Sensor-SDK"

echo "--- 1. SDK Clone and Submodules ---"
cd /tmp
if [ ! -d "$SDK_ROOT" ]; then
    git clone -b v1.4.2 --recursive https://github.com/microsoft/Azure-Kinect-Sensor-SDK.git
fi

# 폴더 진입 확인
cd "$SDK_ROOT"

echo "--- 2. Source Patching ---"

X509_SRC="extern/azure_c_shared/src/adapters/x509_openssl.c"

sed -i 's/OPENSSL_VERSION_NUMBER < 0x30000000L/OPENSSL_VERSION_NUMBER < 0x40000000L/g' "$X509_SRC"
sed -i 's/OPENSSL_VERSION_NUMBER < 0x20000000L/OPENSSL_VERSION_NUMBER < 0x40000000L/g' "$X509_SRC"

sed -i 's/ssl_ctx->extra_certs != NULL/SSL_CTX_get0_chain_certs(ssl_ctx, NULL) != 0/g' "$X509_SRC"
sed -i 's/sk_X509_pop_free(ssl_ctx->extra_certs, X509_free);/SSL_CTX_clear_extra_chain_certs(ssl_ctx);/g' "$X509_SRC"
sed -i 's/ssl_ctx->extra_certs = NULL;//g' "$X509_SRC"

patch_header() {
    if [ -f "$1" ]; then
        grep -q "$2" "$1" || sed -i "1i $2" "$1"
    fi
}

patch_header "extern/libebml/src/src/EbmlSInteger.cpp" "#include <limits>"
patch_header "examples/viewer/opengl/main.cpp" "#include <limits>"
patch_header "tools/k4aviewer/k4aaudiochanneldatagraph.h" "#include <string>"
patch_header "tools/k4aviewer/perfcounter.h" "#include <string>"
patch_header "tools/k4aviewer/k4amicrophonelistener.cpp" "#include <cstring>"

echo "--- 3. Build and Install ---"
mkdir -p build && cd build
cmake .. -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DK4A_COMPILE_AS_ERROR=OFF \
    -DCMAKE_C_FLAGS="-w -D_GNU_SOURCE" \
    -DCMAKE_CXX_FLAGS="-w"
ninja && ninja install

echo "--- 4. Depth Engine extraction ---"
mkdir -p /tmp/k4a_extract && cd /tmp/k4a_extract
wget -q https://packages.microsoft.com/ubuntu/18.04/prod/pool/main/libk/libk4a1.4/libk4a1.4_1.4.1_amd64.deb
ar x libk4a1.4_1.4.1_amd64.deb
tar -xzf data.tar.gz
cp usr/lib/x86_64-linux-gnu/libk4a1.4/libdepthengine.so.2.0 /usr/lib/x86_64-linux-gnu/
ln -sf /usr/lib/x86_64-linux-gnu/libdepthengine.so.2.0 /usr/lib/x86_64-linux-gnu/libdepthengine.so.2
ln -sf /usr/lib/x86_64-linux-gnu/libdepthengine.so.2 /usr/lib/x86_64-linux-gnu/libdepthengine.so
ldconfig

pip3 install pyk4a --break-system-packages

echo "--- 5. Cleanup ---"
rm -rf /tmp/Azure-Kinect-Sensor-SDK /tmp/k4a_extract