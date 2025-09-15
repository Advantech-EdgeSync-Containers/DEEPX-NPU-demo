from __future__ import annotations
import copy
import threading

from pyqttoast import ToastPosition

from clip_demo_app_pyqt.data.input_data import InputData
from clip_demo_app_pyqt.model.model import Model


class VideoAlarmInfo:
    def __init__(self, enabled: bool = False, title: str = "ALARM", video_path: str = "",
                 position: int = ToastPosition.CENTER.value):
        self.__enabled = enabled
        self.__title = title
        self.__media_path = video_path
        self.__position = position

    def setAlarm(self, value: bool):
        self.__enabled = value

    def setTitle(self, title: str):
        self.__title = title

    def setVideoPath(self, video_path: str):
        self.__media_path = video_path

    def setPosition(self, position):
        self.__position = position

    def getAlarm(self) -> bool:
        return self.__enabled

    def getTitle(self) -> str:
        return self.__title

    def getMediaPath(self) -> str:
        return self.__media_path

    def getPosition(self) -> int:
        return self.__position

    def to_dict(self):
        return {
            "enabled": self.__enabled,
            "title": self.__title,
            "media_path": self.__media_path,
            "position": self.__position,
        }


class AlarmInfo:
    def __init__(self, enabled: bool = False, title: str = "ALARM", position: int = ToastPosition.BOTTOM_MIDDLE.value,
                 color: str = "#E8B849"):
        self.__enabled = enabled
        self.__title = title
        self.__position = position
        self.__color = color

    def setAlarm(self, value: bool):
        self.__enabled = value

    def setTitle(self, title: str):
        self.__title = title

    def setPosition(self, position):
        self.__position = position

    def setColor(self, color):
        self.__color = color

    def getAlarm(self) -> bool:
        return self.__enabled

    def getTitle(self) -> str:
        return self.__title

    def getPosition(self) -> int:
        return self.__position

    def getColor(self) -> str:
        return self.__color

    def to_dict(self):
        return {
            "enabled": self.__enabled,
            "title": self.__title,
            "position": self.__position,
            "color": self.__color
        }


class ServerEventInfo:
    def __init__(self, enabled: bool = False, event_type: str = "UNDEFINED", source: str = "#E8B849"):
        self.__enabled = enabled
        self.__event_type = event_type
        self.__source = source

    def setEnableStatus(self, enabled: bool):
        self.__enabled = enabled

    def setEventType(self, event_type: str):
        self.__event_type = event_type

    def setSource(self, source: str):
        self.__source = source

    def getEnableStatus(self) -> bool:
        return self.__enabled

    def getEventType(self) -> str:
        return self.__event_type

    def getSource(self) -> int:
        return self.__source

    def to_dict(self):
        return {
            "enabled": self.__enabled,
            "event_type": self.__event_type,
            "source": self.__source
        }


class Sentence:
    __disabled = False

    def __init__(self, text: str, score_min: float, score_max: float, score_threshold: float,
                 alarm: bool, alarm_title: str, alarm_position: int, alarm_color: str,
                 media_alarm: bool, media_alarm_title: str, media_alarm_media_path: str, media_alarm_position: int):
        self.__text = text
        self.__score_min = score_min
        self.__score_max = score_max
        self.__score_threshold = score_threshold
        self.__alarm_info = AlarmInfo(alarm, alarm_title, alarm_position, alarm_color)
        self.__media_alarm_info = VideoAlarmInfo(media_alarm, media_alarm_title, media_alarm_media_path,
                                                 media_alarm_position)

    def get_text(self) -> str:
        return self.__text

    def get_score_min(self) -> float:
        return self.__score_min

    def get_score_max(self) -> float:
        return self.__score_max

    def get_score_threshold(self) -> float:
        return self.__score_threshold

    def set_disabled(self, val: bool):
        self.__disabled = val

    def set_alarm(self, val: bool):
        self.__alarm_info.setAlarm(val)

    def get_disabled(self):
        return self.__disabled

    def get_alarm(self):
        return self.__alarm_info.getAlarm()

    def get_alarm_title(self):
        return self.__alarm_info.getTitle()

    def get_alarm_color(self):
        return self.__alarm_info.getColor()

    def get_alarm_position(self):
        return self.__alarm_info.getPosition()

    def set_media_alarm(self, val: bool):
        self.__media_alarm_info.setAlarm(val)

    def get_media_alarm(self):
        return self.__media_alarm_info.getAlarm()

    def get_media_alarm_title(self):
        return self.__media_alarm_info.getTitle()

    def get_media_alarm_media_path(self):
        return self.__media_alarm_info.getMediaPath()

    def get_media_alarm_position(self):
        return self.__media_alarm_info.getPosition()

    def to_dict(self):
        return {
            "text": self.__text,
            "min_score": self.__score_min,
            "max_score": self.__score_max,
            "threshold": self.__score_threshold,
            "disabled": self.__disabled,
            "alarm_info": self.__alarm_info.to_dict(),
            "media_alarm_info": self.__media_alarm_info.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict):
        alarm_info_dict = data.get("alarm_info", AlarmInfo().to_dict())
        media_alarm_info_dict = data.get("media_alarm_info", VideoAlarmInfo().to_dict())
        instance = cls(
            text=data["text"],
            score_min=data["min_score"],
            score_max=data["max_score"],
            score_threshold=data["threshold"],
            alarm=alarm_info_dict["enabled"],
            alarm_title=alarm_info_dict["title"],
            alarm_position=alarm_info_dict["position"],
            alarm_color=alarm_info_dict["color"],
            media_alarm=media_alarm_info_dict["enabled"],
            media_alarm_title=media_alarm_info_dict["title"],
            media_alarm_media_path=media_alarm_info_dict["media_path"],
            media_alarm_position=media_alarm_info_dict["position"],
        )
        instance.set_disabled(data.get("disabled", False))
        return instance


