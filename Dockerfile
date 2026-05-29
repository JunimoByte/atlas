FROM python:3.8-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    libdbus-1-3 \
    libgl1 \
    libglib2.0-0 \
    libfontconfig1 \
    libxrender1 \
    libxext6 \
    libsm6 \
    libx11-6 \
    libxkbcommon0 \
    libegl1 \
    libopengl0 \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml setup.py /app/

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -e ".[dev]"

COPY . /app

# Headless Qt mode
ENV QT_QPA_PLATFORM=offscreen

CMD ["pytest", "src/atlas/tests/unit", "-q"]