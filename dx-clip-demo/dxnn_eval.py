import argparse
import os
import sys
from collections import deque
from typing import Literal

import cv2
import onnx
import numpy as np
import pandas as pd
import torch
project_path = os.path.dirname(__file__)
sys.path.append(project_path)
from clip_demo_app_pyqt.lib.clip.dx_text_encoder import ONNXModel

from clip.simple_tokenizer import SimpleTokenizer as ClipTokenizer
from tqdm import tqdm
from dx_engine import InferenceEngine

def get_args():
    # fmt: off
    parser = argparse.ArgumentParser(description="Generate Similarity Matrix from ONNX files")
    
    # Dataset Path Arguments
    parser.add_argument("--val_csv", type=str, default="assets/data/sampled/MSRVTT_JSFUSION_test_10.csv", help="CSV file path of caption labels")
    parser.add_argument("--features_path", type=str, default="assets/data/sampled/MSRVTT_Videos_10", help="Videos directory")
    
    # Dataset Configuration Arguments
    parser.add_argument("--max_words", type=int, default=20, help="")
    parser.add_argument("--feature_framerate", type=int, default=1, help="")
    parser.add_argument("--max_frames", type=int, default=100, help="")
    parser.add_argument("--eval_frame_order", type=int, default=0, choices=[0, 1, 2], help="Frame order, 0: ordinary order; 1: reverse order; 2: random order.")
    parser.add_argument("--slice_framepos", type=int, default=0, choices=[0, 1, 2], help="0: cut from head frames; 1: cut from tail frames; 2: extract frames uniformly.")
    
    # Model Path Arguments
    parser.add_argument("--token_embedder_onnx", type=str, default="assets/onnx/embedding_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for token embedder")
    parser.add_argument("--text_encoder_onnx", type=str, default="assets/onnx/textual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for text encoder")
    parser.add_argument("--video_encoder_onnx", type=str, default="assets/onnx/visual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx", help="ONNX file path for video encoder")
    parser.add_argument("--torch_model", type=str, default="assets/pth/clip4clip_msrvtt_b128_ep5.pth", help="pth file path for torch model")
    
    return parser.parse_args()
    # fmt: on


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif sys.platform.startswith("darwin"):
        return "mps"
    else:
        return "cpu"


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


def postprocess_numpy(x: np.ndarray) -> np.ndarray:
    assert len(x.shape) == 3
    x = x[:, 0]
    x = x / np.linalg.norm(x, axis=-1, keepdims=True)
    return x


def postprocess_torch(x: torch.Tensor) -> torch.Tensor:
    assert len(x.shape) == 3
    x = x[:, 0]
    x = x / torch.norm(x, dim=-1, keepdim=True)
    return x


