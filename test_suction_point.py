import zenoh
import time
import numpy as np
from camera_devices.shm_sub import ShmCamera
import cv2
import os
os.environ["XDG_SESSION_TYPE"] = "x11"
import open3d as o3d

WIDTH = 1920
HEIGHT = 1080
CHANNELS = 3
TARGET_WIDHT = 448
TARGET_HEIGHT = 256
DEPTH_PATCH_SIZE = 50
DEPTH_HALF_SIZE = DEPTH_PATCH_SIZE // 2

PATCH_MASK = np.arange(-DEPTH_HALF_SIZE, DEPTH_HALF_SIZE + 1)

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

def normal_to_tf(centroid, normal):
    """
    Centroid와 Normal을 결합하여 안정적인 4x4 TF 행렬 생성
    """
    # 1. Z축 설정 (Normal 방향)
    z_axis = normal / np.linalg.norm(normal)
    
    # 2. X축 계산 (카메라의 전역적인 방향을 참조하여 일관성 유지)
    # 카메라 좌표계의 Y축([0, 1, 0])을 참조 벡터로 사용
    ref_vec = np.array([0, 1, 0])
    
    # 만약 Z축과 ref_vec이 평행하면(Singularity), 다른 벡터 사용
    if abs(np.dot(ref_vec, z_axis)) > 0.95:
        ref_vec = np.array([1, 0, 0])
        
    # 외적을 통해 X, Y축 결정 (Gram-Schmidt와 유사한 방식)
    x_axis = np.cross(ref_vec, z_axis)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)

    tf_matrix = np.eye(4)
    tf_matrix[0:3, 0] = x_axis
    tf_matrix[0:3, 1] = y_axis
    tf_matrix[0:3, 2] = z_axis
    tf_matrix[0:3, 3] = centroid
    return tf_matrix

