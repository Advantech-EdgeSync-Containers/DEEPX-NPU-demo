from __future__ import annotations
import argparse
import os
import sys
import subprocess

import numpy as np
import torch
from PIL import Image
from torchvision.transforms import Compose, Resize, CenterCrop, ToTensor, Normalize

project_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_path)
from clip_demo_app_pyqt.lib.clip.dx_text_encoder import ONNXModel

from clip.simple_tokenizer import SimpleTokenizer as ClipTokenizer
from tqdm import tqdm

import threading
import time

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

import cv2
print(cv2.getBuildInformation())

if os.name == "nt":
    import ctypes
    for p in os.environ.get("PATH").split(";"):
        dxrtlib = os.path.join(p, "dxrt.dll")
        if os.path.exists(dxrtlib):
            ctypes.windll.LoadLibrary(dxrtlib)

from dx_engine import InferenceEngine, InferenceOption


# 디스플레이 화면의 크기를 알기 위함.
import tkinter as tk

root = tk.Tk()
root.withdraw()

VIEWER_TOT_SIZE_W = root.winfo_screenwidth()
VIEWER_TOT_SIZE_H = root.winfo_screenheight()

SPECIAL_TOKEN = {
    "CLS_TOKEN": "<|startoftext|>",
    "SEP_TOKEN": "<|endoftext|>",
    "MASK_TOKEN": "[MASK]",
    "UNK_TOKEN": "[UNK]",
    "PAD_TOKEN": "[PAD]",
}
MAX_WORDS = 32
DEVICE = "cpu"

global_input = ""
global_quit = False

# Supported video file extensions
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']

def _find_video_file(base_path: str, video_name: str) -> str:
    """
    Find video file with supported extension in the base path
    
    Args:
        video_name: Name of the video file without extension
        
    Returns:
        Full path to the video file with extension
    """
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        video_path = os.path.join(base_path, video_name + ext)
        if os.path.exists(video_path):
            print(f"Found video file: {video_path}")
            return video_path
    
    # If no file found with supported extension, try with .mp4 as fallback
    fallback_path = os.path.join(base_path, video_name + ".mp4")
    print(f"No video file found with supported extensions for '{video_name}'. Using fallback: {fallback_path}")
    return fallback_path

def get_args():
    # fmt: off
    parser = argparse.ArgumentParser(description="Generate Similarity Matrix from ONNX files")

    # Dataset Path Arguments
    parser.add_argument("--features_path", type=str, default="assets", help="Videos directory")

    # Dataset Configuration Arguments
    parser.add_argument("--max_words", type=int, default=32, help="")
    parser.add_argument("--feature_framerate", type=int, default=1, help="")
    parser.add_argument("--slice_framepos", type=int, default=0, choices=[0, 1, 2], help="0: cut from head frames; 1: cut from tail frames; 2: extract frames uniformly.")

    # Model Path Arguments
    parser.add_argument("--token_embedder_onnx", type=str, default="assets/onnx/embedding_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for token embedder")
    parser.add_argument("--text_encoder_onnx", type=str, default="assets/onnx/textual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for text encoder")
    parser.add_argument("--video_encoder_onnx", type=str, default="assets/onnx/visual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for video encoder")
    parser.add_argument("--video_encoder_dxnn", type=str, default="assets/dxnn/clip_vit_250331.dxnn", help="ONNX file path for video encoder")

    return parser.parse_args()

def insert_text_in_term():
    global global_input
    global global_quit
    while True:
        global_input = input("Enter text to display on video (insert 'quit' to quit): ")
        if global_input == "quit":
            global_quit = True
            break
        if global_quit:
            break

def _mean_pooling_for_similarity_visual(vis_output, video_frame_mask):
    video_mask_un = video_frame_mask.to(dtype=torch.float).unsqueeze(-1)
    visual_output = vis_output * video_mask_un
    video_mask_un_sum = torch.sum(video_mask_un, dim=1, dtype=torch.float)
    video_mask_un_sum[video_mask_un_sum == 0.0] = 1.0
    video_out = torch.sum(visual_output, dim=1) / video_mask_un_sum
    return video_out

