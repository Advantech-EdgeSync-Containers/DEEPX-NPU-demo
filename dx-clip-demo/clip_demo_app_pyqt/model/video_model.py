from __future__ import annotations
from clip_demo_app_pyqt.model.model import Model


class VideoModel(Model):
    def __init__(self, base_path: str, video_path_lists: list[list[str]]):
        Model.__init__(self)
        self.__base_path = base_path
        self.__video_path_lists = video_path_lists
        self.__num_channels = len(self.__video_path_lists)

    def get_num_channels(self) -> int:
        return self.__num_channels
