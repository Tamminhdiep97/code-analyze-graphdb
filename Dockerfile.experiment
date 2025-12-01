# Use Ubuntu 22.04 as base image for compatibility
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    software-properties-common \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies for adding LLVM repository
RUN apt-get update && apt-get install -y \
    wget \
    software-properties-common \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Add LLVM repository for version 16
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
RUN add-apt-repository "deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-16 main"

# Install specific version 16.0.1 of LLVM/Clang
RUN apt-get update && apt-get install -y \
    llvm-16 \
    clang-16 \
    libclang-16-dev \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for default clang/llvm to version 16
RUN ln -s /usr/bin/clang-16 /usr/bin/clang && \
    ln -s /usr/bin/llvm-config-16 /usr/bin/llvm-config

# Set working directory
WORKDIR /app

# Copy requirements file
COPY experiment/requirements.txt .

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt

# Copy the entire experiment directory
COPY experiment/ ./experiment/

# Create a non-root user for security
RUN groupadd -r appuser && useradd -m -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser
