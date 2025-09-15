#!/bin/bash
python dxnn_eval.py \
    --val_csv assets/data/full/MSRVTT_JSFUSION_test.csv \
    --features_path assets/data/full/MSRVTT_Videos \
    --token_embedder_onnx assets/onnx/embedding_f32_op14_clip4clip_msrvtt_b128_ep5.onnx \
    --text_encoder_onnx assets/onnx/textual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx \
    --video_encoder_onnx assets/dxnn/clip_vit_250331.dxnn \
    --torch_model assets/pth/clip4clip_msrvtt_b128_ep5.pth