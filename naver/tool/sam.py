import numpy as np
from hydra_vl4ai.util.misc import get_root_folder
from hydra_vl4ai.tool import module_registry, BaseModel
from segment_anything import sam_model_registry, SamPredictor
import torch
import tensorneko_util as N


@module_registry.register("sam")
class Sam(BaseModel):

    def __init__(self, gpu_number):
        super().__init__(gpu_number)
        path = get_root_folder() / "pretrained_models" / "sam" / "sam_vit_h_4b8939.pth"
        if not path.exists():
            self.prepare()
        self.model = sam_model_registry["vit_h"](checkpoint=str(path))
        self.model.eval().to(self.dev)

    @torch.no_grad()
    def forward(self, image: np.ndarray, bbox, use_image_patch_coord: bool = True) -> np.ndarray:
        left, lower, right, upper = bbox[:4]
        x0 = left
        x1 = right
        if use_image_patch_coord:
            y0 = image.shape[0] - upper
            y1 = image.shape[0] - lower
        else:
            y0 = lower
            y1 = upper
        bbox = [x0, y0, x1, y1]

        predictor = SamPredictor(self.model)
        predictor.set_image(image)
        masks, scores, _ = predictor.predict(
            box=np.array(bbox)
        )

        return masks[np.argmax(scores)]

    @classmethod
    def prepare(cls):
        path = get_root_folder() / "pretrained_models" / "sam"
        if not (path / "sam_vit_h_4b8939.pth").exists():
            N.util.download_file("https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", str(path))
