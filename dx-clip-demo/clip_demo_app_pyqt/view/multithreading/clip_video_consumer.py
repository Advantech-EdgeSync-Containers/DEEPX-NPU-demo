from __future__ import annotations
import logging
import time
# import traceback

import numpy as np
import torch
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize
from PIL import Image
from PyQt5.QtCore import pyqtSignal
from overrides import overrides

from clip_demo_app_pyqt.common.parser.parser_util import ParserUtil
from clip_demo_app_pyqt.common.util.peekable_queue import PeekableQueue
from clip_demo_app_pyqt.lib.clip.dx_video_encoder import DXVideoEncoder
from clip_demo_app_pyqt.model.sentence_model import Sentence, SentenceOutput
from clip_demo_app_pyqt.viewmodel.clip_view_model import ClipViewModel
from clip_demo_app_pyqt.view.multithreading.video_consumer import VideoConsumer


class ClipVideoConsumer(VideoConsumer):
    __dxnn_video_encoder = DXVideoEncoder(ParserUtil.get_args().video_encoder_dxnn)

    __clear_sentence_output_signal = pyqtSignal(int)
    __update_sentence_output_signal = pyqtSignal(int, str, int, float, bool, str, int, str, bool, str, str, int)

    def __init__(self, channel_idx: int, number_of_alarms: list,
                 video_source_changed_signal: pyqtSignal,
                 sentence_list_update_signal: pyqtSignal, num_of_inference_per_sec: int,
                 max_np_array_similarity_queue: int, consumer_video_fps_sync_mode: bool, inference_engine_async_mode:bool, ctx: ClipViewModel):
        super().__init__(channel_idx, video_source_changed_signal, consumer_video_fps_sync_mode)
        self.ctx = ctx
        self.__number_of_alarms = number_of_alarms
        self.__num_of_inference_per_sec = num_of_inference_per_sec  # Number of frames per second for inference (e.g., 10)
        self.__max_np_array_similarity_queue = max_np_array_similarity_queue  # Maximum number of frame collection for inference (e.g., 5)

        self.__prev_np_array_similarity = None
        self.__np_array_similarity_queue = None
        self.__init_np_array_similarity()

        self.__last_update_time_text = 0  # Initialize the last update time
        self.__interval_update_time_text = 1.0  # Set update interval to 1 seconds (adjust as needed)
        self.__frame_count = 0
        self.__dxnn_fps = -1.0
        self.__sol_fps = -1.0

        self.image_transform = self.__transform(224)
        self.video_mask = torch.ones(1, 1)

        sentence_list_update_signal.connect(self.__init_np_array_similarity)
        
        self.inference_engine_async_mode = inference_engine_async_mode
        
        if self.inference_engine_async_mode:
            self.video_pred = np.array((1, 512), dtype=np.float32) * 0.0

    @overrides()
    def _process_impl(self, channel_idx, frame, fps):
        if self._channel_idx != channel_idx:
            raise RuntimeError("channel index is not correct")

        if frame is None:
            logging.debug("QImage is None on VideoConsumer" + str(frame))
            return

        # Increment the frame counter
        self.__frame_count += 1

        # Calculate interval (must be at least 1 / max fps must be 30(for in case of rtsp))
        interval = max(1, int(min(30, fps) / self.__num_of_inference_per_sec))
        # Perform inference only on certain frames based on the interval
        if self.__frame_count % interval != 0:
            return  # Skip frames that don't match the interval
        else:
            self.__frame_count = 0

        # for prevent UI freeze
        time.sleep(0.01)

        s = time.perf_counter_ns()

        similarity_list = []

        dxnn_s = time.perf_counter_ns()
        input_data = self.image_transform(Image.fromarray(frame).convert("RGB"))
        if self.inference_engine_async_mode:
            request_id = self.__dxnn_video_encoder.run_async(input_data, self)
            self.video_pred = self.__dxnn_video_encoder.wait(request_id)
        else:
            self.video_pred = self.__dxnn_video_encoder.run(input_data)
        dxnn_e = time.perf_counter_ns()

        sentence_vector_list = self.ctx.get_sentence_vector_list()
        sentence_vector_count = len(sentence_vector_list)
        sentence_list = self.ctx.get_sentence_list()
        sentence_count = len(sentence_list)

        for text_index in range(sentence_vector_count):
            try:
                similarity = self.__loose_similarity(sentence_vector_list[text_index], torch.Tensor(self.video_pred), self.video_mask)
            except Exception as ex:
                logging.debug(ex)
                return
            similarity_list.append(similarity)

        try:
            if len(similarity_list) > 0:
                np_array_similarity = np.stack(similarity_list).reshape(sentence_vector_count)
                if np_array_similarity.shape == self.__prev_np_array_similarity.shape:
                    self.__prev_np_array_similarity = np_array_similarity
                    self.__push_np_array_similarity_queue(np_array_similarity)
                else:
                    return

        except Exception as ex:
            # traceback.print_exc()
            logging.debug(ex)
            return

        e = time.perf_counter_ns()
        dxnn_fps = 1000 / ((dxnn_e - dxnn_s) / 1000000)
        sol_fps = 1000 / ((e - s) / 1000000)
        self.__dxnn_fps = dxnn_fps
        self.__sol_fps = sol_fps

        self._update_each_fps(channel_idx, dxnn_fps, sol_fps)

        # calculate mean_np_array_similarity
        sum_np_array_similarity = np.zeros(sentence_count)
        np_array_similarity_list: list = self.__np_array_similarity_queue.peek()
        for np_array_similarity in np_array_similarity_list:
            sum_np_array_similarity += np_array_similarity
        mean_np_array_similarity = 0 if len(np_array_similarity_list) == 0 else sum_np_array_similarity / len(np_array_similarity_list)

        self.__update_argmax_text(sentence_list, mean_np_array_similarity, channel_idx)

        if channel_idx == 0:
            self._update_overall_fps(channel_idx)

    # @staticmethod
    # def pp_callback(outputs, arg):
    #     x = outputs[0]
    #     x = x[:, 0]
    #     arg.value.video_pred = x / np.linalg.norm(x, axis=-1, keepdims=True)
    #     return 0
    
    def get_update_sentence_output_signal(self):
        return self.__update_sentence_output_signal

    def get_clear_sentence_output_signal(self):
        return self.__clear_sentence_output_signal

    def __push_np_array_similarity_queue(self, np_array_similarity):
        # If the queue is full, remove the oldest image
        if self.__np_array_similarity_queue.full():
            self.__np_array_similarity_queue.get()  # Remove the oldest image

        # Add the new image to the queue
        self.__np_array_similarity_queue.put(np_array_similarity)

    def __pop_np_array_similarity_queue(self):
        if not self.__np_array_similarity_queue.empty():
            return self.__np_array_similarity_queue.get()
        return None

    @staticmethod
    def __transform(n_px):
        return Compose([
            Resize(n_px, interpolation=Image.BICUBIC),
            CenterCrop(n_px),
            lambda image: image.convert("RGB"),
            ToTensor(),
            Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
        ])

    def __update_argmax_text(self, sentence_list: list[Sentence], logit_list, channel_idx):
        current_update_time_text = time.time()
        if current_update_time_text - self.__last_update_time_text < self.__interval_update_time_text:
            return

        sentence_output_list: list[SentenceOutput] = []
        sorted_index = np.argsort(logit_list)
        indices_index = np.array(sorted(sorted_index[(-1 * self.__number_of_alarms):]))
        for t in indices_index:
            try:
                score = logit_list[t]
                sentence = sentence_list[t]

                if score > sentence.get_score_threshold() and sentence.get_disabled() is False:
                    sentence_output_list.append(SentenceOutput(sentence, score))
            except Exception as ex:
                # traceback.print_exc()
                logging.debug(ex)
                continue

        self.__clear_sentence_output_signal.emit(channel_idx)
        for sentence_output in sentence_output_list:
            self.__update_sentence_output_signal.emit(
                channel_idx,
                sentence_output.get_sentence_text(),
                sentence_output.get_percentage(),
                sentence_output.get_score(),
                sentence_output.get_alarm(),
                sentence_output.get_alarm_title(),
                sentence_output.get_alarm_position(),
                sentence_output.get_alarm_color(),
                sentence_output.get_media_alarm(),
                sentence_output.get_media_alarm_title(),
                sentence_output.get_media_alarm_media_path(),
                sentence_output.get_media_alarm_position()
            )

        self.__last_update_time_text = current_update_time_text

    @overrides()
    def _cleanup(self, channel_idx):
        if self._channel_idx != channel_idx:
            raise RuntimeError("channel index is not correct")

        self.__init_np_array_similarity()
        self.__last_update_time_text = 0  # Initialize the last update time
        self.__interval_update_time_text = 1  # Set update interval to 1 seconds (adjust as needed)
        self.__frame_count = 0
        self.__dxnn_fps = -1.0
        self.__sol_fps = -1.0

    @staticmethod
    def __mean_pooling_for_similarity_visual(vis_output, video_frame_mask):
        video_mask_un = video_frame_mask.to(dtype=torch.float).unsqueeze(-1)
        visual_output = vis_output * video_mask_un
        video_mask_un_sum = torch.sum(video_mask_un, dim=1, dtype=torch.float)
        video_mask_un_sum[video_mask_un_sum == 0.0] = 1.0
        video_out = torch.sum(visual_output, dim=1) / video_mask_un_sum
        return video_out

    def __loose_similarity(self, text_vectors, video_vectors, video_frame_mask):
        sequence_output, visual_output = (
            text_vectors.contiguous(),
            video_vectors.contiguous(),
        )
        visual_output = visual_output / visual_output.norm(dim=-1, keepdim=True)
        visual_output = self.__mean_pooling_for_similarity_visual(
            visual_output, video_frame_mask
        )
        visual_output = visual_output / visual_output.norm(dim=-1, keepdim=True)

        try:
            if sequence_output.ndim > 1:
                sequence_output = sequence_output.squeeze(1)
        except Exception as ex:
            # traceback.print_exc()
            logging.debug(ex)
            return
        sequence_output = sequence_output / sequence_output.norm(dim=-1, keepdim=True)
        retrieve_logits = torch.matmul(sequence_output, visual_output.t())
        return retrieve_logits

    def __init_np_array_similarity(self):
        self.__prev_np_array_similarity = np.zeros(len(self.ctx.get_sentence_list()))

        if hasattr(self, '__np_array_similarity_queue'):
            del self.__np_array_similarity_queue
        self.__np_array_similarity_queue = PeekableQueue(self.__max_np_array_similarity_queue)
