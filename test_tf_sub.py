import zenoh
import numpy as np
np.set_printoptions(suppress=True, precision=4)
from camera_devices.kinect_wrapper import KinectCamera
from camera_devices.utils import undistort_points
import cv2
import json


class Detector_with_zenoh:
    def __init__(self):
        self.flange2camera = [
            [ 0.0, -0.93969262, -0.34202014, 0.09292 ],
            [ 1.0,  0.0,        0.0,         0.032   ],
            [ 0.0, -0.34202014, 0.93969262,  0.17445 ],
            [ 0.0,  0.0,        0.0,         1.0     ]
        ]
        self.flange2camera = np.array(self.flange2camera, dtype=float)

        self.mouse_x = 0
        self.mouse_y = 0

        self.camera = KinectCamera()
        self.camera.start()
        self.K = self.camera.K
        # K = [K[0][0], K[1][1], K[2][0], K[2][1]]
        self.D = self.camera.D
        
        conf = zenoh.Config()
        self.session = zenoh.open(conf)
        sub = self.session.declare_subscriber("detector/request", self.on_request)
        self.pub = self.session.declare_publisher("detector/response")

    def on_request(self, sample):
        data = sample.payload.to_string()
        state = data[0]
        tf_flange = data[1:]
        tf_flange = np.fromstring(tf_flange, sep=' ').reshape(4, 4)

        self.tf_camera = tf_flange @ self.flange2camera
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_x, self.mouse_y = x, y

    def run(self):
        cv2.namedWindow('img', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('img', 800, 600)
        cv2.setMouseCallback('img', self.mouse_callback)

        while True:
            frame = self.camera.get_frame()
            if frame is None:
                continue

            color, depth, timestamp = frame

            x, y = cv2.undistortPoints(np.array([[self.mouse_x, self.mouse_y]], dtype=np.float32), self.K, self.D).squeeze()
            # x, y = undistort_points(mouse_x, mouse_y, K, D)
            z_c = depth[self.mouse_y][self.mouse_x] / 1000
            x_c = x * z_c
            y_c = y * z_c
            
            # print("Camera coordinates points")
            # print(x, y, z_c)

            p_camera = np.array([x_c, y_c, z_c, 1.0])
            p_robot = self.tf_camera @ p_camera
            # print(p_camera)
            # print(p_robot)
            # print()
            # print(self.tf_camera)

            text = f"U: {self.mouse_x}, V: {self.mouse_y}, depth: {depth[self.mouse_y][self.mouse_x]}"
            cv2.putText(color, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            text = f"Camera: {x_c}, {y_c}, {z_c} "
            cv2.putText(color, text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            text = f"Robot: {p_robot[0]}, {p_robot[1]}, {p_robot[2]} "
            cv2.putText(color, text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.circle(color, (self.mouse_x, self.mouse_y), 4, (0,255,0), -1, cv2.LINE_AA)
            color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
            cv2.imshow("img", color)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            if key == 32:

                data = [0.0, 1.0]
                data += np.array([0.0, 1.0,  0.0, p_robot[0], 
                                 1.0, 0.0,  0.0, p_robot[1],
                                 0.0, 0.0, -1.0, p_robot[2],
                                 0.0, 0.0,  0.0, 1.0]).tolist()
            
                data = " ".join(str(data).split(", "))[1:-1]
                print(data)
                # target_json = {
                    # "matrix": 
                # }
                # json_string = json.dumps(target_json)
                self.pub.put(data)

    def stop(self):
        self.session.close()
        self.camera.stop()
        cv2.destroyAllWindows()


def main():
    detector = Detector_with_zenoh()
    detector.run()
    detector.stop()


        # depth_vis = cv2.normalize(deptooh, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        # depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

        # color = cv2.addWeighted(color, .6, depth_color, .4, 0, 0)




        # # cv2.imshow("depth", depth_color)
        

            


    
if __name__ == "__main__":
    main()
