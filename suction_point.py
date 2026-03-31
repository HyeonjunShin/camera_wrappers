import cv2
import numpy as np
from camera_devices.kinect_wrapper import KinectCamera

# 설정 파라미터
ROI_SIZE = 20  # 흡착 패드 크기에 맞춘 주변 영역 (픽셀 단위)
FLATNESS_THRESHOLD = 0.01  # 평탄도 임계값 (작을수록 평평함)

mouse_x, mouse_y = 0, 0
def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_x, mouse_y = x, y

def compute_normal_map(depth, K):
    """
    Depth Map과 내적 행렬(K)을 이용하여 Normal Map을 계산합니다.
    """
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    
    # Sobel 연산자로 x, y 방향 경사도 계산
    dz_dx = cv2.Sobel(depth.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    dz_dy = cv2.Sobel(depth.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    
    # 법선 벡터 계산: n = (-dz/dx, -dz/dy, 1) 방향 성분 활용
    # 실제 카메라 좌표계 투영을 고려한 근사식
    nx = -dz_dx
    ny = -dz_dy
    nz = np.ones_like(depth, dtype=np.float32) * (fx + fy) / (2.0 * depth + 1e-6)
    
    norm = np.sqrt(nx**2 + ny**2 + nz**2)
    normal_map = np.stack([nx/norm, ny/norm, nz/norm], axis=-1)
    return normal_map

def get_best_suction_in_roi(normal_map, depth, x, y, roi_size):
    """
    클릭한 지점 주변 ROI에서 가장 평평한(Normal 변화가 적은) 지점을 찾습니다.
    """
    h, w = depth.shape
    x1, x2 = max(0, x-roi_size), min(w, x+roi_size)
    y1, y2 = max(0, y-roi_size), min(h, y+roi_size)
    
    roi_normals = normal_map[y1:y2, x1:x2]
    roi_depths = depth[y1:y2, x1:x2]
    
    # 각 픽셀의 로컬 분산(평탄도) 계산 - 여기서는 단순화하여 Z축 법선 벡터의 크기 확인
    # nz가 1에 가까울수록 카메라를 정면으로 바라보는 평평한 면입니다.
    flatness_map = 1.0 - roi_normals[:, :, 2] 
    
    # ROI 내에서 가장 평평한 곳의 인덱스 추출
    min_val, _, min_loc, _ = cv2.minMaxLoc(flatness_map)
    
    best_x = x1 + min_loc[0]
    best_y = y1 + min_loc[1]
    
    return (best_x, best_y), roi_normals[min_loc[1], min_loc[0]], min_val

def main():
    camera = KinectCamera()
    camera.start()
    K = camera.K # 내적 행렬 사용
    
    cv2.namedWindow('img')
    cv2.setMouseCallback('img', mouse_callback)

    while True:
        frame = camera.get_frame()
        if frame is None: continue

        color, depth, _ = frame
        
        # 1. Normal Map 생성
        # Depth의 노이즈 제거를 위해 가우시안 블러 적용 권장
        smooth_depth = cv2.GaussianBlur(depth.astype(np.float32), (5, 5), 0)
        normal_map = compute_normal_map(smooth_depth, K)

        # 2. Suction 가능 지점 분석
        best_pt, normal_vec, score = get_best_suction_in_roi(normal_map, depth, mouse_x, mouse_y, ROI_SIZE)
        
        # 시각화용 Normal Map (0~255 변환)
        normal_vis = ((normal_map + 1.0) * 127.5).astype(np.uint8)

        # 3. 결과 표시
        res_color = color.copy()
        cv2.circle(res_color, (mouse_x, mouse_y), ROI_SIZE, (255, 255, 0), 1) # 탐색 영역
        cv2.circle(res_color, best_pt, 5, (0, 0, 255), -1) # 최적 흡착점
        
        # 정보 텍스트
        text = f"Depth: {depth[best_pt[1], best_pt[0]]:.1f}mm, Normal: [{normal_vec[0]:.2f}, {normal_vec[1]:.2f}, {normal_vec[2]:.2f}]"
        cv2.putText(res_color, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(res_color, f"Flatness Score: {score:.4f} (lower is better)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("img", res_color)
        cv2.imshow("normal_map", normal_vis)
        
        if cv2.waitKey(1) == ord('q'): break

    camera.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()