class SentenceOutput:
    def __init__(self, sentence: Sentence, score: float):
        self.__sentence = sentence
        self.__score = score
        self.__percentage = int(sentence.get_score_min() / sentence.get_score_max() * score)

        score_min = sentence.get_score_min()
        score_max = sentence.get_score_max()

        if score < score_min:
            percentage = 0
        elif score > score_max:
            percentage = 100
        else:
            percentage = int((score - score_min) / (score_max - score_min) * 100)

        self.__percentage = percentage

    def get_sentence_text(self) -> str:
        return self.__sentence.get_text()

    def get_score(self) -> float:
        return self.__score

    def get_percentage(self) -> int:
        return self.__percentage

    def get_alarm(self) -> bool:
        return self.__sentence.get_alarm()

    def get_alarm_title(self) -> str:
        return self.__sentence.get_alarm_title()

    def get_alarm_position(self) -> int:
        return self.__sentence.get_alarm_position()

    def get_alarm_color(self) -> str:
        return self.__sentence.get_alarm_color()

    def get_media_alarm(self) -> bool:
        return self.__sentence.get_media_alarm()

    def get_media_alarm_title(self) -> str:
        return self.__sentence.get_media_alarm_title()

    def get_media_alarm_media_path(self) -> str:
        return self.__sentence.get_media_alarm_media_path()

    def get_media_alarm_position(self) -> int:
        return self.__sentence.get_media_alarm_position()

import sys
import time

import torch
from clip.simple_tokenizer import SimpleTokenizer as ClipTokenizer
from tqdm import tqdm
from clip_demo_app_pyqt.lib.clip.dx_text_encoder import ONNXModel
from clip_demo_app_pyqt.common.parser.parser_util import ParserUtil

class TextVectorUtil:
    SPECIAL_TOKEN = {
        "CLS_TOKEN": "<|startoftext|>",
        "SEP_TOKEN": "<|endoftext|>",
        "MASK_TOKEN": "[MASK]",
        "UNK_TOKEN": "[UNK]",
        "PAD_TOKEN": "[PAD]",
    }
    MAX_WORDS = 32
    DEVICE = ""
    if torch.cuda.is_available():
        DEVICE = "cuda"
    elif sys.platform.startswith("darwin"):
        DEVICE = "mps"
    else:
        DEVICE = "cpu"

    model_load_time_s = time.perf_counter_ns()

    token_embedder = ONNXModel(
        model_path=ParserUtil.get_args().token_embedder_onnx
    )
    text_encoder = ONNXModel(
        model_path=ParserUtil.get_args().text_encoder_onnx
    )

    model_load_time_e = time.perf_counter_ns()
    print("[TIME] Model Load : {} ns".format(model_load_time_e - model_load_time_s))

    @classmethod
    def get_text_vector_list(cls, text_list: list[str]) -> list:
        ret = []
        for i in tqdm(range(len(text_list))):
            text = text_list[i]
            text_vectors = cls.get_text_vector(text)
            ret.append(text_vectors)
        return ret

    @classmethod
    def get_text_vector(cls, text: str) -> torch.Tensor:
        text = text if len(text.split(" ")) < cls.MAX_WORDS - 1 else str.join(text.split(" ")[:cls.MAX_WORDS - 2])
        text = cls.SPECIAL_TOKEN["CLS_TOKEN"] + " " + text + " " + cls.SPECIAL_TOKEN["SEP_TOKEN"]
        token_ids = ClipTokenizer().encode(text)
        token_ids_mask = [1] * len(token_ids) + [0] * (
                cls.MAX_WORDS - len(token_ids)
        )
        token_ids = token_ids + [0] * (
                cls.MAX_WORDS - len(token_ids)
        )
        token_ids_mask = torch.tensor([token_ids_mask]).to(cls.DEVICE, dtype=torch.float32)
        token_ids = torch.tensor([token_ids]).to(cls.DEVICE)
        text_embedding = cls.token_embedder(token_ids)
        text_vectors = cls.text_encoder([text_embedding, token_ids_mask])
        return text_vectors


