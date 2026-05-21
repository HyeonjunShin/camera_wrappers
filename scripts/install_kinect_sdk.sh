#!/bin/bash

set -e

# 0. 필수 의존성 라이브러리 및 X11, USB 관련 패키지 설치
echo "--- 필수 시스템 패키지 및 디스플레이 라이브러리 설치 ---"
sudo apt-get update
sudo apt-get install -y \
    xorg-dev \
    libxrandr-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    libsoundio-dev \
    libudev-dev \
    libusb-1.0-0-dev \
    python3-pip \
    wget \
    git \
    cmake \
    build-essential

cd /tmp
REPO_DIR="Azure-Kinect-Sensor-SDK"

# 1. 저장소 클론 및 이동
if [ ! -d "$REPO_DIR" ]; then
    git clone -b v1.4.2 --recursive https://github.com/microsoft/Azure-Kinect-Sensor-SDK.git
fi
cd $REPO_DIR

# 2. 서브모듈 다운로드를 위한 1차 CMake 실행
mkdir -p build && cd build
echo "--- 종속성 서브모듈 다운로드 중 (1차 CMake) ---"
# libusb 헤더 경로(/usr/include/libusb-1.0)를 강제로 인클루드 경로에 명시
cmake .. \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_C_FLAGS="-w -D_GNU_SOURCE -I/usr/include/libusb-1.0" \
    -DCMAKE_CXX_FLAGS="-w -I/usr/include/libusb-1.0"

# 3. 소스 코드 수정 (Patching) & Udev Rules 설정
cd ..
echo "--- 소스 코드 수정 및 디바이스 권한 설정 시작 ---"

# 카메라 권한 설정을 위한 udev rules 복사
# if [ -f "scripts/99-k4a.rules" ]; then
#     sudo cp scripts/99-k4a.rules /etc/udev/rules.d/
#     sudo udevadm control --reload-rules && sudo udevadm trigger
#     echo "--- 디바이스 권한 규칙(udev rules) 적용 완료 ---"
# fi

# [A] OpenSSL 3.0 대응을 위한 x509_openssl.c 파일 안전하게 교체 (통째로 덮어쓰기)
TARGET_FILE="extern/azure_c_shared/src/adapters/x509_openssl.c"
if [ -f "$TARGET_FILE" ]; then
    cat << 'EOF' > "$TARGET_FILE"
#include <stddef.h>
#include "azure_c_shared_utility/x509_openssl.h"
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/crypto.h>
#include "azure_c_shared_utility/xlogging.h"

static void log_openssl_error(void)
{
    unsigned long error_code;
    while ((error_code = ERR_get_error()) != 0)
    {
        LogError("OpenSSL Error: %s", ERR_error_string(error_code, NULL));
    }
}

int x509_openssl_add_ecc_key(SSL_CTX* ssl_ctx, const char* ecc_key)
{
    (void)ssl_ctx;
    (void)ecc_key;
    return 0;
}

int x509_openssl_add_certificates(SSL_CTX* ssl_ctx, const char* certificates)
{
    int result;
    if (ssl_ctx == NULL || certificates == NULL)
    {
        LogError("Invalid argument (ssl_ctx=%p, certificates=%p)", ssl_ctx, certificates);
        result = MU_FAILURE;
    }
    else
    {
        BIO* bio = BIO_new_mem_buf((void*)certificates, -1);
        if (bio == NULL)
        {
            LogError("BIO_new_mem_buf failed");
            result = MU_FAILURE;
        }
        else
        {
            X509* cert;
            result = 0;
            while ((cert = PEM_read_bio_X509(bio, NULL, NULL, NULL)) != NULL)
            {
                if (SSL_CTX_add_extra_chain_cert(ssl_ctx, cert) != 1)
                {
                    LogError("SSL_CTX_add_extra_chain_cert failed");
                    X509_free(cert);
                    result = MU_FAILURE;
                    break;
                }
            }
            BIO_free(bio);
        }
    }
    return result;
}
EOF
    echo "[$TARGET_FILE] OpenSSL 3.0 호환 코드로 덮어쓰기 완료."
fi

# [B] 헤더 파일 추가 (중복 체크 포함 함수)
patch_header() {
    FILE=$1; HEADER=$2; LINE=$3
    if [ -f "$FILE" ]; then
        if ! grep -q "$HEADER" "$FILE"; then
            sed -i "${LINE}i ${HEADER}" "$FILE"
            echo "[$FILE] ${HEADER} 추가 완료 (Line ${LINE})."
        else
            echo "[$FILE] ${HEADER}가 이미 존재합니다."
        fi
    fi
}

# 요청하신 모든 헤더 추가 작업
patch_header "tools/k4amicrophonelistener.cpp" "#include <cstring>" 7
patch_header "extern/libebml/src/src/EbmlSInteger.cpp" "#include <limits>" 37
patch_header "examples/viewer/opengl/main.cpp" "#include <limits>" 6
patch_header "tools/k4aviewer/k4aaudiochanneldatagraph.h" "#include <string>" 10
patch_header "tools/k4aviewer/perfcounter.h" "#include <string>" 7
patch_header "tools/k4aviewer/k4amicrophonelistener.cpp" "#include <cstring>" 11

# 4. 최종 빌드 및 설치
cd build
echo "--- 컴파일 시작 (make) ---"
make -j$(nproc)

echo "--- 시스템 설치 (sudo make install) ---"
sudo make install

# 5. Depth Engine (libdepthengine.so) 추출 및 설치
echo "--- Depth Engine 설치 시작 ---"
TEMP_DIR="/tmp/k4a_extract"
mkdir -p $TEMP_DIR && cd $TEMP_DIR

# .deb 패키지 다운로드 및 압축 해제
wget -q https://packages.microsoft.com/ubuntu/18.04/prod/pool/main/libk/libk4a1.4/libk4a1.4_1.4.1_amd64.deb
ar x libk4a1.4_1.4.1_amd64.deb
tar -xzf data.tar.gz

# 라이브러리 복사 및 심볼릭 링크 생성
sudo cp usr/lib/x86_64-linux-gnu/libk4a1.4/libdepthengine.so.2.0 /usr/lib/x86_64-linux-gnu/
sudo ln -sf /usr/lib/x86_64-linux-gnu/libdepthengine.so.2.0 /usr/lib/x86_64-linux-gnu/libdepthengine.so.2
sudo ln -sf /usr/lib/x86_64-linux-gnu/libdepthengine.so.2 /usr/lib/x86_64-linux-gnu/libdepthengine.so

# 6. Python 바인딩 설치 (pyk4a)
echo "--- pyk4a (Python Binding) 설치 시작 ---"
pip3 install pyk4a --break-system-packages

# 정리 및 라이브러리 갱신
# cd / && rm -rf $TEMP_DIR && rm -rf /tmp/$REPO_DIR
sudo ldconfig

echo "--- 모든 작업이 성공적으로 완료되었습니다! ---"