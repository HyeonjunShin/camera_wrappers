import zenoh
import cv2
import numpy as np
from camera_devices.kinect_wrapper import KinectCamera

class ZenohComm:
    def __init__(self, camera):
        self.camera = camera
    
    def pub(self):
        self.camera.start()
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            cv2.imshow("img", frame[0])
            key = cv2.waitKey(1)
            
            if key == ord('q'):
                break

        camera.stop()


if __name__ == "__main__":
    camera = KinectCamera()
    zenoh_comm = ZenohComm(camera)
    zenoh_comm.pub()

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