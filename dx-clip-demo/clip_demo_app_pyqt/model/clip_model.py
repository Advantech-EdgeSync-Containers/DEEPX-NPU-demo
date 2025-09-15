from __future__ import annotations
from clip_demo_app_pyqt.model.sentence_model import SentenceModel, Sentence
from clip_demo_app_pyqt.model.video_model import VideoModel


class ClipModel(SentenceModel, VideoModel):
    def __init__(self, base_path: str, video_path_lists: list[list[str]], sentence_list: list[Sentence]):
        SentenceModel.__init__(self, sentence_list)
        VideoModel.__init__(self, base_path, video_path_lists)
