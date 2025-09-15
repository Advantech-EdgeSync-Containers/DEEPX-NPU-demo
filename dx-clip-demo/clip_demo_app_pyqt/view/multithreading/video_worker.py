from queue import Queue

from clip_demo_app_pyqt.common.base import Base
from clip_demo_app_pyqt.view.multithreading.video_consumer import VideoConsumer
from clip_demo_app_pyqt.view.multithreading.video_producer import VideoProducer

class WorkerQueue(Queue):
    def __init__(self, maxsize=None):
        super().__init__(maxsize)


class VideoWorker(Base):
    def __init__(self, channel_idx: int, video_producer: VideoProducer, video_consumer: VideoConsumer):
        super().__init__()
        self.__channel_idx = channel_idx
        self.__video_producer = video_producer
        self.__video_consumer = video_consumer

        from clip_demo_app_pyqt.common.config.ui_config import UIConfig
        self.__max_queue_size = UIConfig.consumer_queue_size
        self.__worker_queue = WorkerQueue(maxsize=self.__max_queue_size)

    def get_channel_idx(self)-> int:
        return self.__channel_idx

    def get_video_producer(self) -> VideoProducer:
        return self.__video_producer

    def get_video_consumer(self) -> VideoConsumer:
        return self.__video_consumer

    def push_queue(self, payload):
        # If the queue is full, remove the oldest image
        if self.__worker_queue.full():
            self.__worker_queue.get()  # Remove the oldest image

        # Add the new image to the queue
        self.__worker_queue.put(payload)

    def pop_queue(self):
        if not self.__worker_queue.empty():
            return self.__worker_queue.get()
        return None
