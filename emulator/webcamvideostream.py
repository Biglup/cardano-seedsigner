######################################################################
#  Webcam video stream for desktop emulator
#
#  Original author: @EnteroPositivo (Twitter, Gmail, GitHub)
#  Source: https://github.com/enteropositivo/seedsigner-emulator
#
#  Adapted for Cardano SeedSigner project
######################################################################

from threading import Thread
import time

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("Warning: OpenCV not installed. Camera features will be disabled.")


class WebcamVideoStream:
    def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
        self.frame = None
        self.should_stop = False
        self.is_stopped = True

        if not HAS_OPENCV:
            self.camera = None
            return

        # Initialize the camera
        self.camera = cv2.VideoCapture(0)
        self.set_resolution(resolution)

    def start(self):
        if not HAS_OPENCV or self.camera is None:
            return self

        # Start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        self.is_stopped = False
        return self

    def hasCamera(self):
        if not HAS_OPENCV or self.camera is None:
            return False
        return self.camera.isOpened()

    def update(self):
        if not self.hasCamera():
            self.is_stopped = True
            self.should_stop = False
            return

        # Keep looping infinitely until the thread is stopped
        while not self.should_stop:
            ret, stream = self.camera.read()
            if ret:
                stream = cv2.resize(stream, (240, 240))
                stream = cv2.cvtColor(stream, cv2.COLOR_BGR2RGB)
                self.frame = stream
            time.sleep(0.05)

        self.is_stopped = True
        self.should_stop = False

    def read(self):
        return self.frame

    @staticmethod
    def single_frame():
        if not HAS_OPENCV:
            return None
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    def stop(self):
        # Indicate that the thread should be stopped
        self.should_stop = True

        # Block in this thread until stopped
        while not self.is_stopped:
            time.sleep(0.01)

    def set_resolution(self, resolution):
        if self.camera:
            self.camera.set(3, resolution[0])
            self.camera.set(4, resolution[1])
