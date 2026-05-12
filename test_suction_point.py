import zenoh
import time
import numpy as np
from camera_devices.shm_sub import ShmCamera
import cv2

WIDTH = 1920
HEIGHT = 1080
CHANNELS = 3
TARGET_WIDHT = 448
TARGET_HEIGHT = 256

INTRINSIC = np.array(
    [[907.18255615, 0.0, 962.34729004], [0.0, 906.9387207, 548.12927246], [0.0, 0.0, 1.0]]
)

DISTORTION = np.array(
    [
        2.63843089e-01,
        -2.51909852e00,
        -3.29987561e-05,
        -1.81387455e-04,
        1.62435722e00,
        1.49601102e-01,
        -2.34095073e00,
        1.54302502e00,
    ]
)

flange2camera = np.array([[ 0.0, -1.0, 0.0, 0.0565],
                          [ 1.0, 0.0, 0.0,  0.0],
                          [ 0.0, 0.0, 1.0,  0.0932],
                          [ 0.0, 0.0, 0.0,  1.0]])

# flange2camera = np.array([
# [ 0.00000000e+00, -9.70295726e-01, -2.41921896e-01,  2.83800000e-02],
#  [ 1.00000000e+00,  0.00000000e+00,  0.00000000e+00,  0.00000000e+00],
#  [ 0.00000000e+00, -2.41921896e-01,  9.70295726e-01,  7.89600000e-02],
#  [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,  1.00000000e+00]]
#  )

class CommModule:
    def __init__(self):
        try:
            conf = zenoh.Config()
            self.z_session = zenoh.open(conf)
            self.pub = self.z_session.declare_publisher("detector/response")
            self.sub = self.z_session.declare_subscriber("detector/request", self.on_zenoh)
            print("✅ Zenoh 연결 성공 (Topic: detector/response)")
        except Exception as e:
            print(f"❌ Zenoh 연결 실패: {e}")
            return
        
        cv2.namedWindow("view", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("view", self.on_mouse)
        self.shm_camera = ShmCamera()

        self.tf_flange = None
        self.x = None
        self.y = None
        self.z = None
        
    def on_zenoh(self, sample):
        payload = sample.payload.to_string()
        # print(f"📩 [Received] Path: {sample.key_expr} | Data: {payload}")
        self.tf_flange = np.fromstring(payload, sep=" ").reshape((4,4))
        # print(self.tf_flange)

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.x = x
            self.y = y

    def run(self):
        try:
            # 사용자가 중단할 때까지 계속 대기
            while True:
                frame_data = self.shm_camera.get_frame()
                if frame_data is None:
                    continue
                color, depth, timestamp = frame_data
                view_color = cv2.cvtColor(color, cv2.COLOR_RGB2BGR)
                
                if self.x is not None and self.y is not None:
                    self.z = depth[self.y][self.x][0] * 0.001
                    if self.z != 0:
                        p_pixel = np.array([[[self.x, self.y]]]).astype(np.float32)
                        x_normal, y_normal = cv2.undistortPoints(p_pixel, INTRINSIC, DISTORTION).squeeze()
                        x_c = x_normal * self.z
                        y_c = y_normal * self.z
                        z_c = self.z

                        p_camera = np.array([x_c, y_c, z_c, 1])


                        tf_camera = self.tf_flange @ flange2camera
                        p_base = tf_camera @ p_camera

                        cv2.circle(view_color, (self.x, self.y), 5, (0, 255, 0), -1)
                        text = f"u:{self.x:.3f} v:{self.y:.3f} x:{p_base[0]:.3f} y:{p_base[1]:.3f} z:{p_base[2]:.3f} "
                        cv2.putText(view_color, text, (self.x + 10, self.y - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA) # 본문

                cv2.imshow("view", view_color)
                key = cv2.waitKey(1)
                if key == ord("q"):
                    break
                if key == 32:
                    tf_camera = self.tf_flange @ flange2camera
                    p_base = tf_camera @ p_camera
                    
                    tf_target = np.array([0.0, 1.0, 0.0, p_base[0], 
                                          1.0, 1.0, 0.002, p_base[1],
                                          0.002, 0.0, -1.0, p_base[2],
                                          0.0, 0.0, 0.0, 1.0]).astype(np.str_).tolist()
                    # tf_target = np.array([-0.001,  1.,     0.001,  p_base[0],
                    #                         0.985,  0.,     0.173,  p_base[1],
                    #                         0.173,  0.001, -0.985,  0.05,
                    #                             0,0,0,1]).astype(np.str_).tolist()
                    
                    tf_target = ["1", "0.9"] + tf_target
                    print(tf_target)
                    self.pub.put(" ".join(tf_target))
                    # print(p_base)
                    

        except KeyboardInterrupt:
            print("\n 모니터링을 종료합니다.")
        finally:
            self.shm_camera.close()
            self.z_session.close()




def main():
    comm_module = CommModule()
    comm_module.run()



if __name__ == "__main__":
    main()
