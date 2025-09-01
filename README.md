# QuickCrop - Photo Crop/Resize Web Tool

QuickCrop is an intelligent photo cropping and resizing web application designed for e-commerce product photography. It uses computer vision to automatically detect faces and poses, ensuring perfect crops for different aspect ratios.

## Key Features

- **Smart Detection**: Automatic face and pose detection using MediaPipe
- **Four Preset Modes**: 
  - 1:1 Square - Perfect for social media
  - 9:16 Vertical - Stories and reels format
  - 16:9 Horizontal - Landscape/banner format
  - 2:3 Portrait - Standard portrait orientation
- **Batch Processing**: Process multiple images at once
- **Image Optimization**: Automatic PNG optimization using oxipng and pngquant
- **RESTful API**: Clean API for integration with other services

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: React with TypeScript and Next.js
- **Computer Vision**: MediaPipe for face/pose detection
- **Image Processing**: OpenCV, Pillow
- **Containerization**: Docker with multi-stage builds

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd QuickCrop

# Start the application
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Manual Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
QuickCrop/
├── backend/          # FastAPI backend application
├── frontend/         # React frontend application
├── docker/           # Docker-related files
├── docs/             # Documentation
├── .taskmaster/      # Task management (development)
└── docker-compose.yml
```

## Documentation

- [Development Setup](docs/development/setup.md)
- [API Documentation](docs/api/endpoints.md)
- [Deployment Guide](docs/deployment/docker.md)
- [Architecture Overview](docs/architecture/overview.md)

## Development

This project uses Task Master for development workflow management. See [CLAUDE.md](CLAUDE.md) for AI-assisted development guidelines.

## Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]