def _loose_similarity(text_vectors, video_vectors, video_frame_mask):
    sequence_output, visual_output = (
        text_vectors.contiguous(),
        video_vectors.contiguous(),
    )
    visual_output = visual_output / visual_output.norm(dim=-1, keepdim=True)
    visual_output = _mean_pooling_for_similarity_visual(
        visual_output, video_frame_mask
    )
    visual_output = visual_output / visual_output.norm(dim=-1, keepdim=True)

    sequence_output = sequence_output.squeeze(1)
    sequence_output = sequence_output / sequence_output.norm(dim=-1, keepdim=True)
    retrieve_logits = torch.matmul(sequence_output, visual_output.t())
    return retrieve_logits

def get_text_vectors(text_list: list[str], embedder, encoder):
    ret = []
    for i in tqdm(range(len(text_list))):
        text = text_list[i]
        text = text if len(text.split(" ")) < MAX_WORDS - 1 else str.join(text.split(" ")[:MAX_WORDS - 2])
        text = SPECIAL_TOKEN["CLS_TOKEN"] + " " + text + " " + SPECIAL_TOKEN["SEP_TOKEN"]
        token_ids = ClipTokenizer().encode(text)
        token_ids_mask = [1] * len(token_ids) + [0] * (
                            MAX_WORDS - len(token_ids)
                        )
        token_ids = token_ids + [0] * (
                            MAX_WORDS - len(token_ids)
                        )
        token_ids_mask = torch.tensor([token_ids_mask]).to(DEVICE, dtype=torch.float32)
        token_ids = torch.tensor([token_ids]).to(DEVICE)
        text_embedding = embedder(token_ids)
        text_vectors = encoder([text_embedding, token_ids_mask])
        ret.append(text_vectors)
    return ret if len(ret) > 1 else text_vectors

class DXVideoEncoder():
    def __init__(self, model_path: str):
        io = InferenceOption()
        io.set_use_ort(False)
        self.ie = InferenceEngine(model_path, io)
        self.cpu_offloaded = False
        if "cpu_0" in self.ie.get_task_order():
            self.cpu_offloaded = True
    
    def run(self, x):
        x = x.numpy()
        if not self.cpu_offloaded:
            x = self.preprocess_numpy(x)
        x = np.ascontiguousarray(x)
        o = self.ie.run([x])[0]
        o = self.postprocess_numpy(o)
        o = torch.from_numpy(o)
        return o

    @staticmethod
    def preprocess_numpy(
        x: np.ndarray,
        mul_val: np.ndarray = np.float32([64.75055694580078]),
        add_val: np.ndarray = np.float32([-11.950003623962402]),
    ) -> np.ndarray:
        x = x.astype(np.float32)
        x = x * mul_val + add_val
        x = x.round().clip(-128, 127)
        x = x.astype(np.int8)
        x = np.reshape(x, [1, 3, 7, 32, 7, 32])
        x = np.transpose(x, [0, 2, 4, 3, 5, 1])
        x = np.reshape(x, [1, 49, 48, 64])
        x = np.transpose(x, [0, 2, 1, 3])
        return x

    @staticmethod
    def postprocess_numpy(x: np.ndarray) -> np.ndarray:
        x = x.reshape(-1, 512)
        x = x[0, :]
        assert x.shape == (512, )
        x = x / np.linalg.norm(x, axis=-1, keepdims=True)
        return x

