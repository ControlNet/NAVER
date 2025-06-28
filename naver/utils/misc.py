import gc
import torch

from hydra_vl4ai.util.console import logger


def clean_cache():
    gc.collect()
    torch.cuda.empty_cache()
    logger.debug("Cache Cleaned")


COLORS = {
    "red": (255, 0, 0),
    "grey": (128, 128, 128),
    "white": (128, 128, 128),
    "dark_blue": (0, 0, 255),
    "green": (0, 255, 0),
    "black": (0, 0, 120),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "violet": (127, 0, 255),
}

color_names = sorted(list(COLORS.keys()))
