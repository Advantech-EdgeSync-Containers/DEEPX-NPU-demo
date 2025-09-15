import argparse
import os
import sys
import subprocess
import time

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

# Global Variables

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
    parser.add_argument("--features_path", type=str, default="assets/demo_videos", help="Videos directory")

    # Dataset Configuration Arguments
    parser.add_argument("--max_words", type=int, default=32, help="")
    parser.add_argument("--feature_framerate", type=int, default=1, help="")
    parser.add_argument("--slice_framepos", type=int, default=0, choices=[0, 1, 2],
                        help="0: cut from head frames; 1: cut from tail frames; 2: extract frames uniformly.")

    # Model Path Arguments
    parser.add_argument("--token_embedder_onnx", type=str,
                        default="assets/onnx/embedding_f32_op14_clip4clip_msrvtt_b128_ep5.onnx",
                        help="ONNX file path for token embedder")
    parser.add_argument("--text_encoder_onnx", type=str,
                        default="assets/onnx/textual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx",
                        help="ONNX file path for text encoder")
    parser.add_argument("--video_encoder_onnx", type=str,
                        default="assets/onnx/visual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx",
                        help="ONNX file path for video encoder")
    parser.add_argument("--video_encoder_dxnn", type=str, default="assets/dxnn/clip_vit_250331.dxnn",
                        help="ONNX file path for video encoder")

    return parser.parse_args()
    # fmt: on


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif sys.platform.startswith("darwin"):
        return "mps"
    else:
        return "cpu"


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
    def preprocess_torch(
            x: torch.Tensor,
            mul_val: torch.Tensor = torch.FloatTensor([64.75055694580078]),
            add_val: torch.Tensor = torch.FloatTensor([-11.950003623962402]),
    ) -> torch.Tensor:
        x = x.to(torch.float32)
        x = x * mul_val + add_val
        x = x.round().clip(-128, 127)
        x = x.to(torch.int8)
        x = torch.reshape(x, [1, 3, 7, 32, 7, 32])
        x = torch.permute(x, [0, 2, 4, 3, 5, 1])
        x = torch.reshape(x, [1, 49, 48, 64])
        x = torch.permute(x, [0, 2, 1, 3])
        return x

    @staticmethod
    def postprocess_numpy(x: np.ndarray) -> np.ndarray:
        x = x.reshape(-1, 512)
        x = x[0, :]
        assert x.shape == (512, )
        x = x / np.linalg.norm(x, axis=-1, keepdims=True)
        return x

    @staticmethod
    def postprocess_torch(x: torch.Tensor) -> torch.Tensor:
        x = x.reshape(-1, 512)
        x = x[0, :]
        assert x.shape == (512, )
        x = x / torch.norm(x, dim=-1, keepdim=True)
        return x