class SingleVideoThread(threading.Thread):
    def __init__(self, base_path: str, video_path_list: list[str], position: tuple, imshow_size: tuple):
        super().__init__()
        ## SETTING
        self.input_size = 224
        self.imshow_size = imshow_size
        self.npu_preprocess_mul_val = np.float32([64.75055694580078])
        self.npu_preprocess_add_val = np.float32([-11.950003623962402])
        self.last_update_time_text = 0
        self.interval_update_time_text = 1
        self.number_of_alarms = 2
        self.video_fps = 30
        self.text_line_height = 30
        self.font_face = cv2.FONT_HERSHEY_SIMPLEX
        self.text_thickness = 2
        #self.textarea_padding = 20
        self.textarea_padding = 0
        self.text_line_height = 40
        self.textarea_left = self.textarea_padding
        self.textarea_height = self.text_line_height * self.number_of_alarms
        self.textarea_bottom = self.textarea_height + self.textarea_padding
        self.text_padding = 30
        self.text_left = self.textarea_left + self.text_padding
        self.text_bottom = self.textarea_bottom - self.text_padding
        self.text_scale = 0.8
        
        if video_path_list[0] == "/dev/video0":
            self.is_camera_source = True
            self.base_path = ""
            self.video_path_list = ["/dev/video0"]
            self.current_index = 0
            self.video_path_current = os.path.join(self.video_path_list[self.current_index])
        else:
            self.is_camera_source = False
            self.base_path = base_path
            self.video_path_list = video_path_list
            self.current_index = 0
            self.video_path_current = _find_video_file(self.base_path, self.video_path_list[self.current_index])

        if use_vaapi:
            self.cap = cv2.VideoCapture(self.__generate_gst_pipeline(self.video_path_current), cv2.CAP_GSTREAMER)
        else:
            self.cap = cv2.VideoCapture(self.video_path_current)

        ret, frame = self.cap.read()
        if ret:
            self.current_original_frame = frame
        else:
            self.current_original_frame = np.zeros((self.imshow_size[1], self.imshow_size[0], 3), dtype=np.uint8)

        self.position = position
        self.transform_ = self.transform(224)

        self.video_source_updated = False
        
        self.similarity_list = []
        self.this_argmax_text = []
        
        self.dxnn_fps = 0
        self.sol_fps = 0

    
    def transform(self, n_px):
        return Compose([
            Resize(n_px, interpolation=Image.BICUBIC),
            CenterCrop(n_px),
            lambda image: image.convert("RGB"),
            ToTensor(),
            Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
        ])
        
    def run(self):
        global global_quit
        global global_input

        self.get_cap()
        while not global_quit:
            self.get_cap()
            time.sleep(1 / self.video_fps * 0.75)

            if global_quit:
                break
            
        self.cap.release()

    def __generate_gst_pipeline(self, video_path):
        width = self.imshow_size[0]
        height = self.imshow_size[1]

        if self.is_camera_source:
            gst_pipeline = (
                f"v4l2src device={video_path} ! "
                f"videoconvert ! appsink"
            )
        else:
            gst_pipeline = (
                f"filesrc location={video_path} ! "
                # f"videotestsrc ! "
                f"queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
                f"qtdemux ! vaapidecodebin ! "
                # f"qtdemux ! h264parse ! avdec_h264 ! "        // use cpu only
                f"queue leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
                f"videoconvert qos=false ! "
                 f"videoscale method=0 add-borders=false qos=false ! "
                 f"video/x-raw,width={width},height={height},pixel-aspect-ratio=1/1 ! "
                f"queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
                f"appsink"
            )

        return gst_pipeline
        
    
    def get_cap(self):
        ret, frame = self.cap.read()
        if not ret:
            self.current_index = 0 if self.current_index + 1 == len(self.video_path_list) else self.current_index + 1
            self.video_path_current = _find_video_file(self.base_path, self.video_path_list[self.current_index])
            self.cap.release()
            if use_vaapi:
                self.cap = cv2.VideoCapture(self.__generate_gst_pipeline(self.video_path_current), cv2.CAP_GSTREAMER)
            else:
                self.cap = cv2.VideoCapture(self.video_path_current)
            ret, frame = self.cap.read()
            self.video_source_updated = True
        self.current_original_frame = frame
    
    def get_resized_frame(self):
        if use_vaapi:
            # The image has already been resized at the GStreamer level, so resizing is skipped.
            resized_frame = self.current_original_frame
        else:
            # sw resize
            resized_frame = cv2.resize(self.current_original_frame, self.imshow_size, cv2.INTER_LINEAR)

        if len(self.this_argmax_text) > 0:
            try:
                cv2.rectangle(
                    resized_frame,
                    (self.textarea_left, self.imshow_size[1] - self.textarea_bottom),
                    (self.imshow_size[0] - self.textarea_padding, self.imshow_size[1] - self.textarea_padding),
                    (0, 0, 0),
                    -1)
                for t in range(len(self.this_argmax_text)):
                    cv2.putText(
                        resized_frame,
                        self.this_argmax_text[t],
                        (self.text_left, self.imshow_size[1] - self.text_bottom + (self.text_line_height * t)),
                        self.font_face, self.text_scale, (0, 0, 255), self.text_thickness, cv2.LINE_AA)
            except Exception as e:
                pass

        # if self.sol_fps > 0 and self.dxnn_fps > 0:
        #     cv2.rectangle(resized_frame, (self.imshow_size[0] - 320, 0), (self.imshow_size[0], 60), 
        #                     (0, 0, 0), -1)
        #     cv2.putText(resized_frame, "APP : {} FPS".format(int(self.sol_fps)),
        #                 (self.imshow_size[0] - 300, 25), self.font_face, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        #     cv2.putText(resized_frame,  "NPU    : {} FPS".format(int(self.dxnn_fps)),
        #                 (self.imshow_size[0] - 300, 48), self.font_face, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

        return resized_frame
    
    def status_video_source(self):
        ret = self.video_source_updated
        self.video_source_updated = False
        return ret
    
    def update(self, text_list, logit_list, alarm_list):
        current_update_time_text = time.time()
        if current_update_time_text - self.last_update_time_text < self.interval_update_time_text:
            return
        argmax_text = []
        sorted_index = np.argsort(logit_list)
        indices_index = np.array(sorted(sorted_index[-self.number_of_alarms:]))
        for t in indices_index:
            value = logit_list[t]
            min_value = alarm_list[t][0]
            max_value = alarm_list[t][1]
            alarm_threshold = alarm_list[t][2]
            if value < min_value:
                ret_level = 0
            elif value > max_value:
                ret_level = 100
            else:
                ret_level = int((value - min_value) / (max_value - min_value) * 100)
            if value > alarm_threshold:
                # print(value, ", ", alarm_threshold)
                argmax_text.append(text_list[t])
        self.this_argmax_text = argmax_text
        self.last_update_time_text = current_update_time_text