def clip4clip_onnx_sim_matrix(
    device: Literal["cuda", "cpu", "mps"],
    video_encoder: ONNXModel,
    text_encoder: ONNXModel,
    token_embedder: ONNXModel,
    torch_model: ClipTorchModel,
    dataset_args: argparse.Namespace,
):

    def _fill_zero_dequeue(frames_deque: deque, height: int, width: int, channel: int, dtype: type):
        zero_frame = np.zeros((height, width, channel), dtype=dtype)
        for _ in range(frames_deque.maxlen):
            frames_deque.append(zero_frame)
        return frames_deque

    def _encode_video_with_sliding_window(
        video: cv2.VideoCapture,
        frame_skip: int,
        temporal_size: int,
        clip4clip_main: Clip4Clip,
        clip4clip_model: CLIP4Clip,
    ):
        # Validate Video File
        fps = video.get(cv2.CAP_PROP_FPS)
        assert fps > 0, "Invalid Video File"

        # Prepare Visual Vector Placeholder
        vis_vector_list = []
        vid_mask_list = []

        # Prepare Frame Queue
        frames_deque = deque(maxlen=temporal_size)
        frames_deque = _fill_zero_dequeue(
            frames_deque=frames_deque,
            height=int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            width=int(video.get(cv2.CAP_PROP_FRAME_WIDTH)),
            channel=3,
            dtype=np.uint8,
        )

        # Read Frames
        frame_count = 0
        while True:
            success, frame = video.read()

            # Terminate If No Frame Anymore
            if not success:
                break

            # Skip Frame
            if frame_count % frame_skip != 0:
                frame_count += 1
                continue

            # Collect Frame
            frames_deque.append(frame)
            input_frames_chunk = np.array(frames_deque)

            # Preprocess the Input Frame Chunk and Captions
            #   Inputs
            #       - input_frames_chunk.shape: [Temporal size, Height, Width, Channel]
            #   Outputs
            #       - vid_preprocessed: [Num chunks=1, Temporal size, Channel, Height, Width]
            #       - vid_mask: [Num chunks=1, Temporal size]
            vid_preprocessed, vid_mask = clip4clip_main.video_preprocess(video=input_frames_chunk)

            # Encode Video
            #   Inputs:
            #       - vid_preprocessed.shape: [Num chunks=1, Temporal size, Channel, Height, Width]
            #       - vid_preprocessed.shape(after reshaping): [Num frames, Channel, Height, Width]
            #   Ouputs:
            #       - visual_output: [Num frames, 512]
            #       - visual_output(after unsqueezing): [1, Num frames, 512]
            batch, frame, channel, height, width = vid_preprocessed.shape
            vid_preprocessed = vid_preprocessed.reshape(batch * frame, channel, height, width)

            outputs = []
            for i in range(len(vid_preprocessed)):
                x = vid_preprocessed[i : i + 1]
                x = x.numpy()
                x = preprocess_numpy(x)
                x = np.ascontiguousarray(x)
                o = video_encoder.run([x])[0]
                o = postprocess_numpy(o)
                o = torch.from_numpy(o)
                outputs.append(o)
                
            visual_output = torch.cat(outputs, dim=0)
            visual_output = visual_output.unsqueeze(0)

            assert visual_output.shape == (1, torch_model.config.temporal_size, 512)

            # Mean Pool the Video Vector
            #   Inputs
            #       - visual_output(after unsqueezing): [1, Num frames, 512]
            #       - vid_mask: [1, Temproal size]
            #   Outputs
            #       - vis_vector: [1, 512]
            vis_vector = clip4clip_model._mean_pooling_for_similarity_visual(
                visual_output=visual_output, video_mask=vid_mask
            )

            assert vis_vector.shape == (1, 512)

            vis_vector_list.append(vis_vector)
            vid_mask_list.append(vid_mask)

            # End of Loop
            frame_count += 1

        return vis_vector_list, vid_mask_list

    # Import `Clip4Clip` class to Utilize its Functions
    print("Clip4Clip Main")
    clip4clip_main = Clip4Clip(config=torch_model.config)

    # Import `CLIP4Clip` class to Utilize its Functions
    print("Clip4Clip Model")
    state_dict = torch.load(torch_model.config.model_path, map_location=device)
    clip4clip_model = CLIP4Clip(clip_state_dict=state_dict, task_cfg=torch_model.config)

    # Prepare Input Video and Captions
    msrvtt_testset = MSRVTT_DataLoader(
        csv_path=dataset_args.val_csv,
        features_path=dataset_args.features_path,
        max_words=dataset_args.max_words,
        feature_framerate=dataset_args.feature_framerate,
        tokenizer=dataset_args.tokenizer,
        max_frames=dataset_args.max_frames,
        frame_order=dataset_args.eval_frame_order,
        slice_framepos=dataset_args.slice_framepos,
    )
    vid_filenames = get_video_filenames_list(dataloader=msrvtt_testset)
    vid_ext = os.listdir(dataset_args.features_path)[0].split(".")[-1]
    vid_filepath_list = [f"{dataset_args.features_path}/{vid_filename}.{vid_ext}" for vid_filename in vid_filenames]
    input_txt_list = get_captions_list(dataloader=msrvtt_testset)

    # Preprocess Captions
    #   Inputs
    #       - len(dummy_input_txt_list): Num captions
    #   Outputs
    #       - txt_ids.shape: [Num captions, Max words]
    #       - txt_mask.shape: [Num captions, Max words]
    txt_ids, txt_mask = clip4clip_main.text_preprocess(texts=input_txt_list)
    # Convert dtype to match the precision to the ONNX file
    txt_mask = txt_mask.to(dtype=torch.float32)

    # Encode Texts
    print("Encode Texts!")
    print("Token Embedding")
    token_embedding = token_embedder(d=txt_ids)
    print("Text Encoding")
    txt_vectors = text_encoder(d=[token_embedding, txt_mask])

    # Process All Videos
    print("Process All Videos!")
    num_caps = txt_vectors.shape[0]
    tensor_sim_matrix = torch.empty((num_caps, 0), device=device)
    for vid_filepath in tqdm(vid_filepath_list, desc="Calculating Similarity Matrix"):
        # Encode a Video Windows
        #   Inputs
        #       - `input_vid`: cv2.VideoCapture
        #   Outputs
        #       - `vis_vector_list`: [vis_vector(Window 0), vis_vector(Window 1), ...]
        #       - `vid_mask_list`: [vid_mask(Window 0), vid_mask(Window 1), ...]
        #       - Window n: frame n - frame (n + temporal size - 1)
        #           - Example: The window assuming the temporal size is 12
        #               - Window 0: frame 0 - frame 11
        #               - Window 1: frame 1 - frame 12
        #               - ...
        vis_vector_list, vid_mask_list = _encode_video_with_sliding_window(
            video=cv2.VideoCapture(vid_filepath),
            frame_skip=torch_model.config.frame_skip,
            temporal_size=torch_model.config.temporal_size,
            clip4clip_main=clip4clip_main,
            clip4clip_model=clip4clip_model,
        )

        # Calculate Similarity Scores
        sim_scores_for_video = torch.empty((num_caps, 0), device=device)  # Initialize
        for vis_vector, vid_mask in zip(vis_vector_list, vid_mask_list):
            # Inputs
            #   - txt_vectors.shape: [Num captions, 512]
            #   - vis_vector.shape: [1, 512]
            #   - vid_mask: [1, Temporal Size]
            # Outputs
            #   - sim_scores_for_window.shape: [Num captions, 1]
            #   - sim_scores_for_video.shape: [Num captions, Num windows]
            similarity_scores_for_window = clip4clip_model._loose_similarity(
                sequence_output=txt_vectors,
                visual_output=vis_vector,
                video_mask=vid_mask,
                sim_header=clip4clip_main.config.sim_header,
            )
            sim_scores_for_video = torch.cat((sim_scores_for_video, similarity_scores_for_window), dim=1)

        # Aggregate Similarity Scores into Representitive One Value(Score) for Each Video
        #   Inputs
        #       - sim_scores_for_video.shape: [Num captions, Num windows]
        #   Outputs
        #       - sim_score_for_video.shape: [Num captions, 1]
        sim_score_for_video = sim_scores_for_video.max(dim=1).values.unsqueeze(1)

        # Collect Similarity Scores for All Videos
        #   Inputs
        #       - sim_matrix.shape: [Num captions, Num Videos Processed]
        #       - sim_score_for_video.shape: [Num captions, 1]
        tensor_sim_matrix = torch.cat((tensor_sim_matrix, sim_score_for_video), dim=1)

    # Save Similarity Matrix
    np_sim_matrix = tensor_sim_matrix.cpu().numpy()

    video_filename_list = [os.path.basename(video_filepath) for video_filepath in vid_filepath_list]
    df_sim_matrix = pd.DataFrame(
        np_sim_matrix,
        columns=video_filename_list,
        index=input_txt_list,
    )
    sim_matrix_filepath = "outputs/sim_matrix.xlsx"
    os.makedirs(os.path.dirname(sim_matrix_filepath), exist_ok=True)
    df_sim_matrix.to_excel(sim_matrix_filepath)
    print(df_sim_matrix)
    print(f"Saved Similarity Matrix: {sim_matrix_filepath}")

    # Compute and Save Metrics
    tv_metrics = compute_metrics(np_sim_matrix)
    series_tv_metrics = pd.DataFrame(tv_metrics).drop(labels="cols", axis=1).iloc[0]
    print(series_tv_metrics)
    tv_metrics_filepath = "outputs/metrics.xlsx"
    os.makedirs(os.path.dirname(tv_metrics_filepath), exist_ok=True)
    series_tv_metrics.to_excel(tv_metrics_filepath)
    print(f"Saved Metrics: {tv_metrics_filepath}")


