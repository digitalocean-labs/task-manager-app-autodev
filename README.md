# Task Manager Application

A production-ready task management application built with Flask, PostgreSQL, and deployed on DigitalOcean App Platform.

## Tutorial Overview

### 1. Introduction
In today's fast-paced development landscape, automating every possible step is key. This tutorial demonstrates how to harness the power of AI agents, specifically through the Claude Code CLI, to automate the entire application development lifecycle. By setting up MCP servers for GitHub, DigitalOcean App Platform, and DigitalOcean PostgreSQL, your AI assistant can understand complex instructions and interact with real-world services to build and deploy a production-ready application.

**Goal**: To showcase maximum agent autonomy using Claude Code, triggering an entire development lifecycle with a single, high-level instruction. The agent will handle everything except the final, human-driven production approval.

**Live Application Link**: https://task-manager-app-production-xp4k6.ondigitalocean.app/login  
**Github Repository**: https://github.com/RithishRamesh-dev/task-manager-app-autodev/tree/staging

### Architecture Overview
![Complete App Lifecycle Development](images/Complete%20App%20Lifecycle%20Development%20.jpeg)

### 2. Prerequisites
- DigitalOcean Account with API tokens
- GitHub Account with Personal Access Token
- Node.js & npm (Version 18+)
- Git
- Claude Code CLI: `npm install -g claude-code`

### 3. Workflow Stages
- **Phase 1**: Project Foundation & Task Decomposition
- **Phase 2**: Development Workflow (Feature Implementation)
- **Phase 3**: Staging → Production Promotion

### 4. Key Technologies
- **MCP (Model Context Protocol)**: Standard for AI-tool communication
- **Claude Code**: Command-line interface for Claude with MCP integration
- **DigitalOcean App Platform**: PaaS for streamlined deployment
- **DigitalOcean Managed PostgreSQL**: Fully managed database service

### 5. Setup & Configuration

**Add MCP Servers:**
```bash
# GitHub MCP Server

Follow the link for Github MCP Setup here: https://docs.google.com/document/d/1s5qSqiCBi13hDleyWEt1WNoGn5kiUJJGULmGysk9jEs/edit?usp=sharing

# DigitalOcean App Platform MCP Server
claude mcp add digitalocean-app-mcp \
  -e DIGITALOCEAN_API_TOKEN=YOUR_DO_APP_PAT \
  -- npx @digitalocean/mcp

# DigitalOcean PostgreSQL MCP Server (optional)
claude mcp add digitalocean-postgres-mcp \
  -e DIGITALOCEAN_API_TOKEN=YOUR_DO_DB_PAT \
  -- npx @digitalocean/mcp

# Verify setup
claude mcp list
```

## About This Project

This application was created following the tutorial **"Complete App Lifecycle Development: Claude Code & MCP Automation"** by Rithish Ramesh. The tutorial demonstrates how to harness the power of AI agents through the Claude Code CLI to automate the entire application development lifecycle, from initial project setup to production deployment.

The tutorial showcases maximum agent autonomy using Claude Code with MCP (Model Context Protocol) servers for GitHub, DigitalOcean App Platform, and DigitalOcean PostgreSQL. This enables an AI assistant to understand complex instructions and interact with real-world services to build and deploy production-ready applications using simple natural language prompts.

## Features

- **User Authentication**: Secure JWT-based authentication system
- **Project Management**: Create and manage projects with team collaboration
- **Task Management**: Full CRUD operations for tasks with status tracking
- **Real-time Updates**: WebSocket integration for live collaboration
- **Role-based Access**: Project owners, admins, members, and viewers
- **Responsive Design**: Mobile-first responsive web interface

## Tech Stack

- **Backend**: Flask, SQLAlchemy, Flask-Migrate
- **Database**: PostgreSQL
- **Authentication**: JWT (Flask-JWT-Extended)
- **Real-time**: Flask-SocketIO
- **Frontend**: Flask Templates with Bootstrap/Tailwind
- **Deployment**: DigitalOcean App Platform
- **CI/CD**: GitHub Actions

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (for WebSocket support)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RithishRamesh-dev/task-manager-app-autodev.git
cd task-manager-app-autodev
```

2. Create virtual environment:
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
# Edit .env with your database and other configuration
```

5. Initialize database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. Create admin user:
```bash
flask create-admin
```

7. Run the application:
```bash
flask run
```

## Database Schema

### Users Table
- User authentication and profile information
- Password hashing with bcrypt
- Active status tracking

### Projects Table  
- Project organization and management
- Owner relationship to users
- Soft delete with is_active flag

### Tasks Table
- Core task management functionality
- Status tracking (pending, in_progress, completed, cancelled)
- Priority levels (low, medium, high, critical)
- Assignment and creation tracking

### Task Comments Table
- Comments and updates on tasks
- User attribution and timestamps

### Project Members Table
- Many-to-many relationship for project access
- Role-based permissions (owner, admin, member, viewer)

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/profile` - Get user profile

### Projects
- `GET /api/projects` - List user projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Tasks
- `GET /api/tasks` - List tasks with filtering
- `POST /api/tasks` - Create new task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

## Development

### Running Tests
```bash
pytest
pytest --cov=app  # With coverage
```

### Code Quality
```bash
black .  # Format code
flake8  # Lint code
```

### Database Migrations
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

## Deployment

The application is configured for deployment on DigitalOcean App Platform with automatic CI/CD via GitHub Actions.

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `REDIS_URL`: Redis connection string

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
