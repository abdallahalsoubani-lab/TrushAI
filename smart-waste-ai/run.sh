#!/bin/bash

#######################################
# Smart Waste Monitoring - Run Script
#######################################
#
# Quick start script for running the application
# Supports both Docker and local development modes
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO] ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}[OK] ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARN] ${1}${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] ${1}${NC}"
}

print_failed() {
    echo -e "${RED}[FAILED] ${1}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Docker daemon is running
docker_daemon_running() {
    if command_exists docker; then
        docker info >/dev/null 2>&1
    else
        return 1
    fi
}

# Function to run with Docker
run_docker() {
    print_info "Starting Smart Waste Monitoring with Docker Compose..."

    # Check if Docker is installed
    if ! command_exists docker-compose && ! command_exists docker; then
        print_error "Docker not found. Please install Docker and Docker Compose."
        print_warning "Falling back to local development mode..."
        run_local
        return
    fi

    # Check if Docker daemon is running
    if ! docker_daemon_running; then
        print_error "Docker daemon is not running. Please start Docker Desktop."
        print_warning "Falling back to local development mode..."
        run_local
        return
    fi

    # Check if .env exists, create from example if not
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file. Please review and update if needed."
        fi
    fi

    # Run database migrations
    print_info "Running database migrations..."
    docker-compose run --rm backend alembic upgrade head || print_warning "Migration may have failed, continuing..."

    # Start services
    print_info "Starting services..."
    docker-compose up -d

    print_success "Services started!"
    echo ""
    print_info "Access points:"
    echo "  " Dashboard:  http://localhost:3000"
    echo "  " Backend:    http://localhost:8000"
    echo "  " API Docs:   http://localhost:8000/docs"
    echo "  " PostgreSQL: localhost:5432"
    echo ""
    print_info "View logs:       docker-compose logs -f"
    print_info "Stop services:   docker-compose down"
    print_info "Restart:         docker-compose restart"
}

# Function to run locally (development mode)
run_local() {
    print_info "Starting Smart Waste Monitoring in local development mode..."

    # Get project root
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$PROJECT_ROOT"

    # Check Python
    PYTHON_CMD=""
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.10+"
        exit 1
    fi

    # Check Node.js
    if ! command_exists node; then
        print_error "Node.js not found. Please install Node.js 18+"
        exit 1
    fi

    # Setup Python virtual environment
    VENV_DIR="$PROJECT_ROOT/venv"
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi

    # Activate virtual environment
    print_info "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"

    # Add project root to PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # Install Python dependencies
    print_info "Installing Python dependencies..."
    pip install --upgrade pip --quiet >/dev/null 2>&1
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet >/dev/null 2>&1
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi

    # Create data directories
    print_info "Creating data directories..."
    mkdir -p data/videos data/frames data/results/visualizations data/results/debug data/results/mistakes
    print_success "Data directories ready"

    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file. Using SQLite by default."
        fi
    fi

    # Skip database migrations for now (if no database setup)
    # print_info "Running database migrations..."
    # cd backend
    # alembic upgrade head || print_warning "Migration may have failed, continuing..."
    # cd ..

    # Start backend in background
    print_info "Starting backend server..."
    $PYTHON_CMD backend/main.py > .backend.log 2>&1 &
    BACKEND_PID=$!

    # Wait for backend to start
    sleep 3

    # Check if backend is running
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_error "Backend failed to start. Check .backend.log for details"
        cat .backend.log
        exit 1
    fi

    # Start dashboard
    print_info "Starting dashboard..."
    cd dashboard
    if [ ! -d "node_modules" ]; then
        print_info "Installing npm dependencies..."
        npm install --silent >/dev/null 2>&1
    fi
    npm run dev > ../.dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    cd ..

    print_success "Services started!"
    echo ""
    print_info "Access points:"
    echo "  Dashboard:  http://localhost:3000"
    echo "  Backend:    http://localhost:8000"
    echo "  API Docs:   http://localhost:8000/docs"
    echo ""
    print_info "Logs:"
    echo "  Backend:    .backend.log"
    echo "  Dashboard:  .dashboard.log"
    echo ""
    print_info "Running in background. Press Ctrl+C to stop."

    # Wait for processes
    wait $BACKEND_PID $DASHBOARD_PID
}

# Function to run locally with migrations (walkscan mode)
run_walkscan() {
    print_info "Starting Smart Waste Monitoring (walkscan) in local development mode..."

    # Get project root
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$PROJECT_ROOT"

    # Check Python
    PYTHON_CMD=""
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_failed "Python not found. Please install Python 3.10+"
        exit 1
    fi

    # Check Node.js
    if ! command_exists node; then
        print_failed "Node.js not found. Please install Node.js 18+"
        exit 1
    fi

    # Setup Python virtual environment
    VENV_DIR="$PROJECT_ROOT/venv"
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    fi

    # Activate virtual environment
    print_info "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"

    # Add project root to PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # Install Python dependencies
    print_info "Installing Python dependencies..."
    pip install --upgrade pip --quiet >/dev/null 2>&1
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet >/dev/null 2>&1
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found"
    fi

    # Create data directories
    print_info "Creating data directories..."
    mkdir -p data/videos data/frames data/results/visualizations data/results/debug data/results/mistakes data/results/captures
    print_success "Data directories ready"

    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file. Using SQLite by default."
        fi
    fi

    # Run database migrations
    print_info "Running database migrations..."
    cd backend
    if ! "$PROJECT_ROOT/venv/bin/alembic" -c alembic.ini upgrade head; then
        print_failed "Database migrations failed"
        exit 1
    fi
    cd ..
    print_success "Migrations complete"

    # Start backend in background
    print_info "Starting backend server..."
    $PYTHON_CMD backend/main.py > .backend.log 2>&1 &
    BACKEND_PID=$!

    # Wait for backend to start
    sleep 3

    # Check if backend is running
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_failed "Backend failed to start. Check .backend.log for details"
        cat .backend.log
        exit 1
    fi

    # Start dashboard
    print_info "Starting dashboard..."
    cd dashboard
    if [ ! -d "node_modules" ]; then
        print_info "Installing npm dependencies..."
        npm install --silent >/dev/null 2>&1
    fi
    npm run dev > ../.dashboard.log 2>&1 &
    DASHBOARD_PID=$!
    cd ..

    print_success "Services started!"
    echo ""
    print_info "Access points:"
    echo "  Dashboard:  http://localhost:3000"
    echo "  Backend:    http://localhost:8000"
    echo "  API Docs:   http://localhost:8000/docs"
    echo ""
    print_info "Logs:"
    echo "  Backend:    .backend.log"
    echo "  Dashboard:  .dashboard.log"
    echo ""
    print_info "Running in background. Press Ctrl+C to stop."

    # Wait for processes
    wait $BACKEND_PID $DASHBOARD_PID
}

# Function to stop services
stop_services() {
    print_info "Stopping services..."

    if command_exists docker-compose || command_exists docker; then
        docker-compose down 2>/dev/null || true
    fi

    # Kill local processes
    pkill -f "python backend/main.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true

    print_success "Services stopped."
}

# Function to show status
show_status() {
    print_info "Service Status:"
    echo ""

    if command_exists docker-compose || command_exists docker; then
        docker-compose ps 2>/dev/null || print_warning "Docker services not running"
    else
        # Check local processes
        if pgrep -f "python backend/main.py" > /dev/null; then
            print_success "Backend: Running"
        else
            print_warning "Backend: Not running"
        fi

        if pgrep -f "next dev" > /dev/null; then
            print_success "Dashboard: Running"
        else
            print_warning "Dashboard: Not running"
        fi
    fi
}

# Function to show logs
show_logs() {
    if command_exists docker-compose || command_exists docker; then
        docker-compose logs -f
    else
        print_error "Log viewing only available for Docker mode"
        print_info "For local mode, check terminal output or log files"
    fi
}

# Function to run database migrations
run_migrations() {
    print_info "Running database migrations..."

    if command_exists docker-compose || command_exists docker; then
        docker-compose run --rm backend alembic upgrade head
    else
        # Get project root
        PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        VENV_DIR="$PROJECT_ROOT/venv"
        if [ ! -d "$VENV_DIR" ]; then
            print_failed "Virtual environment not found. Run ./run.sh start walkscan first."
            exit 1
        fi
        cd backend
        if ! "$PROJECT_ROOT/venv/bin/alembic" -c alembic.ini upgrade head; then
            print_failed "Database migrations failed"
            exit 1
        fi
        cd ..
    fi

    print_success "Migrations complete!"
}

# Function to show help
show_help() {
    echo "Smart Waste Monitoring - Run Script"
    echo ""
    echo "Usage: ./run.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo '  start [docker|local|walkscan]  Start the application (default: docker)'
    echo "  stop                  Stop all services"
    echo "  restart               Restart all services"
    echo "  status                Show service status"
    echo '  logs                  Show service logs (Docker only)'
    echo "  migrate               Run database migrations"
    echo "  help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh start        # Start with Docker"
    echo "  ./run.sh start local  # Start in local development mode"
    echo "  ./run.sh start walkscan  # Start local mode + migrations"
    echo "  ./run.sh stop         # Stop all services"
    echo "  ./run.sh logs         # View logs"
}

# Main script logic
case "${1:-start}" in
    start)
        if [ "${2:-docker}" == "local" ]; then
            run_local
        elif [ "${2:-docker}" == "walkscan" ]; then
            run_walkscan
        else
            run_docker
        fi
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        run_docker
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    migrate)
        run_migrations
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
