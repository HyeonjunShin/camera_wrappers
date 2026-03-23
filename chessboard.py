from camera_devices.kinect_wrapper import KinectCamera
import cv2
import numpy as np

# 체스판 설정 (가로 칸 수, 세로 칸 수) - 내부 코너 개수 기준입니다.
# 예: 10x7 칸 체스판이라면 코너는 9x6개입니다.
CHESSBOARD_SIZE = (9, 6)

def main():
    camera = KinectCamera()
    camera.start()
    
    cv2.namedWindow('Chessboard Tracking')

    while True:
        frame = camera.get_frame()
        if frame is None:
            continue

        color, depth, timestamp = frame
        # 처리 속도를 위해 그레이스케일 변환
        gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)

        # 1. 체스판 코너 찾기
        # ret: 찾았는지 여부, corners: 찾은 코너의 2D 좌표들
        ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD_SIZE, 
                                                 cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)

        if ret:
            # 2. 코너 좌표 정밀화 (Subpixel Accuracy)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            # 3. 화면에 코너 그리기
            cv2.drawChessboardCorners(color, CHESSBOARD_SIZE, corners2, ret)

            # (선택 사항) 특정 코너의 Depth 값 출력 예시 (첫 번째 코너)
            first_corner = corners2[0][0]
            cx, cy = int(first_corner[0]), int(first_corner[1])
            d_val = depth[cy][cx]
            cv2.putText(color, f"First Corner Depth: {d_val}mm", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Chessboard Tracking", color)
        
        if cv2.waitKey(1) == ord('q'):
            break

    camera.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