class VideoViewer(threading.Thread):
    def __init__(self, gt_text_list: list[str], video_threads: list[SingleVideoThread]):
        super().__init__()
        self.gt_text_list = gt_text_list
        self.video_threads = video_threads
        self.stop_thread = False
        self.final_text = ""
        self.result_text = ""
        self.result_logit = 0.0
        self.released = False
        self.font_face = cv2.FONT_HERSHEY_SIMPLEX
        self.text_thickness = 2
        self.x, self.y = 20, 80
        self.view_pannel_frame = np.zeros((VIEWER_TOT_SIZE_H, VIEWER_TOT_SIZE_W, 3), dtype=np.uint8)  # 검정색 판 
        self.show_fps_roi = [int(VIEWER_TOT_SIZE_W * 4 / 5), 0]

        # text list update setting values        
        self.update_new_text = False
        self.pop_last_text = False
        self.new_text = ""
        
        self.thread_length = len(video_threads)
        
        self.video_mask = torch.ones(1, 1)

        self.debug_mode = False
        
        self.last_update_time_fps = 0
        self.interval_update_time_fps = 0.3
        
        self.total_dxnn_fps = 0
        self.total_sol_fps = 0
        self.total_n = 0
        
    def run(self):
        global global_input
        global global_quit
        for thread in self.video_threads:
            thread.start()
            thread.similarity_list = np.zeros((len(self.gt_text_list)))

        wnd_prop_id = cv2.WND_PROP_FULLSCREEN
        wnd_prop_value = cv2.WINDOW_FULLSCREEN
        if self.debug_mode:
            wnd_prop_value = cv2.WINDOW_KEEPRATIO

        cv2.namedWindow('Video', wnd_prop_id)
        cv2.setWindowProperty('Video', wnd_prop_id, wnd_prop_value)
        while not global_quit:
            for vCap in self.video_threads:
                position = vCap.position
                vCap_imshow_size = vCap.imshow_size
                self.view_pannel_frame[position[1]:position[1]+vCap_imshow_size[1], position[0]:position[0]+vCap_imshow_size[0]] = vCap.get_resized_frame()
                if vCap.sol_fps > 0 and vCap.dxnn_fps > 0:
                    self.total_dxnn_fps += vCap.dxnn_fps
                    self.total_sol_fps += vCap.sol_fps
                    self.total_n += 1
            
            if self.total_sol_fps > 0 and self.total_dxnn_fps > 0 :
                cv2.rectangle(self.view_pannel_frame, (VIEWER_TOT_SIZE_W - 500, 0), (VIEWER_TOT_SIZE_W, 130), 
                              (0, 0, 0), -1)
                cv2.putText(self.view_pannel_frame, "APP  : {:5.3f} FPS".format((self.total_sol_fps/self.total_n)),
                            (VIEWER_TOT_SIZE_W - 450, 50), self.font_face, 1, (255, 255, 255), self.text_thickness, cv2.LINE_AA
                            )
                cv2.putText(self.view_pannel_frame,  "NPU  : {:5.3f} FPS".format((self.total_dxnn_fps/self.total_n)),
                            (VIEWER_TOT_SIZE_W - 450, 100), self.font_face, 1, (255, 255, 255), self.text_thickness, cv2.LINE_AA
                            )
            cv2.imshow('Video', self.view_pannel_frame)
            
            if cv2.waitKey(1) == ord('q'):
                global_quit = True
                break
        cv2.destroyAllWindows()
    
    def update_fps(self, dxnn_fps, sol_fps):
        current_update_time_fps = time.time()
        if current_update_time_fps - self.last_update_time_fps < self.interval_update_time_fps:
            return
        self.dxnn_fps = dxnn_fps
        self.sol_fps = sol_fps
        self.last_update_time_fps = current_update_time_fps


