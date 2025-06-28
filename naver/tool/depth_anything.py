import torch
import numpy as np
from hydra_vl4ai.tool import module_registry, BaseModel
import torch
from transformers import pipeline
from torchvision.transforms import functional as T


@module_registry.register("depth_anything_v2")
class DepthAnythingV2(BaseModel):
    def __init__(self, gpu_number=0):
        super().__init__(gpu_number)
        # Model options: MiDaS_small, DPT_Hybrid, DPT_Large
        self.pipe = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Large-hf", device=f"cuda:{gpu_number}")

    @torch.no_grad()
    def forward(self, image: torch.Tensor):
        """Estimate depth map"""
        image = T.to_pil_image(image)
        prediction = np.array(self.pipe(image)["depth"])
        return 1 - prediction / 255
    
    @classmethod
    def prepare(cls):
        """Download the model"""
        pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Large-hf")
        return cls
