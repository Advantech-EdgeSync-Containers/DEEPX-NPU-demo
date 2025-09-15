import numpy as np
import pytest
import torch
from PIL import Image
from dx_engine import InferenceEngine, InferenceOption

import clip

class DXVideoEncoder():
    def __init__(self, model_path: str):
        io = InferenceOption()
        io.set_use_ort(False)
        self.ie = InferenceEngine(model_path, io)
        self.cpu_offloading = False
        if "cpu_0" in self.ie.get_task_order():
            self.cpu_offloading = True
        
    def run(self, xs):
        ret = []
        xs = xs.numpy()
        for i in range(xs.shape[0]):
            x = xs[i:i+1]
            if not self.cpu_offloading:
                x = self.preprocess_numpy(x)
            x = np.ascontiguousarray(x)
            o = self.ie.run([x])[0]
            o = self.postprocess_numpy(o)
            o = torch.from_numpy(o)
            ret.append(o)
        z = torch.stack(ret)
        return z
        
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

def _loose_similarity(text_vectors, video_vectors):
    sequence_output, visual_output = (
            text_vectors.contiguous(),
            video_vectors.contiguous(),
        )
    visual_output = visual_output / visual_output.norm(dim=-1, keepdim=True)
    sequence_output = sequence_output / sequence_output.norm(dim=-1, keepdim=True)
    similarity = torch.matmul(sequence_output, visual_output.t())
    return similarity

@pytest.mark.parametrize('model_name', clip.available_models())
def test_consistency(model_name):
    device = "cpu"
    py_model, transform = clip.load(model_name, device=device)

    image = transform(Image.open("assets/CLIP/CLIP.png")).unsqueeze(0).to(device)
    text = clip.tokenize(["a diagram", "a dog", "a cat"]).to(device)
    with torch.no_grad():
        text_features = py_model.encode_text(text)
    
    dx_npu_model = DXVideoEncoder("assets/dxnn/clip_vit_250331.dxnn")
    
    preds = dx_npu_model.run(image)
    
    similarities = []
    for text_item in text_features:
        similarities.append(_loose_similarity(text_item, preds))
    
    # "a diagram"     , "a dog"         , "a cat"
    # tensor([0.2547]), tensor([0.2015]), tensor([0.1941])
    print(similarities)

if __name__ == "__main__" : 
    test_consistency("ViT-B/32")