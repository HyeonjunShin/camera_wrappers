import zenoh
import cv2
import numpy as np
import struct
import time

# 1. Zenoh 설정 (공유 메모리 활성화 - 송신부와 동일해야 함)
conf = zenoh.Config()
conf.insert_json5("transport/shared_memory/enabled", "true")

# Zenoh 세션 오픈
session = zenoh.open(conf)

# 헤더 사이즈 정의 (송신부와 일치해야 함)
HEADER_SIZE = 32

def on_data(sample):
    """데이터 수신 시 호출되는 콜백 함수"""
    # Zenoh payload를 bytes 객체로 명시적 변환 (슬라이싱 및 numpy 변환 안정성 확보)
    data = bytes(sample.payload)
    
    # 데이터가 헤더보다 작으면 처리 불가
    if len(data) < HEADER_SIZE:
        print(f"Warning: Received data too small ({len(data)} bytes)")
        return

    try:
        # 1. 헤더 파싱
        # <ddIIII : double(8)x2, unsigned int(4)x4
        header = struct.unpack('<ddIIII', data[:HEADER_SIZE])
        pub_time, cam_timestamp, c_len, d_len, rows, cols = header
        
        # 전체 데이터 길이가 헤더 + 컬러 + 뎁스 크기와 일치하는지 검증
        if len(data) < HEADER_SIZE + c_len + d_len:
            print(f"Warning: Incomplete payload. Expected {HEADER_SIZE + c_len + d_len}, got {len(data)}")
            return

        # 2. Color 이미지 복원 (JPEG 디코딩)
        color_start = HEADER_SIZE
        color_end = HEADER_SIZE + c_len
        
        # 버퍼가 비어있는지 체크
        if c_len == 0:
            print("Warning: Color length is 0")
            return

        color_np = np.frombuffer(data[color_start:color_end], dtype=np.uint8)
        
        # numpy 배열이 비어있는지 최종 확인
        if color_np.size == 0:
            print("Error: Extracted color buffer is empty")
            return

        color_img = cv2.imdecode(color_np, cv2.IMREAD_COLOR)
        
        # 디코딩 실패 여부 확인
        if color_img is None:
            print("Error: cv2.imdecode failed (invalid image data)")
            return
        
        # 3. Depth 이미지 복원 (Raw uint16)
        depth_start = color_end
        depth_end = color_end + d_len
        depth_np = np.frombuffer(data[depth_start:depth_end], dtype=np.uint16)
        depth_img = depth_np.reshape((rows, cols))
        
        # 4. 시각화 처리
        depth_vis = cv2.normalize(depth_img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)
        
        # 지연 시간 및 정보 표시
        latency = (time.perf_counter() - pub_time) * 1000 # ms
        cv2.putText(color_img, f"Latency: {latency:.2f}ms", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow("Color Stream", color_img)
        cv2.imshow("Depth Stream (Visualized)", depth_color)
        cv2.waitKey(1)

    except Exception as e:
        print(f"Error processing frame: {e}")

# 구독(Subscriber) 선언
sub = session.declare_subscriber("camera/raw", on_data)

print(f"Zenoh Receiver (SHM) started on 'camera/raw'")
print("Press Ctrl+C to stop...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping receiver...")
finally:
    cv2.destroyAllWindows()
    session.close()