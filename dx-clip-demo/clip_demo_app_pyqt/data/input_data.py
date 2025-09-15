from __future__ import annotations
import json
import os

from overrides import overrides

from clip_demo_app_pyqt.common.singleton import Singleton


class InputData(Singleton):
    __current_file_dir = os.path.dirname(os.path.abspath(__file__))
    __default_path = None
    __data_path = None
    __default_sentence_score_min = None
    __default_sentence_score_max = None
    __default_sentence_score_threshold = None
    __sentence_list = None
    __video_path_lists = None

    @overrides
    def initialize(self, default_path="default_data.json", data_path="data.json", *args, **kwargs):
        self.__default_path = os.path.join(self.__current_file_dir, default_path)
        self.__data_path = os.path.join(self.__current_file_dir, data_path)
        from clip_demo_app_pyqt.model.sentence_model import Sentence
        self.__sentence_list: list[Sentence] = list()
        self.__video_path_lists: list = list()
        self.load_data()

    def get_sentence_list(self):
        return self.__sentence_list

    def get_video_path_lists(self):
        return self.__video_path_lists

    def get_default_sentence_score_min(self):
        return self.__default_sentence_score_min

    def get_default_sentence_score_max(self):
        return self.__default_sentence_score_max

    def get_default_sentence_score_threshold(self):
        return self.__default_sentence_score_threshold

    def load_data(self, force=False):
        """Load data from data.json if it exists; otherwise, load from default_data.json and save to data.json."""
        path = self.__data_path if os.path.exists(self.__data_path) and not force else self.__default_path
        with open(path, 'r') as file:
            try:
                data = json.load(file)
            except Exception:
                self.load_data(force=True)
                return

            self.__default_sentence_score_min = data.get("default_sentence_score_min", 0.0)
            self.__default_sentence_score_max = data.get("default_sentence_score_max", 1.0)
            self.__default_sentence_score_threshold = data.get("default_sentence_score_threshold", 0.5)
            self.__video_path_lists = data.get("video_path_lists", [])
            from clip_demo_app_pyqt.model.sentence_model import Sentence
            self.__sentence_list = [Sentence.from_dict(s) for s in data.get("sentence_list", [])]
        if path == self.__default_path:
            self.save_data()

    def save_data(self):
        """Save current data to data.json."""
        data = {
            "default_sentence_score_min": self.__default_sentence_score_min,
            "default_sentence_score_max": self.__default_sentence_score_max,
            "default_sentence_score_threshold": self.__default_sentence_score_threshold,
            "video_path_lists": self.__video_path_lists,
            "sentence_list": [s.to_dict() for s in self.__sentence_list]
        }
        with open(self.__data_path, 'w') as file:
            json.dump(data, file, indent=4)
