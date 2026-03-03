from kinect_wrapper.main import KinectCamera

def main():
    camera = KinectCamera()
    camera.start()
    print(camera.K)

    camera.stop()
    
if __name__ == "__main__":
    main()
