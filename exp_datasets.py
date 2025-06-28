import json
import numpy as np
import pandas as pd
import os
import cv2
from torch.utils.data import Dataset
from rich.progress import track
from _refer import REFER
from PIL import Image
from pycocotools import mask as mask_util


class Refcoco(Dataset):

    def __init__(self, data_root: str, split: str = "testA") -> None:
        super().__init__()
        self.data_root = data_root
        # open test dataset
        with open(os.path.join(self.data_root, f"{split}.json")) as refcocotrain:
            ref_coco_train_data = json.load(refcocotrain)

        ref_df = pd.DataFrame(
            columns=['img_name', 'sent_id', 'sub_query', 'ground_true'])

        for img_set in track(ref_coco_train_data):

            # load each data
            img_name = img_set['img_name']

            ground_true = img_set['bbox']

            for sub in img_set['sentences']:

                # sub_query (content/question)
                sub_query = sub['sent']
                # query_id
                sent_id = sub['sent_id']

                new_row_ = pd.DataFrame.from_records(
                    [{'img_name': 'train2014/'+img_name, 'sent_id': sent_id, 'sub_query': sub_query, 'ground_true': ground_true}])
                ref_df = pd.concat([ref_df, new_row_], ignore_index=True)
        self.metadata = ref_df
    
    def __getitem__(self, idx):
        row = self.metadata.iloc[idx]
        return os.path.join(self.data_root, row.img_name), row.sent_id, row.sub_query, row.ground_true
    
    def __len__(self):
        return len(self.metadata)


class RefAdv(Dataset):
    def __init__(self, data_root_folder):
        """
        Initialize the RefCOCOg-Adv dataset.

        Args:
            data_root_folder (str): Path to the dataset root folder.
            transform (callable, optional): Optional transform to be applied on a sample.
        """
        self.data_root_folder = data_root_folder
        self.annotations_path = os.path.join(data_root_folder, 'refcocog_adv_annotations.json')
        self.image_folder = os.path.join(data_root_folder, 'train2014')

        # Load annotations
        with open(self.annotations_path, 'r') as f:
            self.annotations = json.load(f)

        self.keys = list(self.annotations.keys())

    def __len__(self):
        return len(self.annotations)

    def __getitem__(self, idx):
        """
        Retrieve a single sample from the dataset.

        Args:
            idx (int): Index of the sample.

        Returns:
            dict: A dictionary containing the image, bounding boxes, and descriptions.
        """
        row = self.annotations[self.keys[idx]]
        img_path = os.path.join(self.image_folder, row['img_file_name'])

        bbox_candidates_map = json.loads(row['bbox_candidates_map'])
        most_confused_bbox = self._convert_bbox_to_xyxy(bbox_candidates_map[row['most_confused_bbox_number']])
        return img_path, None, row['most_confused_bbox_GT_desc'], most_confused_bbox

    @staticmethod
    def _convert_bbox_to_xyxy(bbox):
        x_min, y_min, width, height = bbox
        x_max = x_min + width
        y_max = y_min + height
        return [x_min, y_min, x_max, y_max]

class Refer(Dataset):
    def __init__(self, data_root: str, dataset: str, split: str, label_type: str = "mask") -> None:
        super().__init__()

        assert label_type in ["mask", "bbox"]

        split_type = "unc" if dataset != "refcocog" else "umd"

        self.data_root = data_root
        self.image_root = "images/mscoco/images/train2014" if dataset != "refclef" else "images/saiapr_tc-12"

        self.refer_api = REFER(data_root, dataset, split_type)
        self.refs = {k: v for k, v in self.refer_api.Refs.items() if v["split"] == split}
        self.refs_ids = sorted(list(self.refs.keys()))
        self.label_type = label_type

    def __getitem__(self, index: int):
        ref_id = self.refs_ids[index]
        annotation = self.refer_api.refToAnn[ref_id]
        ref = self.refer_api.Refs[ref_id]

        file = os.path.join(self.data_root, self.image_root, self.refer_api.Imgs[ref["image_id"]]["file_name"])

        w, h = Image.open(file).size
        
        mask = np.zeros((h, w), dtype=np.uint8)

        if type(annotation["segmentation"][0]) is list:
            for seg in annotation["segmentation"]:
                segmentation = np.array(seg).reshape((-1, 2)).astype(np.int32)
                mask = cv2.fillPoly(mask, [segmentation], 1)
        else:
            # segmentation = np.array(annotation["segmentation"]).reshape((-1, 2)).astype(np.int32)
            # mask = cv2.fillPoly(mask, [segmentation], 1)
            # mask used for refclef
            mask = mask_util.decode(annotation["segmentation"])
            # (H, W, 1) -> (H, W)
            mask = mask[:, :, 0]

        if self.label_type == "mask":
            return file, ref["sentences"][0]["sent_id"], ref["sentences"][0]["sent"], mask > 0
        elif self.label_type == "bbox":
            x, y, w, h = cv2.boundingRect(mask)
            bbox = [x, y, x + w, y + h]
            return file, ref["sentences"][0]["sent_id"], ref["sentences"][0]["sent"], bbox
    
    def __len__(self):
        return len(self.refs_ids)
