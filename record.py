from camera_devices.kinect_wrapper import KinectCamera
import cv2
import numpy as np
import time
import os


def main():
    camera = KinectCamera()
    camera.start()
    # print(camera.K)

    cv2.namedWindow('img')

    OUTPUT_DIR = "./output"
    is_recording = False
    frame_count = 0
    session_id = None

    prev_time = 0
    fps = 0
    frame_times = []
    while True:
        frame = camera.get_frame()
        if frame is None:
            continue
        start_time = time.time()

        color, depth, timestamp = frame

        key = cv2.waitKey(1)
        if key == ord('q'):
            break

        if key == 32:
            if not is_recording:    
                # 이 부분에 OUTPUT_DIR이 존재하는지 확인 후 없으면 폴더를 생성하고,
                is_recording = not is_recording
                session_id = time.strftime("%Y%m%d_%H%M%S")
                if not os.path.exists(os.path.join(OUTPUT_DIR, session_id)):
                    os.makedirs(os.path.join(OUTPUT_DIR, session_id))
            else:
                is_recording = not is_recording
                frame_count = 0

        if is_recording:
            file_name = f"frame_{frame_count:06d}.npz"
            file_path = os.path.join(OUTPUT_DIR, session_id, file_name)
            # np.savez_compressed(file_path, timestamp=timestamp, color=color, depth=depth)
            np.savez(file_path, timestamp=timestamp, color=color, depth=depth)
            frame_count += 1

        end_time = time.time()
        curr_fps = 1.0 / (end_time - start_time) if (end_time - start_time) > 0 else 0
        
        frame_times.append(curr_fps)
        if len(frame_times) > 15:
            frame_times.pop(0)
        avg_fps = sum(frame_times) / len(frame_times)

        color_view = color.copy()

        fps_text = f"FPS: {avg_fps:.1f}"
        cv2.putText(color_view, fps_text, (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if is_recording:
            cv2.circle(color_view, (30, 30), 10, (0, 0, 255), -1) # 빨간 불
            cv2.putText(color_view, f"REC | Frames: {frame_count}", (50, 40), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(color_view, "PAUSED (Press Space to REC)", (30, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # depth_view = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        # depth_color = cv2.applyColorMap(depth_view, cv2.COLORMAP_JET)

        # color_view = cv2.addWeighted(color_view, .6, depth_color, .4, 0, 0)

        cv2.imshow("img", color_view)
        # cv2.imshow("depth", depth_color)


    camera.stop()
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()
