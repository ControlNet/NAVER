import asyncio
import json
import os
import time
import tensorneko as N
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--image", type=str, required=True)
parser.add_argument("--query", type=str, required=True)
parser.add_argument("--base_config", type=str, required=True)
parser.add_argument("--model_config", type=str, required=True)
args = parser.parse_args()

from hydra_vl4ai.util.config import Config

Config.base_config_path = args.base_config
Config.model_config_path = args.model_config
Config.debug = False

from hydra_vl4ai.execution.toolbox import Toolbox
from hydra_vl4ai.util.console import logger
from naver import Naver


async def main():
    Toolbox.init(["naver.tool"])
    
    logger.info(f"Processing image: {args.image}")
    logger.info(f"Query: {args.query}")
    
    try:
        # Run NAVER inference
        result_entity = await Naver(args.image, args.query).run()
        
        # Extract and print result based on task type
        match Config.base_config.get("task", "grounding"):
            case "grounding":
                result = result_entity.bbox
                logger.info(f"Result bbox: {result}")
                
            case _:
                raise NotImplementedError(f"Task {Config.base_config.get('task')} not implemented for demo.")
        
        return result_entity
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(main())
    if result is None:
        logger.error("Processing failed.")
