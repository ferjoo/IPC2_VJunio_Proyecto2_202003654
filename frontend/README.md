# Django Frontend

This is the Django frontend application for Project 2.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
```

2. Activate the virtual environment:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Project Structure

- `main/` - Main Django app
- `frontend_project/` - Django project settings
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)
- `manage.py` - Django management script

## Features

- Modern responsive UI with Bootstrap
- API endpoints for backend communication
- CORS configuration for cross-origin requests
- REST Framework integration

## API Endpoints

- `GET /` - Home page
- `GET /api/` - API test endpoint 