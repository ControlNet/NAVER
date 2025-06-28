from hydra_vl4ai.execution.image_patch import ImagePatch


class EntityDetector:
    """The Entity Detector in perception state."""

    def __init__(self, image_patch: ImagePatch):
        self.image_patch = image_patch

    def __call__(self, interested_entities: list[str]) -> dict[str, list[ImagePatch]]:
        interested_entities_patch = self.image_patch.find(interested_entities)
        return interested_entities_patch
