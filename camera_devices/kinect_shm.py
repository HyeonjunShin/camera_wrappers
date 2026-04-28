import numpy as np
from multiprocessing import shared_memory
import struct
import time
from camera_devices.kinect_wrapper import KinectCamera
from multiprocessing import resource_tracker

def remove_shm_from_resource_tracker():
    def patched_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(name, rtype)
    
    resource_tracker.register = patched_register

def shm_pub(camera):
    camera = KinectCamera()
    camera.start()
    K = camera.K
    D = camera.D
    W = camera.width
    H = camera.height
    C = 3

    COLOR_SIZE = (H * W * C)
    DPETH_SIZE = (H * W) * 2 # The 2 means the data type of depth as float16
    SLOT_SIZE = COLOR_SIZE + DPETH_SIZE
    # 헤더: [Latest Slot(Q)] + [Frame Count(Q)] + [Timestamp(Q)] = 24 bytes
    HEADER_SIZE = 24
    TOTAL_SIZE = HEADER_SIZE + (SLOT_SIZE * 2) # 두 개의 슬롯 확보

    try:
        shm = shared_memory.SharedMemory(name="camera_shm", create=True, size=TOTAL_SIZE)
        print(f"The camera is operating.")

        frame_count = 0
        while True:
            write_slot = frame_count % 2
            base_offset = HEADER_SIZE + (write_slot * SLOT_SIZE)

            color, depth, timestamp = camera.get_frame()

            shm.buf[base_offset : base_offset + COLOR_SIZE] = color.tobytes()

            depth_offset = base_offset + COLOR_SIZE
            shm.buf[depth_offset : depth_offset + DPETH_SIZE] = depth.tobytes()

            shm.buf[:HEADER_SIZE] = struct.pack("<QQQ", write_slot, frame_count, timestamp)

            frame_count += 1
            time.sleep(0.03) # 30 FPS

    except KeyboardInterrupt:
        pass
    finally:
        shm.close()
        shm.unlink()

def shm_sub():
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



def main():
    camera = KinectCamera()
    camera.start()
    K = camera.K
    D = camera.D
    W = camera.width
    H = camera.height
    C = 3
    print(K)
    print(D)
    print(H, W, C)

    
        camera.stop()

if __name__ == "__main__":
    main()