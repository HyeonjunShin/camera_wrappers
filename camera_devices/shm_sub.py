import numpy as np
from multiprocessing import shared_memory
import struct
import cv2

from multiprocessing import resource_tracker

def remove_shm_from_resource_tracker():
    def patched_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(name, rtype)
    
    resource_tracker.register = patched_register

# SharedMemory 연결 전에 호출
remove_shm_from_resource_tracker()

H = 1080
W = 1920
C = 3

COLOR_SHAPE = (H, W, C)
COLOR_SIZE = np.prod(COLOR_SHAPE)

DEPTH_SHAPE = (H, W, 1) 
DEPTH_SIZE = np.prod(DEPTH_SHAPE) * 2
# The 2 means the data type of depth as float16
SLOT_SIZE = COLOR_SIZE + DEPTH_SIZE
HEADER_SIZE = 24


cv2.namedWindow("color", cv2.WINDOW_GUI_NORMAL)
try:
    shm = shared_memory.SharedMemory(name="camera_shm")
    last_processed_count = -1


    frame_count = 0
    while True:
        latest_slot, count, ts = struct.unpack("<QQQ", shm.buf[:HEADER_SIZE])
        
        if count > last_processed_count:
            base_offset = HEADER_SIZE + (latest_slot * SLOT_SIZE)
            
            # 1. Color 읽기
            color = np.frombuffer(
                shm.buf[base_offset : base_offset + COLOR_SIZE], dtype=np.uint8
            ).reshape(COLOR_SHAPE).copy()
            
            depth_offset = base_offset + COLOR_SIZE
            depth = np.frombuffer(
                shm.buf[depth_offset : depth_offset + DEPTH_SIZE], dtype=np.uint16
            ).reshape(DEPTH_SHAPE).copy()
            
            last_processed_count = count

            depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)

            # print(np.repeat(depth_norm[...,None], 3, 2).shape)
            view = np.hstack([color, depth_color])

            cv2.putText(color, f"Slot: {latest_slot} | TS: {ts}", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            cv2.imshow("color", view)

            if cv2.waitKey(1) == ord('q'):
                break

except Exception as e:
    print(f"에러: {e}")
finally:
    # 3. shm이 성공적으로 생성(정의)되었을 때만 닫습니다.
    if shm is not None:
        shm.close()
        print("🚪 공유 메모리 연결을 닫았습니다.")
    cv2.destroyAllWindows()