class DXEngineThread(threading.Thread):
    def __init__(self, text_list: list[str], video_threads: list[SingleVideoThread], text_vectors: list, video_encoder: DXVideoEncoder, text_alarm_level_list: list, video_viewer: VideoViewer):
        super().__init__()
        self.text_list = text_list
        self.text_alarm_level_list = text_alarm_level_list
        self.video_threads = video_threads
        self.image_transform = self.transform(224)
        self.video_encoder = video_encoder
        self.text_vectors = text_vectors
        self.video_mask = torch.ones(1, 1)
        self.video_viewer = video_viewer
    
    def transform(self, n_px):
        return Compose([
            Resize(n_px, interpolation=Image.BICUBIC),
            CenterCrop(n_px),
            lambda image: image.convert("RGB"),
            ToTensor(),
            Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
        ])

    def run(self):
        global global_quit
        global global_input
        time.sleep(0.1)
        frame_count = 0
        while not global_quit:
            for index in range(len(self.video_threads)):
                s = time.perf_counter_ns()
                similarity_list = []
                vCap = self.video_threads[index]
                if vCap.status_video_source():
                    vCap.similarity_list = np.zeros((len(self.text_list)))
                    vCap.last_update_time_text = 0
                    frame_count = 0
                frame = vCap.current_original_frame.copy()
                dxnn_s = time.perf_counter_ns()
                input_data = self.image_transform(Image.fromarray(frame).convert("RGB"))
                video_pred = self.video_encoder.run(input_data)
                dxnn_e = time.perf_counter_ns()
                # print(index, " : ", video_pred.shape)
                for text_index in range(len(self.text_vectors)):
                    ret = _loose_similarity(self.text_vectors[text_index], video_pred, self.video_mask)
                    similarity_list.append(ret)
                similarity_list = np.stack(similarity_list).reshape(len(self.text_vectors))
                vCap.similarity_list += similarity_list
                e = time.perf_counter_ns()
                dxnn_fps = 1000/((dxnn_e - dxnn_s) / 1000000)
                sol_fps = 1000/((e - s) / 1000000)
                vCap.dxnn_fps = dxnn_fps
                vCap.sol_fps = sol_fps
                self.video_viewer.update_fps(dxnn_fps, sol_fps)
            for index in range(len(self.video_threads)):
                vCap = self.video_threads[index]
                vCap.update(self.text_list, vCap.similarity_list/(frame_count+1), self.text_alarm_level_list)
            frame_count +=1


