# <img src="assets/logo.svg" width="25"> NAVER: A Neuro-Symbolic Compositional Automaton for Visual Grounding with Explicit Logic Reasoning

<div align="center">
    <img src="assets/teaser.svg">
    <p></p>
</div>

<div align="center">
    <a href="https://github.com/ControlNet/NAVER/issues">
        <img src="https://img.shields.io/github/issues/ControlNet/NAVER?style=flat-square">
    </a>
    <a href="https://github.com/ControlNet/NAVER/network/members">
        <img src="https://img.shields.io/github/forks/ControlNet/NAVER?style=flat-square">
    </a>
    <a href="https://github.com/ControlNet/NAVER/stargazers">
        <img src="https://img.shields.io/github/stars/ControlNet/NAVER?style=flat-square">
    </a>
    <a href="https://github.com/ControlNet/NAVER/blob/master/LICENSE">
        <img src="https://img.shields.io/github/license/ControlNet/NAVER?style=flat-square">
    </a>
    <a href="https://arxiv.org/abs/2502.00372">
        <img src="https://img.shields.io/badge/arXiv-2502.00372-b31b1b.svg?style=flat-square">
    </a>
</div>

<div align="center">    
    <a href="https://pypi.org/project/naver/">
        <img src="https://img.shields.io/pypi/v/naver?style=flat-square">
    </a>
    <a href="https://pypi.org/project/naver/">
        <img src="https://img.shields.io/pypi/dm/naver?style=flat-square">
    </a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/pypi/pyversions/naver?style=flat-square"></a>
</div>


**This repo is the official implementation for the paper [NAVER: A Neuro-Symbolic Compositional Automaton for Visual Grounding with Explicit Logic Reasoning](https://arxiv.org/abs/2502.00372) in ICCV 2025.**


## Release

- [2025/06/28] 🔥 **NAVER** code is open sourced in GitHub.
- [2025/06/25] 🎉 **NAVER** paper is accepted by ICCV 2025.

## TODOs

We're working on the following TODOs:
- [x] GUI demo.
- [ ] Support more LLMs.
- [ ] Video demo & slides presentation.

## Docker (GUI Demo)

We provide a Docker image for the GUI demo.

```bash
docker run --runtime=nvidia --gpus=all -p <GUI-PORT>:8000 -e OPENAI_API_KEY=<OPENAI-API-KEY> -e AZURE_OPENAI_URL=<AZURE-OPENAI-URL> controlnet/naver:latest
```

The GUI will be available at `http://0.0.0.0:<GUI-PORT>`. See details below for more information.

## Installation

### Requirements

- Python >= 3.10
- conda

Please follow the instructions below to install the required packages and set up the environment.

### 1. Clone this repository.
```Bash
git clone https://github.com/ControlNet/NAVER
```

### 2. Setup conda environment and install dependencies. 

Option 1: Using [pixi](https://prefix.dev/) (recommended):
```Bash
pixi install
pixi shell
```

Option 2: Building from source (You may need to setup the CUDA and PyTorch manually):
```Bash
conda install conda-forge/label/rust_dev::rust=1.78 -c conda-forge -y
pip install "git+https://github.com/scallop-lang/scallop.git@f8fac18#egg=scallopy&subdirectory=etc/scallopy"
pip install -e .
```

### 3. Configure the environments

Edit the file `.env` or setup in CLI to configure the environment variables.

```
OPENAI_API_KEY=your-api-key  # if you want to use OpenAI LLMs
AZURE_OPENAI_URL= # if you want to use Azure OpenAI LLMs
OLLAMA_HOST=http://ollama.server:11434  # if you want to use your OLLaMA server for llama or deepseek
# do not change this TORCH_HOME variable
TORCH_HOME=./pretrained_models
```

### 4. Download the pretrained models
Run the scripts to download the pretrained models to the `./pretrained_models` directory. 

```Bash
python -m hydra_vl4ai.download_model --base_config config/refcoco.yaml --model_config config/model_config.yaml --extra_packages naver.tool
```

## Inference

You may need 28GB vRAM to run NAVER. Consider editing the file in `./config/model_config.yaml` to load the models in multiple GPUs.

### Inference with GUI

You need `nodejs` and `npm` to run the GUI demo. It will automatically compile and build the frontend.

The GUI will be available at `http://0.0.0.0:8000`.

```Bash
python demo_gui.py \
  --base_config <YOUR-CONFIG-DIR> \
  --model_config <MODEL-CONFIG-PATH>
```

![gui_preview](assets/gui_preview.webp)

### Inference with given one image and query
```Bash
python demo_cli.py \
  --image <IMAGE_PATH> \
  --query <QUERY> \
  --base_config <YOUR-CONFIG-DIR> \
  --model_config <MODEL-CONFIG-PATH>
```

The result will be printed in the console.

### Inference dataset

```Bash
python main.py \
  --data_root <YOUR-DATA-ROOT> \
  --base_config <YOUR-CONFIG-DIR> \
  --model_config <MODEL-CONFIG-PATH>
```

Then the inference results are saved in the `./result` directory for evaluation.

## Evaluation

```Bash
python evaluate.py --input <RESULT_JSONL_PATH>
```

The evaluation results will be printed in the console. Note the output from LLM is random, so the evaluation results may be slightly different from the paper.

## Citation
If you find this work useful for your research, please consider citing it.
```bibtex
@article{cai2025naver,
  title = {NAVER: A Neuro-Symbolic Compositional Automaton for Visual Grounding with Explicit Logic Reasoning},
  author = {Cai, Zhixi and Ke, Fucai and Jahangard, Simindokht and Garcia de la Banda, Maria and Haffari, Reza and Stuckey, Peter J. and Rezatofighi, Hamid},
  journal = {arXiv preprint arXiv:2502.00372},
  year = {2025},
}
```