class VideoThread(threading.Thread):
    def __init__(self, features_path, video_paths, gt_text_list):
        super().__init__()
        if features_path == "0":
            print("[DEBUG] is camera source : TRUE")
            self.is_camera_source = True
            self.video_paths = ["/dev/video0"]
            self.current_index = 0
            self.video_path_current = os.path.join(self.video_paths[self.current_index])
        else:
            self.is_camera_source = False
            self.features_path = features_path
            self.video_paths = video_paths
            self.current_index = 0
            self.video_path_current = _find_video_file(features_path, self.video_paths[self.current_index])
        self.gt_text_list = gt_text_list
        self.stop_thread = False
        self.final_text = ""
        self.result_text = ""
        self.result_logit = 0.0
        self.released = False
        self.pannel_size_w = 1920
        self.pannel_size_h = 1080
        self.video_size_w = 920
        self.video_size_h = 690
        self.text_line_height = 30
        self.text_line_padding_ratio = 1.5
        self.font_face = cv2.FONT_HERSHEY_SIMPLEX
        self.text_thickness = 2
        self.number_of_alarms = 2
        self.last_update_time_text = 0  # Initialize the last update time
        self.interval_update_time_text = 1  # Set update interval to 1 seconds (adjust as needed)
        self.last_update_time_fps = 0  # Initialize the last update time
        self.interval_update_time_fps = 0.3  # Set update interval to 0.3 seconds (adjust as needed)
        self.view_pannel_frame = np.ones((self.pannel_size_h, self.pannel_size_w, 3),
                                         dtype=np.uint8) * 255  # pennel color
        self.x, self.y = 20, 80
        self.view_pannel_frame[self.y:self.y + self.video_size_w,
        self.x:self.x + self.video_size_w] = 255  # video letterbox color
        self.video_roi = [self.x, self.y + 115, self.video_size_w, self.video_size_h]
        self.terminal_roi = [self.pannel_size_w - self.x - self.video_size_w, int(self.pannel_size_h / 4) + 80]
        self.text_roi = [self.x + self.video_size_w + self.x,
                         self.y + 115 + int(self.video_size_h / 2) - self.text_line_height]
        self.show_fps_roi = [int(self.pannel_size_w * 4 / 5), 0]

        if use_vaapi:
            self.cap = cv2.VideoCapture(self.__generate_gst_pipeline(self.video_path_current), cv2.CAP_GSTREAMER)
        else:
            self.cap = cv2.VideoCapture(self.video_path_current)

        self.original = np.zeros((224, 224, 3), dtype=np.uint8)
        self.transform_ = self.transform(224)
        self.update_new_text = False
        self.pop_last_text = False
        self.new_text = ""

        self.debug_mode = False

        if self.debug_mode:
            self.text_line_height = 20
            self.text_thickness = 1
            self.text_roi = [self.x + self.video_size_w + self.x, self.y + 115 - self.text_line_height]

    def __generate_gst_pipeline(self, video_path):
        width = self.video_size_w
        height = self.video_size_h

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

    def run(self):
        global global_input
        global global_quit

        i = 0

        text_color = (0, 0, 0)
        line_type = cv2.LINE_8
        # get font_scale and font width, font height and baseline using height_in_pixels

        (font_scale, (_, _), baseline) = self.get_font_scale(self.text_line_height)
        text_height = int((self.text_line_height + baseline) * self.text_line_padding_ratio)

        if self.debug_mode:
            cv2.putText(self.view_pannel_frame,
                        "   [TEXT LIST]",
                        (self.terminal_roi[0], self.terminal_roi[1] + (text_height * (i + 1))),
                        self.font_face, font_scale, text_color, self.text_thickness, line_type)
            i += 1
            for text_i in self.gt_text_list:
                cv2.putText(self.view_pannel_frame,
                            "   " + text_i,
                            (self.terminal_roi[0],
                             self.terminal_roi[1] + (text_height * (i + 1))),
                            self.font_face, font_scale, text_color, self.text_thickness, line_type)
                i += 1

        wnd_prop_id = cv2.WND_PROP_FULLSCREEN
        wnd_prop_value = cv2.WINDOW_FULLSCREEN
        if self.debug_mode:
            wnd_prop_value = cv2.WINDOW_KEEPRATIO

        cv2.namedWindow('Video', wnd_prop_id)
        cv2.setWindowProperty('Video', wnd_prop_id, wnd_prop_value)
        while not self.stop_thread:
            ret, self.original = self.cap.read()
            if global_quit:
                self.released = True
                break

            if not ret:
                if self.is_camera_source:
                    print("[DEBUG] camera source is abnormally")
                    self.stop()
                    break
                
                # 현재 비디오가 끝났을 때 다음 비디오로 넘어감
                self.current_index += 1
                if self.current_index < len(self.video_paths):
                    self.video_path_current = _find_video_file(self.features_path, self.video_paths[self.current_index])
                    self.cap.release()
                    if use_vaapi:
                        self.cap = cv2.VideoCapture(self.__generate_gst_pipeline(self.video_path_current),
                                                    cv2.CAP_GSTREAMER)
                    else:
                        self.cap = cv2.VideoCapture(self.video_path_current)

                    ret, self.original = self.cap.read()
                else:
                    self.current_index = 0
                    self.video_path_current = _find_video_file(self.features_path, self.video_paths[self.current_index])
                    self.cap.release()
                    if use_vaapi:
                        self.cap = cv2.VideoCapture(self.__generate_gst_pipeline(self.video_path_current),
                                                    cv2.CAP_GSTREAMER)
                    else:
                        self.cap = cv2.VideoCapture(self.video_path_current)
                    ret, self.original = self.cap.read()

            # image resize
            if use_vaapi:
                # The image has already been resized at the GStreamer level, so resizing is skipped.
                frame = self.original
            else:
                frame = cv2.resize(self.original, (self.video_size_w, self.video_size_h), cv2.INTER_NEAREST)

            # 영상 위에 텍스트 추가
            self.view_pannel_frame[self.video_roi[1]:self.video_roi[1] + self.video_roi[3],
            self.video_roi[0]:self.video_roi[0] + self.video_roi[2]] = frame

            if self.update_new_text:
                cv2.putText(self.view_pannel_frame,
                            "   " + self.new_text,
                            (self.terminal_roi[0], self.terminal_roi[1] + (text_height * (i + 1))),
                            self.font_face, font_scale, text_color, self.text_thickness, line_type)

                i += 1
                self.update_new_text = False

            if self.pop_last_text:
                i -= 1
                cv2.rectangle(
                    self.view_pannel_frame,
                    (self.terminal_roi[0], self.terminal_roi[1] + (text_height * i) + baseline),
                    (self.pannel_size_w,
                     self.terminal_roi[1] + (text_height * (i + 1)) + baseline),
                    (255, 255, 255),
                    -1
                )

                self.pop_last_text = False
                self.final_text = " "

            cv2.imshow('Video', self.view_pannel_frame)

            if cv2.waitKey(30) == ord('q'):
                global_quit = True
                self.released = True
                break
            
        self.cap.release()
        cv2.destroyAllWindows()

    def stop(self):
        self.stop_thread = True

    def get_font_scale(self, height_in_pixels: int) -> (int, (int, int), int):
        # calc factor
        font_scale = 100
        ((fw, fh), baseline) = cv2.getTextSize(
            text="", fontFace=self.font_face, fontScale=font_scale, thickness=self.text_thickness)
        factor = (fh - 1) / font_scale

        # get fontScale using height_in_pixels
        height_in_pixels = self.text_line_height
        font_scale = (height_in_pixels - self.text_thickness) / factor
        ((fw, fh), baseline) = cv2.getTextSize(
            text="Test Text", fontFace=self.font_face, fontScale=font_scale, thickness=self.text_thickness)
        return font_scale, (fw, fh), baseline

    def update_text(self, text_list, logit_list, gt_text_alarm_level):
        # Apply throttling: Skip update if the defined interval has not passed since the last update
        current_time_text = time.time()
        if current_time_text - self.last_update_time_text < self.interval_update_time_text:
            return

        # get font_scale and font width, font height and baseline using height_in_pixels
        (font_scale, (_, _), baseline) = self.get_font_scale(self.text_line_height)
        text_height = int((self.text_line_height + baseline) * self.text_line_padding_ratio)

        sorted_index = np.argsort(logit_list)
        indices_index = sorted(sorted_index[-self.number_of_alarms:])

        cv2.rectangle(
            self.view_pannel_frame,
            (self.text_roi[0], self.text_roi[1]),
            (self.pannel_size_w,
             self.text_roi[1] + int(text_height * self.number_of_alarms) + baseline),
            (255, 255, 255),
            -1
        )
        text_i = 0
        for ii in indices_index:
            value = logit_list[ii]
            min_value = gt_text_alarm_level[ii][0]
            max_value = gt_text_alarm_level[ii][1]
            alarm_threshold = gt_text_alarm_level[ii][2]

            if value < min_value:
                ret_level = 0
            elif value > max_value:
                ret_level = 100
            else:
                ret_level = int((value - min_value) / (max_value - min_value) * 100)

            if value < alarm_threshold:
                text_color = (0, 0, 0)
                if self.debug_mode is False:
                    continue
            else:
                text_color = (0, 0, 255)

            result_str = text_list[ii]
            line_type = cv2.LINE_8

            if self.debug_mode:
                result_str = str(ret_level).rjust(3) + "%  |  " + "{:.3f}".format(value) + "  |  " + result_str
                line_type = cv2.LINE_AA

            cv2.putText(self.view_pannel_frame,
                        result_str,
                        (self.text_roi[0], self.text_roi[1] + (text_height * (text_i + 1))),
                        self.font_face, font_scale, text_color, self.text_thickness, line_type)
            text_i += 1

        # Update the last update time to the current time
        self.last_update_time_text = current_time_text

    def empty_text(self):
        cv2.rectangle(self.view_pannel_frame, (self.text_roi[0], self.text_roi[1] - 10),
                      (self.pannel_size_w, int(self.pannel_size_h / 2)), (255, 255, 255), -1)

    def transform(self, n_px):
        return Compose([
            Resize(n_px, interpolation=Image.BICUBIC),
            CenterCrop(n_px),
            lambda image: image.convert("RGB"),
            ToTensor(),
            Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711)),
        ])

    def get_input_tensor(self):
        try:
            frame_data = self.transform_(Image.fromarray(self.original).convert("RGB"))
        except Exception as e:
            frame_data = np.zeros((224, 224, 3), dtype=np.uint8)
            frame_data = np.transpose(frame_data, (2, 0, 1))
        input_data = torch.as_tensor(frame_data).float()
        input_data = input_data.unsqueeze(0)
        return input_data

    def update_text_vector(self, new_text_vector):
        self.new_text = new_text_vector
        self.update_new_text = True

    def pop_text_vector(self, index):
        self.pop_last_text = True

    def update_fps(self, dxnn_time_list, sol_time_list):
        # Apply throttling: Skip update if the defined interval has not passed since the last update
        current_time_fps = time.time()
        if current_time_fps - self.last_update_time_fps < self.interval_update_time_fps:
            return

        cv2.rectangle(self.view_pannel_frame, (self.show_fps_roi[0], 0), (self.pannel_size_w, 80), (255, 255, 255), -1)
        avg_dxnn_time = 1000 / (np.average(np.stack(dxnn_time_list)) / 1000000)
        avg_solution_time = 1000 / (np.average(np.stack(sol_time_list)) / 1000000)
        cv2.putText(self.view_pannel_frame,
                    "NPU : {:.2f} FPS".format(avg_dxnn_time),
                    (self.show_fps_roi[0], self.show_fps_roi[1] + 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 0),
                    1,
                    cv2.LINE_AA)
        cv2.putText(self.view_pannel_frame,
                    "APP : {:.2f} FPS".format(avg_solution_time),
                    (self.show_fps_roi[0], self.show_fps_roi[1] + 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 0),
                    1,
                    cv2.LINE_AA)

        # Update the last update time to the current time
        self.last_update_time_fps = current_time_fps


