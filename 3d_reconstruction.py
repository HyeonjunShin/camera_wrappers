import cv2
import numpy as np
import open3d as o3d
import threading
import time
from queue import Queue
from camera_devices import kinect_wrapper

# 시스템 제어 글로벌 변수
running = True
# (카메라 Pose, 실시간 추적 중인 전역 3D 특징점들)을 패킹하여 전달할 큐
data_queue = Queue(maxsize=1)

# ==========================================
# 1. 전역 지도(Global Map) 자료구조 정의
# ==========================================
class MapPoint:
    """3D 공간상에 고정된 고유 랜드마크 점 객체"""
    def __init__(self, pt_id, pos_3d, descriptor):
        self.id = pt_id
        self.pos = pos_3d            # np.array([X, Y, Z]) - 세계 좌표계 기준
        self.descriptor = descriptor    # 이 3D 점을 대표하는 ORB 기술자 (1, 32)
        self.observed_kf_ids = []    # 이 점을 관측한 키프레임 ID 목록

class Keyframe:
    """지도의 이정표가 되는 고정 키프레임 객체"""
    def __init__(self, kf_id, pose):
        self.id = kf_id
        self.pose = pose            # 4x4 행렬 (카메라 -> 세계)

class GlobalMap:
    """전역 지도 매니저 및 컨테이너"""
    def __init__(self):
        self.keyframes = {}         # {kf_id: Keyframe}
        self.map_points = {}        # {pt_id: MapPoint}
        self.pt_id_counter = 0
        self.kf_id_counter = 0

    def add_keyframe(self, pose):
        kf = Keyframe(self.kf_id_counter, pose)
        self.keyframes[self.kf_id_counter] = kf
        self.kf_id_counter += 1
        return kf

    def add_map_point(self, pos_3d, descriptor):
        mp = MapPoint(self.pt_id_counter, pos_3d, descriptor)
        self.map_points[self.pt_id_counter] = mp
        self.pt_id_counter += 1
        return mp

    def get_all_descriptors(self):
        """지도 내에 누적된 모든 점들의 기술자 행렬과 매핑 ID 리스트를 반환"""
        if not self.map_points: 
            return None, []
        ids = list(self.map_points.keys())
        des = np.vstack([self.map_points[mid].descriptor for mid in ids])
        return des, ids

# ==========================================
# 2. 특징점 뭉침 방지 그리드 분산 추출 알고리즘
# ==========================================
def detect_features_grid(image, orb, grid_rows=4, grid_cols=6, max_per_cell=60):
    """
    이미지를 바둑판 격자로 쪼개어 각 구역마다 특징점을 분산 추출함으로써
    좁은 영역에 점들이 몰리는 불균일성 문제를 완벽히 해결합니다.
    """
    h, w = image.shape[:2]
    cell_h = h // grid_rows
    cell_w = w // grid_cols
    
    all_keypoints = []
    all_descriptors = []
    
    for r in range(grid_rows):
        for c in range(grid_cols):
            # 구역별 ROI 마스크 생성
            mask = np.zeros((h, w), dtype=np.uint8)
            y_start = r * cell_h
            y_end = (r + 1) * cell_h if r < grid_rows - 1 else h
            x_start = c * cell_w
            x_end = (c + 1) * cell_w if c < grid_cols - 1 else w
            
            mask[y_start:y_end, x_start:x_end] = 255
            
            # 격자 내부에서만 탐지
            kp = orb.detect(image, mask)
            if len(kp) == 0: 
                continue
                
            # 한 곳에 너무 많으면 강도(Response) 순 정렬 후 상위권만 커트
            if len(kp) > max_per_cell:
                kp = sorted(kp, key=lambda x: x.response, reverse=True)[:max_per_cell]
                
            kp, des = orb.compute(image, kp)
            if des is not None:
                all_keypoints.extend(kp)
                all_descriptors.append(des)
                
    if len(all_descriptors) == 0: 
        return [], None
    return all_keypoints, np.vstack(all_descriptors)

