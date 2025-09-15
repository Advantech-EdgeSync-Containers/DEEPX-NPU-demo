from __future__ import annotations
from PyQt5.QtCore import pyqtSignal

from clip_demo_app_pyqt.model.clip_model import SentenceModel
from clip_demo_app_pyqt.model.sentence_model import Sentence
from clip_demo_app_pyqt.viewmodel.view_model import ViewModel


class SentenceViewModel(ViewModel):
    _sentence_list_updated_signal = pyqtSignal()

    def __init__(self, sentence_model: SentenceModel):
        super().__init__(sentence_model)
        self.__sentence_model = sentence_model
        # print("SentenceViewModel : " + str(dir(self)))

    def get_sentence_list_updated_signal(self):
        return self._sentence_list_updated_signal

    def insert_sentence(self, sentence, score_min, score_max, score_threshold,
                        alarm, alarm_title, alarm_position, alarm_color,
                        media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position):
        self.__sentence_model.insert_sentence(sentence, score_min, score_max, score_threshold,
                                              alarm, alarm_title, alarm_position, alarm_color,
                                              media_alarm, media_alarm_title, media_alarm_media_path,
                                              media_alarm_position)
        self._sentence_list_updated_signal.emit()

    def update_sentence(self, sentence, score_min, score_max, score_threshold,
                        alarm, alarm_title, alarm_position, alarm_color,
                        media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position, index):
        self.__sentence_model.update_sentence(sentence, score_min, score_max, score_threshold,
                                              alarm, alarm_title, alarm_position, alarm_color,
                                              media_alarm, media_alarm_title, media_alarm_media_path,
                                              media_alarm_position, index)
        self._sentence_list_updated_signal.emit()

    def pop_sentence(self, index=None):
        self.__sentence_model.pop_sentence(index)
        self._sentence_list_updated_signal.emit()

    def toggle_sentence(self, index):
        self.__sentence_model.toggle_sentence(index)
        self._sentence_list_updated_signal.emit()

    def toggle_alarm(self, index):
        self.__sentence_model.toggle_alarm(index)
        self._sentence_list_updated_signal.emit()

    def toggle_media_alarm(self, index):
        self.__sentence_model.toggle_media_alarm(index)
        self._sentence_list_updated_signal.emit()

    def reset_sentence(self):
        self.__sentence_model.reset_sentence()
        self._sentence_list_updated_signal.emit()

    def clear_sentence(self):
        self.__sentence_model.clear_sentence()
        self._sentence_list_updated_signal.emit()

    def get_sentence_list(self) -> list[Sentence]:
        return self.__sentence_model.get_sentence_list()

    def get_sentence_vector_list(self) -> list:
        return self.__sentence_model.get_sentence_vector_list()
