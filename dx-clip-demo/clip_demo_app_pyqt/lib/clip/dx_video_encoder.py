import numpy as np
import torch

from dx_engine import InferenceEngine
from dx_engine import InferenceOption


class DXVideoEncoder:
    def __init__(self, model_path: str):
        io = InferenceOption()
        io.set_use_ort(False)
        self.ie = InferenceEngine(model_path, io)
        self.cpu_offloaded = False
        if "cpu_0" in self.ie.get_task_order():
            self.cpu_offloaded = True

    def __del__(self):
        print("DXVideoEncoder 객체가 삭제됩니다!")  # 가비지 컬렉션 확인용

    # def register_callback(self, func):
    #     self.ie.register_callback(func)
    
    def run_async(self, x, args):
        x = x.numpy()
        if not self.cpu_offloaded:
            x = self.preprocess_numpy(x)
        x = np.ascontiguousarray(x)
        request_id = self.ie.run_async([x], args)
        return request_id

    def wait(self, request_id):
        o = self.ie.Wait(request_id)[0]
        o = self.postprocess_numpy(o)
        o = torch.from_numpy(o)
        return o
    
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
