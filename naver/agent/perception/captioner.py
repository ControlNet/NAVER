from hydra_vl4ai.execution.image_patch import ImagePatch
from hydra_vl4ai.util.config import Config


from ..smb import NaverStateMemoryBank


class Captioner:
    """The Captioner in perception state."""

    def __init__(self, image_patch: ImagePatch, state_memory_bank: NaverStateMemoryBank) -> None:
        self.image_patch = image_patch
        self.state_memory_bank = state_memory_bank
        self._caption = None

    def __call__(self):
        if self._caption is None:
            self._caption = self.image_patch.forward(
                Config.base_config["vlm_caption_model"], 
                self.image_patch.cropped_image, 
                "Please describe the image in detail."
            )
            self.state_memory_bank.caption = self._caption
        return self._caption
