import logging
from abc import abstractmethod
import time

from PyQt5.QtCore import pyqtSignal, QObject


class VideoConsumer(QObject):
    __update_each_fps_signal = pyqtSignal(int, float, float)
    __update_overall_fps_signal = pyqtSignal()

    def __init__(self, channel_idx: int, video_source_changed_signal: pyqtSignal, video_fps_sync_mode):
        super().__init__()
        self.__running = True
        self.__pause_thread = False
        self.__video_fps_sync_mode = video_fps_sync_mode

        self._channel_idx = channel_idx

        self.__last_update_time_each_fps = 0  # Initialize the last update time
        self.__interval_update_time_each_fps = 0.3  # Set update interval to 0.3 seconds (adjust as needed)

        self.__last_update_time_overall_fps = 0  # Initialize the last update time
        self.__interval_update_time_overall_fps = 0.3  # Set update interval to 0.3 seconds (adjust as needed)

        video_source_changed_signal.connect(self.__video_source_changed)

    def process(self, channel_idx, frame, fps):
        logging.debug("VideoConsumer thread started, channel_id: " + str(self._channel_idx))
        try:
            if self.__running:
                if self.__pause_thread:
                    time.sleep(0.001)  # Introduce a short sleep to prevent tight looping
                    return

                if self.__video_fps_sync_mode:
                    time.sleep(1 / fps)

                self._process_impl(channel_idx, frame, fps)
        except Exception as ex:
            # traceback.print_exc()
            logging.error(f"Error in VideoConsumer run method: {ex}")
            pass

    def stop(self):
        self.__running = False
        self.__pause_thread = False  # Ensure thread is not stuck in pause

    def resume(self):
        self.__pause_thread = False

    def pause(self):
        self.__pause_thread = True

    def get_update_each_fps_signal(self):
        return self.__update_each_fps_signal

    def get_update_overall_fps_signal(self):
        return self.__update_overall_fps_signal

    def _update_overall_fps(self, channel_idx):
        if self._channel_idx != channel_idx:
            raise RuntimeError("channel index is not correct")

        current_update_time_fps = time.time()
        if current_update_time_fps - self.__last_update_time_overall_fps < self.__interval_update_time_overall_fps:
            return

        self.__update_overall_fps_signal.emit()

        self.__last_update_time_overall_fps = current_update_time_fps

    def _update_each_fps(self, channel_idx, dxnn_fps, sol_fps):
        if self._channel_idx != channel_idx:
            raise RuntimeError("channel index is not correct")

        current_update_time_fps = time.time()
        if current_update_time_fps - self.__last_update_time_each_fps < self.__interval_update_time_each_fps:
            return

        self.__update_each_fps_signal.emit(channel_idx, dxnn_fps, sol_fps)

        self.__last_update_time_each_fps = current_update_time_fps

    def __video_source_changed(self, channel_idx: int):
        if self._channel_idx != channel_idx:
            raise RuntimeError("channel index is not correct")

        self._cleanup(channel_idx)

    @abstractmethod
    def _process_impl(self, channel_idx, frame, fps):
        pass

    @abstractmethod
    def _cleanup(self, channel_idx):
        pass

