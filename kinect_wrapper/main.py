from pyk4a import PyK4A, Config, ColorResolution, DepthMode, FPS, ImageFormat, CalibrationType, ColorControlCommand, ColorControlMode

class KinectCamera:
    def __init__(self):
        self.k4a = PyK4A(
            Config(
                color_resolution=ColorResolution.RES_1080P,
                color_format=ImageFormat.COLOR_BGRA32,
                depth_mode=DepthMode.NFOV_UNBINNED,
                synchronized_images_only=True,
                camera_fps=FPS.FPS_30,
            )
        )

        self.width = 1920
        self.height = 1080

    def start(self):
        try:
            self.k4a.start()
            print("Strat the Kinect camera.")
        except Exception as e:
            print(f"Error: {e}")
            return
        
        # self.k4a._set_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE, 16670, ColorControlMode.MANUAL)
        self.k4a._set_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE, 8330, ColorControlMode.MANUAL)
        self.k4a._set_color_control(ColorControlCommand.WHITEBALANCE, 4500, ColorControlMode.MANUAL)
        
        calibration = self.k4a.calibration
        self.K = calibration.get_camera_matrix(CalibrationType.COLOR)
        self.D = calibration.get_distortion_coefficients(CalibrationType.COLOR)
        # calibration.get_extrinsic_parameters(CalibrationType.DEPTH, CalibrationType.COLOR)

        # calibration.color_resolution


        # self.new_mtx, roi = cv2.getOptimalNewCameraMatrix(self.K, self.D, (self.width, self.height), 0, (self.width, self.height))
        # self.mapx, self.mapy = cv2.initUndistortRectifyMap(self.K, self.D, None, self.new_mtx, (self.width, self.height), cv2.CV_32FC1)

        for target in ColorControlCommand:
            print(target, self.k4a._get_color_control(target))

    def getExposure(self):
        return self.k4a._get_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE)[0]
    def setExposure(self, value):
        print(self.getExposure())
        return self.k4a._set_color_control(ColorControlCommand.EXPOSURE_TIME_ABSOLUTE, value, ColorControlMode.MANUAL)

    def getBrightness(self):
        return self.k4a._get_color_control(ColorControlCommand.BRIGHTNESS)[0]
    def setBrightness(self, value):
        print(self.getBrightness())
        return self.k4a._set_color_control(ColorControlCommand.BRIGHTNESS, value, ColorControlMode.MANUAL)

    def getContrast(self):
        return self.k4a._get_color_control(ColorControlCommand.CONTRAST)[0]
    def setContrast(self, value):
        print(self.getContrast())
        return self.k4a._set_color_control(ColorControlCommand.CONTRAST, value, ColorControlMode.MANUAL)
    
    def getSaturation(self):
        return self.k4a._get_color_control(ColorControlCommand.SATURATION)[0]
    def setSaturation(self, value):
        print(self.getSaturation())
        return self.k4a._set_color_control(ColorControlCommand.SATURATION, value, ColorControlMode.MANUAL)
        
    def getWhiteBalance(self):
        return self.k4a._get_color_control(ColorControlCommand.WHITEBALANCE)[0]
    def setWhiteBalance(self, value):
        print(self.getWhiteBalance())
        return self.k4a._set_color_control(ColorControlCommand.WHITEBALANCE, value, ColorControlMode.MANUAL)
            
    def getSharpness(self):
        return self.k4a._get_color_control(ColorControlCommand.SHARPNESS)[0]
    def setSharpness(self, value):
        print(self.getSharpness())
        return self.k4a._set_color_control(ColorControlCommand.SHARPNESS, value, ColorControlMode.MANUAL)
    
    def getBlackLightCompensation(self):
        return self.k4a._get_color_control(ColorControlCommand.BACKLIGHT_COMPENSATION)[0]
    def setBlackLightCompensation(self, value):
        print(self.getBlackLightCompensation())
        return self.k4a._set_color_control(ColorControlCommand.BACKLIGHT_COMPENSATION, value, ColorControlMode.MANUAL)
    
    def getPowerLineFrequency(self):
        return self.k4a._get_color_control(ColorControlCommand.POWERLINE_FREQUENCY)[0]
    def setPowerLineFrequency(self, value):
        print(self.getPowerLineFrequency())
        return self.k4a._set_color_control(ColorControlCommand.POWERLINE_FREQUENCY, value, ColorControlMode.MANUAL)
    
    def getGain(self):
        return self.k4a._get_color_control(ColorControlCommand.GAIN)[0]
    def setGain(self, value):
        print(self.getGain())
        return self.k4a._set_color_control(ColorControlCommand.GAIN, value, ColorControlMode.MANUAL)

    def stop(self):
        self.k4a.stop()
        print("Stop the Kinect camera.")
    
    def getFrame(self):
        capture = self.k4a.get_capture()

        color = capture.color
        depth = capture.transformed_depth
        if color is None or depth is None:
            return None
        timestamp_image = capture.color_timestamp_usec
        
        color = cv2.cvtColor(color, cv2.COLOR_BGRA2BGR)
        # image = cv2.remap(image, self.mapx, self.mapy, cv2.INTER_LINEAR)

        # depth = cv2.remap(depth, self.mapx, self.mapy, cv2.INTER_LINEAR)

        # depth = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        # depth = cv2.applyColorMap(depth, cv2.COLORMAP_JET)

        # alpha = 0.5  # 원본 컬러 이미지의 불투명도 (60%)
        # beta = 0.5  # Depth 맵의 불투명도 (40%)
        
        # overlay_result = cv2.addWeighted(
            # frame, alpha, 
            # depth, beta, 
            # 0)
        # cv2.imshow("depth", overlay_result)
        return (color, depth, timestamp_image)
    
    def getUndistorted(self, color):
        color = cv2.remap(color, self.mapx, self.mapy, cv2.INTER_LINEAR)
        return color