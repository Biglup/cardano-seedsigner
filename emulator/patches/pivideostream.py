######################################################################
#  Patched pivideostream.py for desktop emulator
#
#  Replaces PiCamera with webcam stream
#  Emulator by: @EnteroPositivo (Twitter, Gmail, GitHub)
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


class PiVideoStream:
    """Replacement for Pi camera video stream using webcam."""

    def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
        self.frame = None
        self.should_stop = False
        self.is_stopped = True

        if not HAS_OPENCV:
            self.camera = None
            return

        # Initialize the camera
        self.camera = cv2.VideoCapture(0)
        if self.camera.isOpened():
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    def start(self):
        if not HAS_OPENCV or self.camera is None or not self.camera.isOpened():
            return self

        # Start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        self.is_stopped = False
        return self

    def update(self):
        if not HAS_OPENCV or self.camera is None:
            self.is_stopped = True
            return

        # Keep looping infinitely until the thread is stopped
        while not self.should_stop:
            ret, frame = self.camera.read()
            if ret:
                # Resize to 240x240 and convert color
                frame = cv2.resize(frame, (240, 240))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frame = frame
            time.sleep(0.03)

        self.is_stopped = True
        self.should_stop = False

    def read(self):
        return self.frame

    def stop(self):
        # Indicate that the thread should be stopped
        self.should_stop = True

        # Block in this thread until stopped
        while not self.is_stopped:
            time.sleep(0.01)