# ==========================================
# 3. 비전 연산 백그라운드 스레드 (Frame-to-Map)
# ==========================================
def vision_thread():
    global running
    camera = kinect_wrapper.KinectCamera()
    camera.start()

    # 카메라 내장 파라미터 셋업
    fx, fy, cx, cy = camera.K[0, 0], camera.K[1, 1], camera.K[0, 2], camera.K[1, 2]
    K = np.array(camera.K, dtype=np.float32)

    # 그리드 분할 연산을 위해 nfeatures 총량을 넉넉하게 확장
    orb = cv2.ORB_create(nfeatures=4000, scaleFactor=1.2, nlevels=8)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    global_map = GlobalMap()
    current_pose = np.eye(4)
    is_initialized = False

    while running:
        frame = camera.get_frame()
        if frame is None: 
            continue
        color, depth, ts = frame

        gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
        
        # 🌟 그리드 분산 기법 적용 특징점 추출
        kp_curr, des_curr = detect_features_grid(gray, orb, grid_rows=4, grid_cols=6, max_per_cell=60)
        if des_curr is None or len(kp_curr) == 0: 
            continue

        display_color = color.copy()

        # 🌟 시스템 첫 프레임 초기화
        if not is_initialized:
            first_kf = global_map.add_keyframe(current_pose.copy())
            for i, kp in enumerate(kp_curr):
                u, v = map(int, kp.pt)
                z_mm = depth[v, u]
                if z_mm == 0 or z_mm > 4000: continue
                
                z_m = z_mm / 1000.0
                x_m = (u - cx) * z_m / fx
                y_m = (v - cy) * z_m / fy
                
                mp_pos = np.array([x_m, y_m, z_m])
                mp = global_map.add_map_point(mp_pos, des_curr[i:i+1])
                mp.observed_kf_ids.append(first_kf.id)
                
            is_initialized = True
            print(f"[SLAM] 초기화 완료! 초기 등록된 MapPoints: {len(global_map.map_points)}")
            continue

        # 🌟 전역 지도 데이터와 현재 프레임 매칭 (Frame-to-Map Tracking)
        map_descriptors, map_point_ids = global_map.get_all_descriptors()
        
        if map_descriptors is not None and len(kp_curr) > 10:
            matches = bf.knnMatch(map_descriptors, des_curr, k=2)
            
            # 시점 변화율에 대응하기 위해 Ratio 조건 문턱값을 0.70으로 매칭력 보강
            good_matches = [m for m_n in matches if len(m_n) == 2 for m, n in [m_n] if m.distance < 0.70 * n.distance]
            
            # PnP 최소 가동 조건 완화 (추적 끊김 현상 방지)
            if len(good_matches) >= 8:
                pts_3d_world = []
                pts_2d_curr = []
                
                for m in good_matches:
                    mp_id = map_point_ids[m.queryIdx]
                    pts_3d_world.append(global_map.map_points[mp_id].pos)
                    pts_2d_curr.append(kp_curr[m.trainIdx].pt)
                
                pts_3d_world = np.array(pts_3d_world, dtype=np.float32)
                pts_2d_curr = np.array(pts_2d_curr, dtype=np.float32)
                
                # 유연한 예외 반경 조절을 위해 reprojectionError를 3.0으로 셋업
                success, rvec, tvec, inliers = cv2.solvePnPRansac(
                    pts_3d_world, pts_2d_curr, K, distCoeffs=None,
                    flags=cv2.SOLVEPNP_ITERATIVE, confidence=0.99, reprojectionError=3.0
                )
                
                if success and inliers is not None:
                    inlier_idx = inliers.squeeze()
                    if inliers.ndim == 0 or inlier_idx.ndim == 0: 
                        inlier_idx = np.array([inlier_idx])
                    
                    R, _ = cv2.Rodrigues(rvec)
                    T_w2c = np.eye(4)
                    T_w2c[:3, :3] = R
                    T_w2c[:3, 3] = tvec.squeeze()
                    
                    # 🌟 고정된 전역 맵 타겟이므로 누적 오차가 없어 흐르지 않는 정밀 Pose 도출
                    current_pose = np.linalg.inv(T_w2c)
                    
                    # 🌟 동적 지도 확장 메커니즘 (이동 거리 혹은 추적점 부족 현상 방어)
                    last_kf = global_map.keyframes[list(global_map.keyframes.keys())[-1]]
                    dist = np.linalg.norm(current_pose[:3, 3] - last_kf.pose[:3, 3])
                    n_inliers = len(inlier_idx)
                    
                    # 15cm 이동했거나, 시점이 급변해 매핑 포인트가 30개 미만으로 떨어졌을 때 맵 확장
                    if dist > 0.15 or n_inliers < 30:
                        new_kf = global_map.add_keyframe(current_pose.copy())
                        
                        # 새로운 구역의 점들을 전역 맵포인트 랜드마크로 대거 영입
                        for i, kp in enumerate(kp_curr):
                            u, v = map(int, kp.pt)
                            z_mm = depth[v, u]
                            if z_mm == 0 or z_mm > 4000: 
                                continue
                            
                            # 기존에 이미 추적 성공한 trainIdx 특징점들은 중복 생성 패스
                            if i in [good_matches[idx].trainIdx for idx in inlier_idx if idx < len(good_matches)]:
                                continue
                            
                            z_m = z_mm / 1000.0
                            x_m = (u - cx) * z_m / fx
                            y_m = (v - cy) * z_m / fy
                            
                            pt_homo = np.array([x_m, y_m, z_m, 1.0])
                            pt_w = (current_pose @ pt_homo)[:3]
                            
                            mp = global_map.add_map_point(pt_w, des_curr[i:i+1])
                            mp.observed_kf_ids.append(new_kf.id)
                        
                        print(f"[Map System] 확장 완료. 누적 랜드마크 점: {len(global_map.map_points)}")
                    
                    # Open3D 3D 시각화용 활성 인라이어 데이터셋 패킹
                    active_pts_global = pts_3d_world[inlier_idx]
                    
                    # 🌟 2D OpenCV 화면용 특징점 시각화 (전체 무작위 점=빨간색, 매칭인라이어=녹색 대형 원)
                    for kp in kp_curr:
                        cv2.circle(display_color, (int(kp.pt[0]), int(kp.pt[1])), 2, (0, 0, 255), -1)
                    for pt in pts_2d_curr[inlier_idx]:
                        cv2.circle(display_color, (int(pt[0]), int(pt[1])), 5, (0, 255, 0), -1)
                        
                    cv2.putText(display_color, f"Total MapPoints: {len(global_map.map_points)} | Inliers: {n_inliers}", 
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                    
                    # 큐 데이터 스레드 전송
                    if data_queue.full():
                        try: data_queue.get_nowait()
                        except: pass
                    data_queue.put((current_pose.copy(), active_pts_global.copy()))
                else:
                    cv2.putText(display_color, "TRACKING LOST (PnP Fail)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                cv2.putText(display_color, "TRACKING LOST (Low Matches)", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.imshow("Kinect Core Tracker", display_color)
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break

    camera.stop()
    running = False

# ==========================================
# 4. 메인 스레드 (Open3D 렌더링 및 자유 뷰)
# ==========================================
def main():
    global running
    # 비전 연산 스레드 백그라운드 구동
    t = threading.Thread(target=vision_thread)
    t.start()

    # Open3D 생성 및 품질 조절
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Global Map-Based SLAM Visualizer", width=1024, height=768)
    
    render_opt = vis.get_render_option()
    render_opt.point_size = 5.0
    render_opt.background_color = np.array([0.1, 0.1, 0.1]) # 고대조용 다크 스크린
    
    # 0번 원점 격자 좌표축
    global_axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5, origin=[0, 0, 0])
    vis.add_geometry(global_axis)

    # 실시간 구동할 카메라 축
    moving_cam = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.15)
    vis.add_geometry(moving_cam)

    # 3D 특징점들을 담아낼 전용 빈 포인트클라우드 객체 선등록 (튕김 원천 봉쇄)
    feature_pc = o3d.geometry.PointCloud()
    vis.add_geometry(feature_pc)

    last_pose = np.eye(4)
    is_first_frame = True

    while running:
        if not data_queue.empty():
            pose, pts_global = data_queue.get()
            
            # 1. 카메라 좌표 격자 위치 트랜스폼 연산
            moving_cam.transform(np.linalg.inv(last_pose))
            moving_cam.transform(pose)
            vis.update_geometry(moving_cam)
            last_pose = pose.copy()
            
            # 2. 3D 공간 특징점 포인트 어레이 치환 및 시각화 반영
            feature_pc.points = o3d.utility.Vector3dVector(pts_global)
            colors = np.ones_like(pts_global) * [0.0, 1.0, 0.0]  # 선명한 형광 초록색
            feature_pc.colors = o3d.utility.Vector3dVector(colors)
            vis.update_geometry(feature_pc)
            
            # 3. 데이터 로딩 시점 딱 한 번 원점 포커싱 (이후 사용자가 자유롭게 마우스 조작 가능)
            if is_first_frame:
                vis.reset_view_point(True)
                is_first_frame = False
        
        # Open3D 비동기 인터랙션 루프 처리
        vis.poll_events()
        vis.update_renderer()
        time.sleep(0.01)

    vis.destroy_window()
    t.join()
    print("[SLAM] 파이프라인이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()