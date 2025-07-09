import numpy as np
import torch

from hydra_vl4ai.util.config import Config
from hydra_vl4ai.util.console import logger
from hydra_vl4ai.util.misc import get_root_folder
from hydra_vl4ai.tool._base import BaseModel, module_registry
import tensorneko_util as N
from PIL import Image
from torchvision.ops import box_convert
from transformers import AutoProcessor, AutoModelForCausalLM
        

@module_registry.register("florence2")
class Florence2(BaseModel):
    model_name = "microsoft/Florence-2-large-ft"

    def __init__(self, gpu_number=0):
        super().__init__(gpu_number)

        self.device = self.dev
        self.torch_dtype = torch.float16
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, torch_dtype=self.torch_dtype, trust_remote_code=True).to(self.device)
        self.processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
        self.task_prompt = '<OPEN_VOCABULARY_DETECTION>'
        
    @torch.no_grad()
    def forward(self, input_image, grounding_caption, box_threshold=None, text_threshold=0.25):
        if box_threshold is None:
            box_threshold = Config.base_config["florence2_threshold"]
        input_image = np.asarray(input_image.permute(1,2,0)*255, dtype=np.uint8)

        img_pil = Image.fromarray(input_image)
        re_width, re_height = img_pil.size

        prompt = self.task_prompt + grounding_caption

        inputs = self.processor(text=prompt, images=img_pil, return_tensors="pt").to(self.device, self.torch_dtype)
        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3
        )
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = self.processor.post_process_generation(generated_text, task=self.task_prompt, image_size=(re_width, re_height))

        # transfer boxes to sam-format 
        transfered_boxes = np.array(parsed_answer[self.task_prompt]["bboxes"])
        transfered_boxes = transfered_boxes.reshape(transfered_boxes.shape[0], 4)[:,[0,3,2,1]]
        transfered_boxes[:,1] = re_height - transfered_boxes[:,1]
        transfered_boxes[:,3] = re_height - transfered_boxes[:,3]
        
        confidences = torch.ones(len(transfered_boxes))  # confidence is not provided by the model
        return np.concatenate([transfered_boxes, confidences[:, None].numpy()], axis=1)
    
    @classmethod
    def prepare(cls):
        """Download the model"""
        AutoModelForCausalLM.from_pretrained(cls.model_name, torch_dtype=torch.float32, trust_remote_code=True)
        AutoProcessor.from_pretrained(cls.model_name, trust_remote_code=True)
        return cls
