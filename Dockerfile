###############################################
# Stage 1: Build the SvelteKit GUI (Node)
###############################################
FROM node:22-bookworm-slim AS gui-builder

WORKDIR /app/gui

# Install GUI deps with good cache utilization
COPY gui/package.json gui/package-lock.json ./
RUN npm ci

# Build the GUI
COPY gui/ .
ENV PUBLIC_BASE_URL=
RUN npm run build


###############################################
# Stage 2: Runtime with CUDA + Pixi
###############################################
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies commonly needed by CV/ML stacks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    pkg-config \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libsm6 \
 && rm -rf /var/lib/apt/lists/*

# Install Pixi (https://pixi.sh)
RUN curl -fsSL https://pixi.sh/install.sh | bash -s -- -y \
 && echo 'export PATH="/root/.pixi/bin:$PATH"' >> /root/.bashrc
ENV PATH="/root/.pixi/bin:${PATH}"

WORKDIR /app

RUN mkdir -p /app/gui
# Copy prebuilt GUI from the builder image to avoid building at runtime
COPY --from=gui-builder /app/gui/build /app/gui/build

# Configure local model caches (kept inside the project tree)
ENV HF_HOME=/app/pretrained_models/hf
ENV TORCH_HOME=/app/pretrained_models/torch
ENV OLLAMA_HOST=http://localhost:11434
ENV OPENAI_API_KEY=
ENV AZURE_OPENAI_URL=
ENV CONFIG=config/refcoco.yaml
ENV MODEL_CONFIG=config/model_config.yaml
ENV PYTHONUNBUFFERED=1

# Resolve and install the environment
COPY config /app/config
COPY module_repos /app/module_repos
COPY pretrained_models /app/pretrained_models
COPY naver /app/naver
COPY demo_gui.py /app/demo_gui.py
COPY pixi.toml /app/pixi.toml
COPY pyproject.toml /app/pyproject.toml
COPY setup.py /app/setup.py
COPY LICENSE /app/LICENSE
COPY README.md /app/README.md

# remove the rust depdency from pixi.toml
RUN sed -i '/rust = { version = "==1\.78\.0\.dev20240310", channel = "conda-forge\/label\/rust_dev" }/d' pixi.toml

# install rust-nighly 1.80 seperately
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain nightly-2024-08-15
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pixi install -v && pixi clean cache -y

# Expose the GUI port
EXPOSE 8000

# Run the FastAPI GUI (serves prebuilt SvelteKit under /)
CMD pixi run python demo_gui.py --base_config "$CONFIG" --model_config "$MODEL_CONFIG"