def main():
    # Get Input Arguments
    args = get_args()

    # Get Device
    device = get_device()

    # Set up ONNX Models (Used for Inference)
    video_encoder = InferenceEngine(model_path=args.video_encoder_onnx)
    text_encoder = ONNXModel(model_path=args.text_encoder_onnx)
    token_embedder = ONNXModel(model_path=args.token_embedder_onnx)

    # Set up Torch Model (Only Used for Configurations)
    torch_model_config = T2VRetConfig(
        model_path=args.torch_model,
        device=device,
    )
    torch_model = ClipTorchModel(target_task=1, target_model=0, config=torch_model_config)

    # Set up Dataset Arguments
    print("Set up dataset Arguments")
    dataset_args = argparse.Namespace(
        val_csv=args.val_csv,
        features_path=args.features_path,
        max_words=args.max_words,
        feature_framerate=args.feature_framerate,
        tokenizer=ClipTokenizer(),
        max_frames=args.max_frames,
        eval_frame_order=args.eval_frame_order,
        slice_framepos=args.slice_framepos,
    )

    # Inference with ONNX and Generate Similarity Matrix
    clip4clip_onnx_sim_matrix(
        device=device,
        video_encoder=video_encoder,
        text_encoder=text_encoder,
        token_embedder=token_embedder,
        torch_model=torch_model,
        dataset_args=dataset_args,
    )


if __name__ == "__main__":
    main()