# QuickCrop Documentation

## Overview
QuickCrop is a photo crop/resize web tool designed for e-commerce product photography. It automatically detects faces and poses to crop images perfectly for different aspect ratios.

## Documentation Structure

- **api/** - API endpoint documentation
- **architecture/** - System architecture and design decisions
- **deployment/** - Deployment guides and configurations
- **development/** - Developer setup and contribution guidelines

## Features

### Four Preset Crop Modes
1. **1:1 Square** - Centered on face with 20% padding
2. **9:16 Vertical** - Upper body composition with face at top third
3. **16:9 Horizontal** - Wider crop with face/torso centered
4. **2:3 Portrait** - Standard portrait orientation

### Key Technologies
- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React with TypeScript
- **Computer Vision**: MediaPipe for face and pose detection
- **Image Processing**: OpenCV, Pillow
- **Optimization**: oxipng, pngquant for PNG optimization
- **Containerization**: Docker with multi-stage builds

## Quick Start

See [development/setup.md](development/setup.md) for detailed setup instructions.

## API Documentation

See [api/endpoints.md](api/endpoints.md) for API reference.

## Deployment

See [deployment/docker.md](deployment/docker.md) for deployment instructions.