class SentenceModel(Model):
    def __init__(self, sentence_list: list[Sentence]) -> None:
        Model.__init__(self)
        self.__sentence_lock = threading.Lock()

        self.__sentence_list: list[Sentence] = sentence_list
        self.__sentence_vector_list: list = TextVectorUtil.get_text_vector_list(
            [sentence.get_text() for sentence in self.__sentence_list])

    def insert_sentence(self, text_input, score_min, score_max, score_threshold,
                        alarm, alarm_title, alarm_position, alarm_color, media_alarm, media_alarm_title,
                        media_alarm_media_path, media_alarm_position, index=0) -> None:
        self.insert_sentence_obj(
            Sentence(text_input, score_min, score_max, score_threshold, alarm, alarm_title, alarm_position, alarm_color,
                     media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position), index)

    def insert_sentence_obj(self, sentence: Sentence, index=0) -> None:
        with self.__sentence_lock:
            self.__sentence_list.insert(index, sentence)
            self.__sentence_vector_list.insert(index, TextVectorUtil.get_text_vector(sentence.get_text()))
            InputData().save_data()

    def pop_sentence(self, index=None) -> Sentence:
        with self.__sentence_lock:
            if index is None:
                index = -1
            self.__sentence_vector_list.pop(index)
            sentence = self.__sentence_list.pop(index)
            InputData().save_data()
            return sentence

    def toggle_sentence(self, index) -> None:
        sentence = self.pop_sentence(index)
        sentence.set_disabled(not sentence.get_disabled())
        InputData().save_data()
        self.insert_sentence_obj(sentence, index)

    def toggle_alarm(self, index) -> None:
        sentence = self.pop_sentence(index)
        sentence.set_alarm(not sentence.get_alarm())
        InputData().save_data()
        self.insert_sentence_obj(sentence, index)

    def toggle_media_alarm(self, index) -> None:
        sentence = self.pop_sentence(index)
        sentence.set_media_alarm(not sentence.get_media_alarm())
        InputData().save_data()
        self.insert_sentence_obj(sentence, index)

    def update_sentence(self, text_input, score_min, score_max, score_threshold,
                        alarm, alarm_title, alarm_position, alarm_color, media_alarm, media_alarm_title,
                        media_alarm_media_path, media_alarm_position, index) -> None:
        self.pop_sentence(index)
        self.insert_sentence(text_input, score_min, score_max, score_threshold,
                             alarm, alarm_title, alarm_position, alarm_color,
                             media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position, index)

    def reset_sentence(self) -> None:
        with self.__sentence_lock:
            input_data = InputData()
            input_data.load_data(force=True)
            self.__sentence_list: list[Sentence] = input_data.get_sentence_list()
            self.__sentence_vector_list: list = TextVectorUtil.get_text_vector_list(
                [sentence.get_text() for sentence in self.__sentence_list])

    def clear_sentence(self) -> None:
        with self.__sentence_lock:
            self.__sentence_list.clear()
            self.__sentence_vector_list.clear()
            InputData().save_data()

    def get_sentence_list(self) -> list[Sentence]:
        with self.__sentence_lock:
            return copy.deepcopy(self.__sentence_list)

    def get_sentence_vector_list(self) -> list[torch.Tensor]:
        with self.__sentence_lock:
            return copy.deepcopy(self.__sentence_vector_list)