def main():
    global global_input
    global result_logits_np
    global global_quit

    SPECIAL_TOKEN = {
        "CLS_TOKEN": "<|startoftext|>",
        "SEP_TOKEN": "<|endoftext|>",
        "MASK_TOKEN": "[MASK]",
        "UNK_TOKEN": "[UNK]",
        "PAD_TOKEN": "[PAD]",
    }
    max_words = 32
    # Get Input Arguments
    args = get_args()

    # Get Device
    device = get_device()

    model_load_time_s = time.perf_counter_ns()

    dxnn_video_encoder = DXVideoEncoder(args.video_encoder_dxnn)

    token_embedder = ONNXModel(
        model_path=args.token_embedder_onnx
    )
    text_encoder = ONNXModel(
        model_path=args.text_encoder_onnx
    )

    model_load_time_e = time.perf_counter_ns()
    print("[TIME] Model Load : {} ns".format(model_load_time_e - model_load_time_s))

    gt_video_path_list = [
        "burning_car",
        "crowded_subway_platform",
        "elderly_woman_fallen_indoor",
        "kitchen_stove_fire",
        "men_fighting_indoors",
    ]
    
    # gt_video_path_list = [
    #     "fire_on_car",
    #     "dam_explosion_short",
    #     "violence_in_shopping_mall_short",
    #     "gun_terrorism_in_airport",
    #     "crowded_in_subway",
    #     "heavy_structure_falling",
    # ]

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
    ]

    gt_text_alarm_level = [
        [0.27, 0.29, 0.28],  # "The subway is crowded with people",
        [0.27, 0.29, 0.28],  # "People is crowded in the subway",

        [0.21, 0.25, 0.225],  # "Heavy objects are fallen",

        [0.23, 0.25, 0.24],  # "Physical confrontation occurs between two people",
        [0.22, 0.25, 0.23],  # "Violence with kicking and punching",

        [0.27, 0.29, 0.28],  # "Terrorism is taking place at the airport",
        [0.23, 0.26, 0.247],  # "Terrorist is shooting at people",

        [0.24, 0.28, 0.255],  # "The water is exploding out",
        [0.24, 0.28, 0.255],  # "The water is gushing out",

        [0.23, 0.26, 0.24],  # "Fire is coming out of the car",
        [0.24, 0.28, 0.26],  # "The car is exploding",
    ]

    video_thread = VideoThread(args.features_path, gt_video_path_list, gt_text_list)

    # text embedding vector 미리 준비 
    text_vector_list = []

    # 시간 측정
    run_dxnn_time_t = []
    run_sol_time_t = []
    for i in tqdm(range(len(gt_text_list))):
        gt_text_sample = gt_text_list[i]
        # Get Token's IDs,
        # 9 text ids : number of token ids
        # token to ids (using by "bpe_simple_vocab_16e6.txt.gz")
        # ex ) "some one talking about top ten movies of the year" 
        #      -> [some, one, talking, about, top, ten, movies, of, the, year]
        #      slice up to 30 words (SPECIAL_TOKEN["CAL_TOKEN"] + " " + orignal tokens[:30] + " " + SPECIAL_TOKEN["SEP_TOKEN"])
        #      -> [0, 1, 2, 3, 5, 6, 7, 8, 9, eof]
        gt_text_sample = gt_text_sample if len(gt_text_sample.split(" ")) < max_words - 1 else str.join(gt_text_sample.split(" ")[:max_words - 2])
        gt_text_sample = SPECIAL_TOKEN["CLS_TOKEN"] + " " + gt_text_sample + " " + SPECIAL_TOKEN["SEP_TOKEN"]
        gt_text_token_ids = ClipTokenizer().encode(gt_text_sample)
        raw_text_data = gt_text_token_ids

        text_input_mask = [1] * len(raw_text_data) + [0] * (
                max_words - len(raw_text_data)
        )

        text_input_ids = raw_text_data + [0] * (
                max_words - len(raw_text_data)
        )

        text_input_mask = torch.tensor(
            [text_input_mask],
        ).to(device, dtype=torch.float32)

        text_input_ids = torch.tensor(
            [text_input_ids],
        ).to(device)

        # [1, 32, 512]
        text_embedding = token_embedder(text_input_ids)

        # [1, 512]
        text_vectors = text_encoder([text_embedding, text_input_mask])

        text_vector_list.append(text_vectors)

    video_thread.start()
    video_path = video_thread.current_index
    j = 0
    result_logits_np = np.zeros((len(text_vector_list), 1, 1))
    print("Enter text to display on video (insert 'quit' to quit): ")
    while True:
        # initialize result_logits_np
        if video_thread.video_paths.__len__() <= 1 or video_thread.current_index != video_path:
            j = 0
            if len(text_vector_list) > 0:
                result_logits_np = np.zeros((len(text_vector_list), 1, 1))
            video_path = video_thread.current_index

        run_sol_time_s = time.perf_counter_ns()
        raw_video_data = video_thread.get_input_tensor()
        raw_video_mask_data = torch.ones(1, raw_video_data.shape[0])

        run_dxnn_time_s = time.perf_counter_ns()

        # 9 text ids : number of token ids
        # token to ids (using by "bpe_simple_vocab_16e6.txt.gz")
        ############################################ time
        video_pred = dxnn_video_encoder.run(raw_video_data).reshape(1, 512)
        run_dxnn_time_e = time.perf_counter_ns()
        run_dxnn_time_t.append(run_dxnn_time_e - run_dxnn_time_s)

        result_logits = []
        for k in range(len(text_vector_list)):
            ############################################ time
            retrieve_logits = _loose_similarity(text_vector_list[k], video_pred, raw_video_mask_data)
            result_logits.append(retrieve_logits)
        run_sol_time_e = time.perf_counter_ns()
        run_sol_time_t.append(run_sol_time_e - run_sol_time_s)

        if len(text_vector_list) > 0:
            result_logits_np += np.stack(result_logits)
            video_thread.update_text(gt_text_list, result_logits_np[:, 0, 0] / (j + 1), gt_text_alarm_level)
        else:
            video_thread.empty_text()

        # print("max retrieve_logits = {}, argmax = {}".format(result_logits_np[argmax_index]/(j+1), argmax_index))

        if global_input == "del":
            j = 0
            if len(text_vector_list) > 0:
                text_vector_list.pop(-1)
                result_logits_np = np.zeros((len(text_vector_list), 1, 1))
                gt_text_list.pop(-1)
                gt_text_alarm_level.pop(-1)
                video_thread.pop_text_vector(-1)
            global_input = ""
        elif global_input != "":
            gt_text_token = global_input if len(global_input.split(" ")) < max_words - 1 else str.join(global_input.split(" ")[:max_words - 2])
            gt_text_token = SPECIAL_TOKEN["CLS_TOKEN"] + " " + gt_text_token + " " + SPECIAL_TOKEN["SEP_TOKEN"]
            gt_text_token_ids = ClipTokenizer().encode(gt_text_token)
            raw_text_data = gt_text_token_ids
            text_input_mask = [1] * len(raw_text_data) + [0] * (
                    max_words - len(raw_text_data)
            )

            text_input_ids = raw_text_data + [0] * (
                    max_words - len(raw_text_data)
            )

            text_input_mask = torch.tensor(
                [text_input_mask],
            ).to(device, dtype=torch.float32)

            text_input_ids = torch.tensor(
                [text_input_ids],
            ).to(device)
            text_embedding = token_embedder(text_input_ids)
            text_vectors = text_encoder([text_embedding, text_input_mask])
            text_vector_list.append(text_vectors)
            j = 0
            result_logits_np = np.zeros((len(text_vector_list), 1, 1))
            video_thread.update_text_vector(global_input)
            gt_text_list.append(global_input)
            gt_text_alarm_level.append([0.23, 0.31, 0.26])
            global_input = ""
        j += 1

        if video_thread.released or global_quit:
            break
        video_thread.update_fps(run_dxnn_time_t, run_sol_time_t)

    # # print Profile
    # avg_t_text_tokenizer_list = np.average(np.stack(t_text_tokenizer_list))
    # avg_t_text_token_to_id = np.average(np.stack(t_text_token_to_id))
    # avg_t_text_embedding = np.average(np.stack(t_text_embedding))
    # avg_t_text_encoding = np.average(np.stack(t_text_encoding))

    avg_run_dxnn_time = np.average(np.stack(run_dxnn_time_t))
    avg_run_sol_time = np.average(np.stack(run_sol_time_t))

    print("\n")
    # print("** Average of text tokenizer = {} ns".format(avg_t_text_tokenizer_list))
    # print("** Average of text token to ids = {} ns".format(avg_t_text_token_to_id))
    print("** Average of dxnn running = {} ns".format(avg_run_dxnn_time))
    print("** Average of solution running = {} ns".format(avg_run_sol_time))
    print("\n")

    # print("** Average of get video encoded data for 30 frames = {} ns".format(avg_t_video_encoder))
    # print("** Average of calculation similarity = {} ns".format(avg_t_sim_value))
    # print("\n")


if __name__ == "__main__":
    text_thread = threading.Thread(target=insert_text_in_term)
    text_thread.daemon = True
    text_thread.start()

    main()

    text_thread.join()