class Viewer3D:
    def __init__(self):
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window(window_name='Viewer 3D', width=800, height=600)
        
        opt = self.vis.get_render_option()
        opt.point_size = 1.0
        opt.background_color = np.asarray([0, 0, 0])

        self.view_ctl = self.vis.get_view_control()
        self.view_ctl.set_constant_z_near(0.01)
        self.view_ctl.set_constant_z_far(5.0)
        self.view_ctl.set_zoom(2)

        self.pcd = o3d.geometry.PointCloud()
        self.vis.add_geometry(self.pcd)

        self.target_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.2)
        self.vis.add_geometry(self.target_frame)

        axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
        self.vis.add_geometry(axes)
    
    def update_pcd(self, points_3d):
        self.pcd.points = o3d.utility.Vector3dVector(points_3d)
        self.pcd.paint_uniform_color([1.0, 0.8, 0.0])
        self.vis.update_geometry(self.pcd)

        centroid = np.mean(points_3d, axis=0)
        self.view_ctl.set_lookat(centroid)
        # self.view_ctl.set_front([0.0, 0.0, -1.0])
        # self.view_ctl.set_up([0.0, -1.0, 0.0])
        self.view_ctl.set_zoom(0.5)

    def update_frame(self, tf):
        new_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.05)
        new_frame.transform(tf)
        
        self.target_frame.vertices = new_frame.vertices
        self.vis.update_geometry(self.target_frame)

    def close(self):
        self.vis.destroy_window()

    def update(self):
        self.vis.poll_events()
        self.vis.update_renderer()


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
        self.depth_patch = None

        self.viewer_3d = Viewer3D()

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
                    self.depth_patch = depth[self.y - DEPTH_HALF_SIZE : self.y + DEPTH_HALF_SIZE + 1, self.x - DEPTH_HALF_SIZE : self.x + DEPTH_HALF_SIZE + 1, 0] * 0.001
                    self.depth_patch = self.depth_patch.ravel()
                    
                    mx, my = np.meshgrid(PATCH_MASK + self.x, PATCH_MASK + self.y)
                    mesh = np.vstack((mx.ravel(), my.ravel())).T.astype(np.float32)

                    # self.z = depth[self.y, self.x, 0] * 0.001
                    # self.z = np.mean(self.depth_patch)

                    if self.z != 0:
                        p_pixel = np.array([[[self.x, self.y]]]).astype(np.float32)
                        # x_normal, y_normal = cv2.undistortPoints(p_pixel, INTRINSIC, DISTORTION).squeeze()
                        x_normal, y_normal = cv2.undistortPoints(mesh, INTRINSIC, DISTORTION).squeeze().T

                        # x_c = x_normal * self.z
                        # y_c = y_normal * self.z
                        # z_c = self.z
                        x_c = x_normal * self.depth_patch
                        y_c = y_normal * self.depth_patch
                        z_c = self.depth_patch

                        # p_camera = np.array([x_c, y_c, z_c, 1])
                        valid_mask = z_c > 0
                        points_3d = np.vstack((x_c[valid_mask], y_c[valid_mask], z_c[valid_mask])).T

                        centroid = np.mean(points_3d, axis=0)
                        centered_pts = points_3d - centroid
                        cov = np.cov(centered_pts.T)
                        evals, evecs = np.linalg.eig(cov)
                        normal = evecs[:, np.argmin(evals)]
                        if normal[2] < 0:
                            normal = -normal

                        tf = normal_to_tf(centroid, normal)

                        self.viewer_3d.update_pcd(points_3d)
                        self.viewer_3d.update_frame(tf)

                        # tf_camera = self.tf_flange @ flange2camera
                        # # p_base = tf_camera @ p_camera
                        # p_base = tf_camera @ tf

                        cv2.circle(view_color, (self.x, self.y), 5, (0, 255, 0), -1)
                        # text = f"u:{self.x:.3f} v:{self.y:.3f} x:{p_base[0]:.3f} y:{p_base[1]:.3f} z:{p_base[2]:.3f} "
                        # cv2.putText(view_color, text, (self.x + 10, self.y - 10), 
                        #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA) # 본문

                cv2.imshow("view", view_color)
                key = cv2.waitKey(1)

                self.viewer_3d.update()
                if key == ord("q"):
                    break
                if key == 32:
                    # tf_camera = self.tf_flange @ flange2camera
                    # p_base = tf_camera @ p_camera
                    
                    # tf_target = np.array([0.0, 1.0, 0.0, p_base[0], 
                    #                       1.0, 1.0, 0.002, p_base[1],
                    #                       0.002, 0.0, -1.0, p_base[2],
                    #                       0.0, 0.0, 0.0, 1.0]).astype(np.str_).tolist()
                    # # tf_target = np.array([-0.001,  1.,     0.001,  p_base[0],
                    # #                         0.985,  0.,     0.173,  p_base[1],
                    # #                         0.173,  0.001, -0.985,  0.05,
                    # #                             0,0,0,1]).astype(np.str_).tolist()
                    
                    # tf_target = ["1", "0.9"] + tf_target
                    # print(tf_target)
                    # self.pub.put(" ".join(tf_target))
                    # print(p_base)
                    if self.tf_flange is not None and 'tf' in locals():
                        # 1. 카메라 기준 TF를 로봇 베이스 기준 TF로 변환
                        tf_camera_const = self.tf_flange @ flange2camera
                        tf_base = tf_camera_const @ tf
                        
                        # 2. 4x4 행렬을 전송용 1차원 리스트로 평탄화 (Row-major)
                        # 기존 코드의 tf_target 형식을 유지하기 위해 flatten() 사용
                        matrix_flat = tf_base.flatten().tolist()
                        
                        # 3. 헤더 데이터 ("1", "0.9")와 결합 및 문자열 변환
                        # matrix_flat은 float 리스트이므로 문자열로 변환 필요
                        tf_send_data = ["1", "0.9"] + [str(round(x, 6)) for x in matrix_flat]
                        
                        print(f"🚀 [Sending TF] Base Frame: {tf_send_data}")
                        self.pub.put(" ".join(tf_send_data))
                    else:
                        print("⚠️ 로봇 TF 데이터가 없거나 계산된 타겟 TF가 없습니다.")

        except KeyboardInterrupt:
            print("\n 모니터링을 종료합니다.")
        finally:
            self.shm_camera.close()
            self.z_session.close()
            self.viewer_3d.close()



def main():
    comm_module = CommModule()
    comm_module.run()



if __name__ == "__main__":
    main()
