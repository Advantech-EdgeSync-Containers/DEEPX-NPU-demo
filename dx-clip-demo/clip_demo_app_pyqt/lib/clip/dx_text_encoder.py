import torch
import onnxruntime
import os


class ONNXModel(torch.nn.Module):
    def __init__(self, model_path: str):
        super().__init__()
        assert os.path.isfile(model_path), f"can't load model file at {model_path}"
        self.model = onnxruntime.InferenceSession(model_path)
        self.output_names = [x.name for x in self.model.get_outputs()]
    
    def forward(self, x):
        if len(self.model.get_inputs()) != 1:
            inputs = {}
            for i in range(len(self.model.get_inputs())):
                if abs(len(self.model.get_inputs()[i].shape) - len(x[i].shape)) == 1 :
                    x[i] = x[i][0,...]
                inputs[self.model.get_inputs()[i].name] = x[i].cpu().numpy()
        else:
            x = x.cpu().numpy()
            inputs = {self.model.get_inputs()[0].name: x}
        pred = self.model.run(self.output_names, inputs)
        if isinstance(pred, list):
            import numpy as np
            pred = np.stack(pred)
        return torch.Tensor(pred, device="cpu")
