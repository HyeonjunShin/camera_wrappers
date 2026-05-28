import cv2
from pyk4a import PyK4APlayback
import zenoh

def main(file_path):    
    zh = zenoh.Zenoh()

    playback = PyK4APlayback(file_path)
    playback.open()

    while True:
        try:
            capture = playback.get_next_capture()
        except EOFError as e:
            print(f"End of file reached")
            playback.seek(0)
        
        color = capture.color
        depth = capture.depth
        if color is None or depth is None:
            continue

        color = cv2.imdecode(color, cv2.IMREAD_COLOR)
        timestamp = capture.depth_timestamp_usec

        print(f"Timestamp: {timestamp}, Color shape: {color.shape}, Depth shape: {depth.shape}")

        # Publish to Zenoh
        zh.put("camera1/color", color)
        zh.put("camera1/depth", depth)
        zh.put("camera1/timestamp", timestamp)

        # cv2.imshow("Color", color)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
            # break

if __name__ == "__main__":
    file_path = "./resource/robot_camera.mkv"
    main(file_path)