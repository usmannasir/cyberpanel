# CyberPanel Development Setup

This guide will help you set up CyberPanel in a Docker development environment.

## Prerequisites

- Docker
- Docker Compose
- Git

## Quick Start

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/getsuperhost/cyberpanel.git
   cd cyberpanel
   ```

2. **Run the development setup script**:
   ```bash
   ./setup-dev.sh
   ```

   This script will:
   - Build the Docker containers
   - Set up the database
   - Run migrations
   - Collect static files
   - Optionally create a superuser

3. **Access the application**:
   - CyberPanel: http://localhost:8000
   - phpMyAdmin: http://localhost:8080
   - Database: localhost:3306

## Manual Setup

If you prefer to set up manually:

1. **Build and start containers**:
   ```bash
   docker-compose -f docker-compose.dev.yml up --build -d
   ```

2. **Run database migrations**:
   ```bash
   docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py migrate
   ```

3. **Collect static files**:
   ```bash
   docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py collectstatic --noinput
   ```

4. **Create superuser** (optional):
   ```bash
   docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py createsuperuser
   ```

## Development Workflow

### Starting the Environment
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Stopping the Environment
```bash
docker-compose -f docker-compose.dev.yml down
```

### Viewing Logs
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### Accessing the Django Shell
```bash
docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py shell
```

### Running Tests
```bash
docker-compose -f docker-compose.dev.yml exec cyberpanel python manage.py test
```

### Making Code Changes
The development setup uses volume mounting, so changes to your local files will be reflected immediately in the container. The Django development server will auto-reload when you make changes.

## Services

- **cyberpanel**: Main Django application (port 8000)
- **db**: MariaDB database (port 3306)
- **phpmyadmin**: Database management interface (port 8080)

## Configuration

### Environment Variables
The development environment uses the following environment variables (defined in `.env.dev`):

- `DEBUG=True`: Enables Django debug mode
- `DJANGO_SETTINGS_MODULE=CyberCP.settings_dev`: Uses development settings
- Database connection variables for MySQL/MariaDB

### Database
- **Host**: db (Docker service name)
- **Port**: 3306
- **Database**: cyberpanel
- **User**: cyberpanel
- **Password**: SLTUIUxqhulwsh

## File Structure

```
cyberpanel/
├── Dockerfile.dev              # Development Docker image
├── docker-compose.dev.yml      # Development Docker Compose
├── setup-dev.sh               # Development setup script
├── .env.dev                   # Development environment variables
├── CyberCP/
│   ├── settings_dev.py        # Development Django settings
│   └── settings.py            # Production Django settings
└── ...                        # Other CyberPanel files
```

## Troubleshooting

### Container Won't Start
Check the logs:
```bash
docker-compose -f docker-compose.dev.yml logs cyberpanel
```

### Database Connection Issues
Ensure the database container is running:
```bash
docker-compose -f docker-compose.dev.yml ps
```

### Permission Issues
The containers run as a non-root user. If you encounter permission issues, check the file permissions in your local directory.

### Port Conflicts
If ports 8000, 8080, or 3306 are already in use, modify the port mappings in `docker-compose.dev.yml`.

## Production Deployment

⚠️ **Important**: This setup is for development only. For production:

1. Use `CyberCP/settings.py` instead of `CyberCP/settings_dev.py`
2. Set `DEBUG=False`
3. Use a proper secret key
4. Configure proper database credentials
5. Set up proper static file serving
6. Configure HTTPS

## Contributing

When contributing to CyberPanel:

1. Make your changes in the local directory
2. Test them in the Docker development environment
3. Ensure all tests pass
4. Follow the existing code style and conventions

## Support

For issues related to the development setup, check:
- Docker and Docker Compose documentation
- CyberPanel community forums
- GitHub issues

For CyberPanel-specific issues, visit the [CyberPanel Community Forums](https://community.cyberpanel.net).
