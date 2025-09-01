# Development Setup

## Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- Docker and Docker Compose (optional, for containerized development)
- Git

## Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env.local
# Edit .env.local with your configuration
```

4. Run the development server:
```bash
npm run dev
```

## Docker Development

For a containerized development environment:

```bash
docker-compose up --build
```

This will start both backend and frontend services with hot reloading enabled.

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Code Quality

### Backend
```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

### Frontend
```bash
# Format code
npm run format

# Lint
npm run lint

# Type checking
npm run type-check
```