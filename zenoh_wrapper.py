import zenoh
import cv2
import numpy as np
from camera_devices.kinect_wrapper import KinectCamera
import json 



class ZenohWrapper:
    def __init__(self, ID):
        self.zenoh = zenoh.Zenoh()
        self.ID = ID

    def pub_frame(self, frame):
        self.zenoh.put(f"camera{self.ID}/color", frame.get_color())
        self.zenoh.put(f"camera{self.ID}/depth", frame.get_depth())
        self.zenoh.put(f"camera{self.ID}/timestamp", frame.get_timestamp())
    
    def sub_frame(self):
        color = self.zenoh.get(f"camera{self.ID}/color")
        depth = self.zenoh.get(f"camera{self.ID}/depth")
        timestamp = self.zenoh.get(f"camera{self.ID}/timestamp")
        return Frame(color, depth, timestamp)
    
if __name__ == "__main__":
    camera = KinectCamera()
    zenoh_wrapper = ZenohWrapper(camera)
    zenoh_wrapper.pub()

    # main()



# # 1. Zenoh 세션 초기화
# session = zenoh.open()
# key_expr = 'demo/image'
# pub = session.declare_publisher(key_expr)

# # 2. 이미지 로드 (또는 카메라 프레임)
# img = cv2.imread('image.jpg')
# if img is None:
#     print("이미지를 찾을 수 없습니다.")
#     exit()

# # 3. 인코딩 (데이터 크기를 줄이기 위해 JPEG 압축)
# _, buffer = cv2.imencode('.jpg', img)
# data = buffer.tobytes()

# # 4. 데이터 전송
# print(f"Sending image to {key_expr}...")
# pub.put(data)

# session.close()