from hydra_vl4ai.util.console import logger

try:
    import segment_anything
except ImportError:
    logger.info("SAM not installed. Skipping.")
    pass
else:
    from .sam import Sam

from .depth_anything import DepthAnythingV2
from .florence import Florence2
from .internvl import InternVL2
