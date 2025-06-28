import asyncio
import json
import os
import tensorneko as N
import torch
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--data_root", type=str, required=True)
parser.add_argument("--base_config", type=str, required=True)
parser.add_argument("--model_config", type=str, required=True)
parser.add_argument("--result_folder", type=str, default="./result")
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()

from hydra_vl4ai.util.config import Config
Config.base_config_path = args.base_config
Config.model_config_path = args.model_config
Config.debug = args.debug

from hydra_vl4ai.execution.toolbox import Toolbox
from hydra_vl4ai.util.console import logger
from hydra_vl4ai.agent.llm import Cost
import exp_datasets
from naver import Naver


async def main():
    Toolbox.init(["naver.tool"])

    match Config.base_config["dataset"]:
        case "refcoco":
            dataset = exp_datasets.Refcoco(args.data_root, split="testA")
        case "refcoco+":
            dataset = exp_datasets.Refcoco(args.data_root, split="testA")
        case "refcocog":
            dataset = exp_datasets.Refer(args.data_root, "refcocog", "test", "bbox")
        case "refadv":
            dataset = exp_datasets.RefAdv(args.data_root)
        case _:
            raise ValueError("Invalid dataset")
        
    # output path
    Path(args.result_folder).mkdir(parents=True, exist_ok=True)
    save_path = Path(args.result_folder) / f"result.naver_{Config.base_config['dataset']}.jsonl"
    print(f"Saving results to {save_path}")
        
    # resume if the file exists
    completed = []
    if os.path.exists(save_path):
        prev_results = N.io.read.json.of_jsonl(str(save_path))
        if prev_results is not None:
            completed = [result["datum_id"] for result in prev_results]
        
    for i, (image_path, datum_id, query, ground_truth) in enumerate(dataset):
        if datum_id in completed:
            logger.info(f"Skipping {i+1}/{len(dataset)}")
            continue
            
        logger.info(f"Processing {i+1}/{len(dataset)}")
        
        try:
            result_entity = await Naver(image_path, query).run()

            match Config.base_config["task"]:
                case "grounding":
                    result = result_entity.bbox
                    
                    # Calculate IoU for evaluation
                    iou = N.evaluation.iou_2d(
                        torch.tensor([result]),
                        torch.tensor([ground_truth]),
                    )[0, 0].item()
                    
                    logger.info(f"Query: {query}, Result: {result}, Ground Truth: {ground_truth}, IoU: {iou}")
                    logger.info(f"Cost: {Cost.cost:.5f}, Input Tokens: {Cost.input_tokens}, Output Tokens: {Cost.output_tokens}")

                    result_data = {
                        "datum_id": datum_id,
                        "query": query,
                        "ground_truth": ground_truth,
                        "result": result,
                        "iou": iou
                    }
                    
                case _:
                    raise NotImplementedError(f"Task {Config.base_config['task']} is not implemented.")

        except Exception as e:
            # if the error occurs, we skip saving the result, but will be computed as a "runtime failure" in evaluation.
            logger.error(f"Error processing {datum_id}: {e}")
            import traceback
            traceback.print_exc()
            result_data = {
                "datum_id": datum_id,
                "query": query,
                "ground_truth": ground_truth,
                "result": None,
                "iou": None
            }

        with open(save_path, "a") as f:
            f.write(json.dumps(result_data) + "\n")
            f.flush()
                
if __name__ == "__main__":
    asyncio.run(main())
