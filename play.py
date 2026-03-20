import cv2
import numpy as np
import os
import glob

def replay_session(session_id=None):
    OUTPUT_DIR = "./output"

    # 1. 세션 폴더 설정 (지정하지 않으면 가장 최근 폴더 선택)
    if session_id is None:
        sessions = sorted([d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))])
        if not sessions:
            print("재생할 데이터가 없습니다.")
            return
        session_id = sessions[-1]  # 가장 마지막(최신) 세션
    
    session_path = os.path.join(OUTPUT_DIR, session_id)
    print(f"Replaying session: {session_id}")

    # 2. 파일 목록 정렬해서 가져오기
    files = sorted(glob.glob(os.path.join(session_path, "*.npz")))
    if not files:
        print("폴더 내에 .npz 파일이 없습니다.")
        return

    cv2.namedWindow('Replay')
    
    idx = 0
    while idx < len(files):
        # .npz 파일 로드
        data = np.load(files[idx])
        color = data['color']
        depth = data['depth']
        timestamp = data.get('timestamp', 0) # 저장된 timestamp 불러오기

        # 화면에 정보 표시용 텍스트
        display_img = color.copy()
        info_text = f"Frame: {idx}/{len(files)-1} | Time: {timestamp:.2f}"
        cv2.putText(display_img, info_text, (30, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Depth 시각화 (옵션: 보고 싶을 때 주석 해제)
        # depth_view = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        # depth_color = cv2.applyColorMap(depth_view, cv2.COLORMAP_JET)
        # cv2.imshow("Depth", depth_color)

        cv2.imshow("Replay", display_img)

        # 키 제어
        key = cv2.waitKey(33) # 약 30 FPS 속도
        if key == ord('q'): # 종료
            break
        elif key == ord('p'): # 일시정지
            cv2.waitKey(-1)
        
        idx += 1

    print("재생이 완료되었습니다.")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 특정 폴더를 재생하려면 session_id="20240522_..." 처럼 입력하세요.
    replay_session("20260320_141045") 
