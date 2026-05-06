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

class ShmCamera:
    def __init__(self):
        remove_shm_from_resource_tracker() # Shm 파일 자동삭제 방지
        self.H = 1080
        self.W = 1920
        self.C = 3

        self.COLOR_SHAPE = (self.H, self.W, self.C)
        self.COLOR_SIZE = np.prod( self.COLOR_SHAPE)

        self.DEPTH_SHAPE = (self.H, self.W, 1) 
        self.DEPTH_SIZE = np.prod(self.DEPTH_SHAPE) * 2
        # The 2 means the data type of depth as float16
        self.SLOT_SIZE = self.COLOR_SIZE + self.DEPTH_SIZE
        self.HEADER_SIZE = 24
        try:
            self.shm = shared_memory.SharedMemory(name="camera_shm")
            self.last_processed_count = -1
        except Exception as e:
            print(f"ShmCamera Error: {e}")

    def get_frame(self):
        latest_slot, count, timestamp = struct.unpack("<QQQ", self.shm.buf[:self.HEADER_SIZE])
        
        if count > self.last_processed_count:
            base_offset = self.HEADER_SIZE + (latest_slot * self.SLOT_SIZE)
            
            # 1. Color 읽기
            color = np.frombuffer(
                self.shm.buf[base_offset : base_offset + self.COLOR_SIZE], dtype=np.uint8
            ).reshape(self.COLOR_SHAPE).copy()
            
            # 2. Depth 읽기
            depth_offset = base_offset + self.COLOR_SIZE
            depth = np.frombuffer(
                self.shm.buf[depth_offset : depth_offset + self.DEPTH_SIZE], dtype=np.uint16
            ).reshape(self.DEPTH_SHAPE).copy()
            
            self.last_processed_count = count
            return color, depth, timestamp
        
        return None

    def close(self):
        if self.shm is not None:
            self.shm.close()
            print("Close the shm.")

# def main():
#     shm_cam = ShmCamera()
#     COLOR_SHAPE = shm_cam.COLOR_SHAPE
#     COLOR_SIZE = shm_cam.COLOR_SIZE
#     DEPTH_SHAPE = shm_cam.DEPTH_SHAPE
#     DEPTH_SIZE = shm_cam.DEPTH_SIZE
#     SLOT_SIZE = shm_cam.SLOT_SIZE
#     HEADER_SIZE = shm_cam.HEADER_SIZE
#     shm = shm_cam.shm
#     last_processed_count = -1

#     try:


#     # cv2.namedWindow("color", cv2.WINDOW_GUI_NORMAL)



#         frame_count = 0
#         while True:
#             latest_slot, count, ts = struct.unpack("<QQQ", shm.buf[:HEADER_SIZE])
#             print(count)
#             if count > last_processed_count:
#                 base_offset = HEADER_SIZE + (latest_slot * SLOT_SIZE)
                
#                 # 1. Color 읽기
#                 color = np.frombuffer(
#                     shm.buf[base_offset : base_offset + COLOR_SIZE], dtype=np.uint8
#                 ).reshape(COLOR_SHAPE).copy()
                
#                 depth_offset = base_offset + COLOR_SIZE
#                 depth = np.frombuffer(
#                     shm.buf[depth_offset : depth_offset + DEPTH_SIZE], dtype=np.uint16
#                 ).reshape(DEPTH_SHAPE).copy()
                
#                 last_processed_count = count

#                 depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
#                 depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)

#                 # print(np.repeat(depth_norm[...,None], 3, 2).shape)
#                 view = np.hstack([color, depth_color])

#                 cv2.putText(color, f"Slot: {latest_slot} | TS: {ts}", (50, 50), 
#                             cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
#                 cv2.imshow("color", view)

#                 if cv2.waitKey(1) == ord('q'):
#                     break

#     except Exception as e:
#         print(f"에러: {e}")
#     finally:
#         # 3. shm이 성공적으로 생성(정의)되었을 때만 닫습니다.
#         if shm is not None:
#             shm.close()
#             print("🚪 공유 메모리 연결을 닫았습니다.")
#         cv2.destroyAllWindows()

# if __name__ == "__main__":
    # main()