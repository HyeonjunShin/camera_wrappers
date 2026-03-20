import zenoh
import cv2
import numpy as np
import struct
import time
from camera_devices.kinect_wrapper import KinectCamera

# 1. Zenoh 설정 (Shared Memory 활성화)
conf = zenoh.Config()
conf.insert_json5("transport/shared_memory/enabled", "true")

session = zenoh.open(conf)
pub = session.declare_publisher(
    "camera/raw",
    congestion_control=zenoh.CongestionControl.DROP,
    reliability=zenoh.Reliability.BEST_EFFORT
)

camera = KinectCamera()
camera.start()

# 최적화 헤더 설정: 
# [curr_time(8), cam_timestamp(8), color_len(4), depth_len(4), rows(4), cols(4)] = 32 bytes
HEADER_SIZE = 32  
payload_buffer = bytearray(1024 * 1024 * 10) # 10MB로 넉넉하게 할당

print(f"Zenoh Shared Memory Streaming: {'Enabled' if 'shared_memory' in str(conf) else 'Disabled'}")
print("Streaming started... (Press Ctrl+C to stop)")

prev_time = time.perf_counter()

try:
    while True:
        frame = camera.get_frame()
        if frame is None:
            continue

        # camera에서 제공하는 원본 timestamp 포함
        color, depth, cam_timestamp = frame
        curr_time = time.perf_counter()

        # Color: JPEG 압축
        _, color_buf = cv2.imencode(".jpg", color, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        color_bytes = color_buf.tobytes()
        c_len = len(color_bytes)
        
        # Depth: Raw 데이터 (uint16)
        depth_bytes = depth.tobytes()
        d_len = len(depth_bytes)
        
        rows, cols = depth.shape

        # 1. 헤더 작성 (d: double 2개, I: unsigned int 4개)
        struct.pack_into('<ddIIII', payload_buffer, 0, curr_time, cam_timestamp, c_len, d_len, rows, cols)
        
        # 2. 데이터 복사
        payload_buffer[HEADER_SIZE : HEADER_SIZE + c_len] = color_bytes
        payload_buffer[HEADER_SIZE + c_len : HEADER_SIZE + c_len + d_len] = depth_bytes

        # 3. Zenoh 전송
        total_size = HEADER_SIZE + c_len + d_len
        pub.put(payload_buffer[:total_size])
        
        # FPS 측정
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        print(f"Pub FPS: {fps:>5.1f} | Cam TS: {cam_timestamp:.3f} | Total: {total_size:>7} bytes", end="\r", flush=True)

except KeyboardInterrupt:
    print("\nStopping streamer...")
except Exception as e:
    print(f"\nError: {e}")
finally:
    camera.stop()
    session.close()