import logging
import os
import threading
import time
import sys
import subprocess
from typing import List, Tuple

import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QImage

# print(cv2.getBuildInformation())

# Supported video file extensions
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']

def is_vaapi_available():
    try:
        result = subprocess.run(
            ["gst-inspect-1.0", "vaapidecodebin"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

use_vaapi = False
if os.name != "nt":
    if is_vaapi_available():
        use_vaapi = True
        sys.path.insert(0, "/usr/lib/python3/dist-packages")
        print("VA-API detected, path added.")

class VideoProducer(QObject):
    __scaled_video_frame_updated_signal = pyqtSignal(int, QImage)
    __origin_video_frame_updated_signal = pyqtSignal(int, np.ndarray, int)
    __video_source_changed_signal = pyqtSignal(int)

    def __init__(self, channel_idx: int, base_path: str, video_path_list: List[str], video_size: Tuple,
                 video_fps_sync_mode: int, video_frame_skip_interval: int, sentence_list_updated_signal: pyqtSignal):
        super().__init__()
        self.__running = True
        self.__pause_thread = False
        self.__video_fps_sync_mode = video_fps_sync_mode

        self.__change_video_lock = threading.Lock()

        self.__frame_count = 0
        self.__video_frame_skip_interval = video_frame_skip_interval
        
        self.__is_rtsp_source = False
        self.__is_camera_source = False

        sentence_list_updated_signal.connect(self.__change_video)

        self._channel_idx = channel_idx

        self.__current_index = 0
        if video_path_list[0] == "/dev/video0":
            self.__base_path = ""
            self.video_path_list = ["/dev/video0"]
            self.__video_path_current = os.path.join(self.video_path_list[self.__current_index])
            self.__is_camera_source = True
        else:
            self.__base_path = base_path
            self.video_path_list = video_path_list

            video_path = self.video_path_list[self.__current_index]
            if video_path.startswith("rtsp"):
                self.__is_rtsp_source = True
                self.__video_path_current = f"{video_path}"
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            else:
                self.__is_rtsp_source = False
                # Find video file with supported extension
                self.__video_path_current = self.__find_video_file(video_path)

            self.__is_camera_source = False

        self.__video_capture = cv2.VideoCapture()
        self.__video_size = video_size
        self.__video_label_size = video_size

        if use_vaapi:
            self.__video_capture = cv2.VideoCapture(self.__generate_gst_pipeline(self.__video_path_current),
                                                    cv2.CAP_GSTREAMER)
        elif self.__is_rtsp_source:
            if self.__rtsp_url_test(self.__video_path_current):
                self.__video_capture = cv2.VideoCapture(self.__video_path_current, cv2.CAP_FFMPEG)
            else:
                self.__change_video(True)
        else:
            self.__video_capture = cv2.VideoCapture(self.__video_path_current)

        if not self.__video_capture.isOpened():
            logging.error("Error: Could not open video.")
            self.__video_fps = 30       # default video fps value
        else:
            self.__video_fps = int(round(self.__video_capture.get(cv2.CAP_PROP_FPS), 0))
            logging.debug("channel_idx:" + str(self._channel_idx) + f"FPS: {self.__video_fps}")

        self.__current_video_frame = np.zeros((self.__video_label_size[1], self.__video_label_size[0], 3), dtype=np.uint8)
    
    def __find_video_file(self, video_name: str) -> str:
        """
        Find video file with supported extension in the base path
        
        Args:
            video_name: Name of the video file without extension
            
        Returns:
            Full path to the video file with extension
        """
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            video_path = os.path.join(self.__base_path, video_name + ext)
            if os.path.exists(video_path):
                logging.debug(f"Found video file: {video_path}")
                return video_path
        
        # If no file found with supported extension, try with .mp4 as fallback
        fallback_path = os.path.join(self.__base_path, video_name + ".mp4")
        logging.warning(f"No video file found with supported extensions for '{video_name}'. Using fallback: {fallback_path}")
        return fallback_path

    def __rtsp_url_test(self, rtsp_url_path):
        cap = cv2.VideoCapture(rtsp_url_path)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # timeout (OpenCV >=4.5)
        if cap.isOpened():
            frame = None
            lock = threading.Lock()
            stop_reader = False
            def reader():
                nonlocal frame, stop_reader
                while not stop_reader:
                    ret = False
                    try:
                        ret, new_frame = cap.read()
                    except Exception as e:
                        pass
                    with lock:
                        if ret:
                            frame = new_frame
            reader_thread = threading.Thread(target=reader, daemon=True)
            reader_thread.start()
            
            while True:
                start_time = time.time()
                while time.time() - start_time < 5:
                    with lock:
                        if frame is not None:
                            break
                    time.sleep(1)
                break

            stop_reader = True
            
            if frame is None:
                print("[DXAPP][Notify] No frame received within 5 seconds. Proceeding to the next stream.")
                try:
                    cap.release()
                except Exception as e:
                    pass
                return False
            else:
                reader_thread.join()
                cap.release()
                return True

    def __generate_gst_pipeline(self, video_path):
        # width = self.__video_label_size[0]
        # height = self.__video_label_size[1]

        if self.__is_camera_source:
            gst_pipeline = (
                f"v4l2src device={video_path} ! "
                f"videoconvert ! appsink"
            )
        else:
            gst_pipeline = (
                f"filesrc location={video_path} ! "
                f"queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
                f"qtdemux ! vaapidecodebin ! "
                # f"qtdemux ! h264parse ! avdec_h264 ! "        // use cpu only
                f"queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
                f"videoconvert qos=false ! "
                # Temporary code: Commented out hardware-accelerated resize. Reason: Malfunction in PyQt (interference between channels).
                # f"videoscale method=0 add-borders=false qos=false ! "
                # f"video/x-raw,width={width},height={height},pixel-aspect-ratio=1/1 ! "
                f"queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
                f"appsink"
            )

        logging.debug(f"Using GStreamer pipeline: {gst_pipeline}")
        return gst_pipeline

    def is_camera_source(self):
        return self.__is_camera_source

    def set_video_label_size(self, size: Tuple[int, int]):
        self.__video_label_size = size
    
    def capture_frame(self):
        
        logging.debug("VideoProducer thread started, channel_id: " + str(self._channel_idx))

        if self.__running is False or self.__pause_thread:
            time.sleep(0.001)  # Adding a small sleep to avoid busy-waiting
            return None

        if self.__video_fps_sync_mode:
            # 1: 1sec, 0.75: Adjustment ratio considering NPU inference execution time
            time.sleep((1 / self.__video_fps) * 0.75)

        self.__frame_count += 1
        if self.__video_frame_skip_interval > 0:
            if self.__frame_count % self.__video_frame_skip_interval == 0:
                self.__frame_count = 0
                return None

        self.__update_current_video_frame()
        if not self.ret:
            self.__change_video(True)
        else:
            self.__current_video_frame = self.frame
        # Frame processing and signal transmission
        rgb_image = cv2.cvtColor(self.__current_video_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        if use_vaapi:
            # Temporary code: Commented out hardware-accelerated resize. Reason: Malfunction in PyQt (interference between channels).
            # The image has already been resized at the GStreamer level, so resizing is skipped.
            # scaled_image = convert_to_qt_format

            # sw resize
            scaled_image = convert_to_qt_format.scaled(self.__video_label_size[0], self.__video_label_size[1],
                                                       Qt.KeepAspectRatio)
        else:
            # sw resize
            scaled_image = convert_to_qt_format.scaled(self.__video_label_size[0], self.__video_label_size[1],
                                                       Qt.KeepAspectRatio)

        # Send the scaled QImage to the main thread
        self.__scaled_video_frame_updated_signal.emit(self._channel_idx, scaled_image)

        # Send the original QImage to the video consumer thread
        return [self._channel_idx, self.__current_video_frame, self.__video_fps]

    def __update_current_video_frame(self):
        with self.__change_video_lock:
            self.ret, self.frame = self.__video_capture.read()

    def __change_video(self, is_next=False):
        camera_mode = False
        if self.video_path_list[0] == '/dev/video0':# or self.video_path_list[self.__current_index].startswith("rtsp"):
            camera_mode = True
            is_next = False

        if is_next:
            self.__current_index = 0 if self.__current_index + 1 == len(self.video_path_list) else self.__current_index + 1
            if self.video_path_list[self.__current_index].startswith("rtsp"):
                self.__current_index = self.__current_index + 1

        if camera_mode:
            self.__video_path_current = os.path.join(self.video_path_list[self.__current_index])
        else:
            # Find video file with supported extension
            self.__video_path_current = self.__find_video_file(self.video_path_list[self.__current_index])
            
        with self.__change_video_lock:
            if self.__video_capture.isOpened():
                self.__video_capture.release()
            if use_vaapi:
                self.__video_capture = cv2.VideoCapture(self.__generate_gst_pipeline(self.__video_path_current),
                                                        cv2.CAP_GSTREAMER)
            else:
                self.__video_capture = cv2.VideoCapture(self.__video_path_current)

            if not self.__video_capture.isOpened():
                logging.debug("Failed to open video capture")
            else:
                ret, frame = self.__video_capture.read()

            if ret:
                self.__video_source_changed_signal.emit(self._channel_idx)
                self.__current_video_frame = frame
            else:
                logging.debug("Failed to read video frame: " + str(ret))

    def stop(self):
        self.__running = False
        self.__pause_thread = False  # Ensure thread is not stuck in pause
        logging.debug(f"VideoProducer {self._channel_idx} stopping...")
        with self.__change_video_lock:
            if self.__video_capture.isOpened():
                self.__video_capture.release()

    def resume(self):
        self.__pause_thread = False

    def pause(self):
        self.__pause_thread = True
        timer = threading.Timer(0.5, self.draw_black_preview)
        timer.start()

    def draw_black_preview(self):
        # for draw black preview image
        self.__current_video_frame = np.zeros((self.__video_label_size[1], self.__video_label_size[0], 3),
                                              dtype=np.uint8)
        rgb_image = cv2.cvtColor(self.__current_video_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_image = convert_to_qt_format.scaled(self.__video_label_size[0], self.__video_label_size[1],
                                                   Qt.KeepAspectRatio)
        self.__scaled_video_frame_updated_signal.emit(self._channel_idx, scaled_image)

    def get_video_frame_updated_signal(self) -> [pyqtSignal]:
        return [self.__scaled_video_frame_updated_signal, self.__video_source_changed_signal]
