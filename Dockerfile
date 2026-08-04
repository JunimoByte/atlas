FROM python:3.8-slim

# System dependencies for Qt6 / PyQt6 on headless Linux
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
    libxcb1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY . /app

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -e ".[dev]" && \
    pip install "PyQt6>=6.0"

# Headless Qt mode
ENV QT_QPA_PLATFORM=offscreen

CMD ["pytest", "src/atlas/tests/unit", "-q"]