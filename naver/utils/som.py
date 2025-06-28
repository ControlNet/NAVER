from typing import Literal
import numpy as np
from detectron2.data import MetadataCatalog

from ._visualizer import Visualizer


metadata = MetadataCatalog.get("coco_2017_train_panoptic")

def apply_som_for_two(image: np.ndarray, mask1, mask2, mask1_color, mask2_color, 
                           anno_mode: list[Literal["Mask", "Box", "Mark"]], label_mode="1", alpha=0.1) -> np.ndarray:
    visualizer = Visualizer(image, metadata)

    visualizer.draw_binary_mask_with_number(mask1, color=mask1_color,
                                            text="A", label_mode=label_mode, alpha=alpha, anno_mode=anno_mode)
    visualizer.draw_binary_mask_with_number(mask2, color=mask2_color,
                                            text="B", label_mode=label_mode, alpha=alpha, anno_mode=anno_mode)
    
    return visualizer.output.get_image()


def apply_som_for_one(image: np.ndarray, mask, mask_color, anno_mode: list[Literal["Mask", "Box", "Mark"]], 
                      label_mode="1", alpha=0.1) -> np.ndarray:
    visualizer = Visualizer(image, metadata)

    visualizer.draw_binary_mask_with_number(mask, color=mask_color,
                                            text="A", label_mode=label_mode, alpha=alpha, anno_mode=anno_mode)
    
    return visualizer.output.get_image()