def main():
    global global_input
    global global_quit

    args = get_args()

    dxnn_video_encoder = DXVideoEncoder(args.video_encoder_dxnn)
    
    token_embedder = ONNXModel(
        model_path=args.token_embedder_onnx
    )
    text_encoder = ONNXModel(
        model_path=args.text_encoder_onnx
    )

    gt_video_path_lists = [
        [
            "demo_videos/burning_car",
        ],
        [
            "demo_videos/crowded_subway_platform",
        ],
        [
            "demo_videos/elderly_woman_fallen_indoor",
        ],
        [
            "demo_videos/kitchen_stove_fire",
        ],
        [
            "demo_videos/men_fighting_indoors",
        ],
        [
            "demo_videos/burning_car",
        ],
        [
            "demo_videos/crowded_subway_platform",
        ],
        [
            "demo_videos/elderly_woman_fallen_indoor",
        ],
        [
            "demo_videos/kitchen_stove_fire",
        ],
        [
            "demo_videos/men_fighting_indoors",
        ],
        [
            "demo_videos/burning_car",
        ],
        [
            "demo_videos/crowded_subway_platform",
        ],
        [
            "demo_videos/elderly_woman_fallen_indoor",
        ],
        [
            "demo_videos/kitchen_stove_fire",
        ],
        [
            "demo_videos/men_fighting_indoors",
        ],
        [
            "demo_videos/burning_car",
        ],
    ]
    
    # gt_video_path_lists = [
    #     [
    #         "demo_videos/fire_on_car",
    #     ],
    #     [
    #         "demo_videos/dam_explosion_short",
    #     ],
    #     [
    #         "demo_videos/violence_in_shopping_mall_short",
    #     ],
    #     [
    #         "demo_videos/gun_terrorism_in_airport",
    #     ],
    #     [
    #         "demo_videos/crowded_in_subway",
    #     ],
    #     [
    #         "demo_videos/heavy_structure_falling",
    #     ],
    #     [
    #         "demo_videos/electrical_outlet_is_emitting_smoke",
    #     ],
    #     [
    #         "demo_videos/pot_is_catching_fire",
    #     ],
    #     [
    #         "demo_videos/falldown_on_the_grass",
    #     ],
    #     [
    #         "demo_videos/fighting_on_field",
    #     ],
    #     [
    #         "demo_videos/fire_in_the_kitchen",
    #     ],
    #     [
    #         "demo_videos/group_fight_on_the_streat",
    #     ],
    #     [
    #         "demo_videos/iron_is_on_fire",
    #     ],
    #     [
    #         "demo_videos/someone_helps_old_man_who_is_fallting_down",
    #     ],
    #     [
    #         "demo_videos/the_pile_of_sockets_is_smoky_and_on_fire"
    #     ],
    #     [
    #         "demo_videos/two_childrens_are_fighting",
    #     ],
    # ]

    gt_text_alarm_level = [
        [0.27, 0.29, 0.28],      # "The subway is crowded with people",
        [0.27, 0.29, 0.28],      # "People is crowded in the subway",

        [0.21, 0.25, 0.225],     # "Heavy objects are fallen",

        [0.23, 0.25, 0.24],      # "Physical confrontation occurs between two people",
        [0.22, 0.25, 0.23],      # "Violence with kicking and punching",

        [0.27, 0.29, 0.28],       # "Terrorism is taking place at the airport",
        [0.23, 0.26, 0.247],       # "Terrorist is shooting at people",

        [0.24, 0.28, 0.255],       # "The water is exploding out",
        [0.24, 0.28, 0.255],      # "The water is gushing out",

        [0.23, 0.26, 0.24],     # "Fire is coming out of the car",
        [0.24, 0.28, 0.26],     # "The car is exploding",

        [0.23, 0.26, 0.24],     # "The electrical outlet on the wall is emitting smoke",
        [0.23, 0.26, 0.24],     # "Smoke is rising from the electrical outlet."

        [0.23, 0.26, 0.24],     # "A pot on the induction cooktop is catching fire.",
        [0.23, 0.26, 0.24],     # "A fire broke out in a pot in the kitchen."

        [0.23, 0.26, 0.24],     # "Two childrens are fighting.",
        [0.23, 0.26, 0.24],     # "Two children start crying after a fight."

        [0.23, 0.26, 0.24],     # "Several men are engaged in a fight.",
        [0.23, 0.26, 0.24],     # "Several people are fighting in the street.",

        [0.23, 0.26, 0.24],     # "An elderly man is complaining of pain on the street."
        [0.23, 0.26, 0.24],     # "An man is crouching on the street."

        [0.23, 0.26, 0.24],     # "Someone helps old man who is falling down."
        [0.23, 0.26, 0.24],     # "An elderly grandfather is lying on the floor."

        [0.23, 0.26, 0.24],     # "A fire has occurred in the electric iron."
        [0.23, 0.26, 0.24],     # "The electric iron on the table is on fire."

        [0.23, 0.26, 0.24],     # "Two men are engaging in mixed martial arts on the ring."
    ]

    gt_text_list = [
        "The subway is crowded with people",
        "People is crowded in the subway",
        
        "Heavy objects are fallen",
        
        "Physical confrontation occurs between two people",
        "Violence with kicking and punching",
        
        "Terrorism is taking place at the airport",
        "Terrorist is shooting at people",
        
        "The water is exploding out",
        "The water is gushing out",
        
        "Fire is coming out of the car",
        "The car is exploding",

        "The electrical outlet on the wall is emitting smoke",
        "Smoke is rising from the electrical outlet.",

        "A pot on the induction cooktop is catching fire.",
        "A fire broke out in a pot in the kitchen.",

        "Two childrens are fighting.",
        "Two children start crying after a fight.",

        "Several men are engaged in a fight.",
        "Several people are fighting in the street.",

        "An elderly man is complaining of pain on the street.",
        "An man is crouching on the street.",

        "Someone helps old man who is falling down.",
        "An elderly grandfather is lying on the floor",

        "A fire has occurred in the electric iron.",
        "The electric iron on the table is on fire.",

        "Two men are engaging in mixed martial arts on the ring.",
    ]


    div = int(np.ceil(np.sqrt(len(gt_video_path_lists))))
    print("DIV : ", div) 
    video_threads = []
    for i in range(len(gt_video_path_lists)):
        pos_x, pos_y = (i % div) * (VIEWER_TOT_SIZE_W/div), (i // div) * (VIEWER_TOT_SIZE_H/div)
        video_threads.append(
                    SingleVideoThread(
                                args.features_path, gt_video_path_lists[i], (int(pos_x), int(pos_y)), (int(VIEWER_TOT_SIZE_W/div), int(VIEWER_TOT_SIZE_H/div))
                    )
        )
    
    text_vector_list = get_text_vectors(gt_text_list, token_embedder, text_encoder)
    video_viewer = VideoViewer(gt_text_list, video_threads)
    dxnn_engine = DXEngineThread(gt_text_list, video_threads, text_vector_list, dxnn_video_encoder, gt_text_alarm_level, video_viewer)
    video_viewer.start()
    dxnn_engine.start()
    
if __name__ == "__main__":
    
    main()
