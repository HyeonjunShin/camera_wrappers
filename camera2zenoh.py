from camera_devices.kinect_wrapper import KinectCamera
import zenoh
import cv2

def main():    
    camera = KinectCamera()
    camera.start()

    while True:
        capture = camera.get_frame()
        if capture is None:
            continue
        
        color = capture.get_color()
        

        # print(capture)


        # color = capture.color
        # depth = capture.depth
        # if color is None or depth is None:
        #     continue

        # color = cv2.imdecode(color, cv2.IMREAD_COLOR)
        # timestamp = capture.depth_timestamp_usec

        # print(f"Timestamp: {timestamp}, Color shape: {color.shape}, Depth shape: {depth.shape}")

        # # Publish to Zenoh
        # zh.put("camera1/color", color)
        # zh.put("camera1/depth", depth)
        # zh.put("camera1/timestamp", timestamp)

        cv2.imshow("Color", color)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

if __name__ == "__main__":
    main()