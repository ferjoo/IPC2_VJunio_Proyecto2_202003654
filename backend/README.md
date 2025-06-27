# Flask API Backend

A RESTful API backend built with Flask, featuring user management with sparse matrix storage, file uploads, and comprehensive testing.

## Features

- **Flask Framework**: Modern Python web framework
- **Sparse Matrix Storage**: Efficient in-memory storage using sparse matrices
- **Marshmallow**: Data serialization and validation
- **CORS Support**: Cross-origin resource sharing enabled
- **Password Hashing**: Secure password storage with bcrypt
- **Comprehensive Testing**: Unit tests with pytest
- **Environment Configuration**: Flexible configuration management
- **File Upload System**: XML and CSV file processing
- **JWT Authentication**: Secure token-based authentication

## Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py          # Main routes (health, info)
│   │   └── api.py           # API v1 routes
│   ├── models/
│   │   ├── __init__.py
│   │   └── user_storage.py  # Sparse matrix user storage
│   ├── services/
│   │   ├── __init__.py
│   │   └── user_service.py  # Business logic layer
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py       # Utility functions
│       └── sparse_matrix.py # Sparse matrix implementation
├── tests/
│   ├── __init__.py
│   └── test_api.py          # API tests
├── requirements.txt         # Python dependencies
├── run.py                  # Application entry point
├── env.example             # Environment variables template
└── README.md               # This file
```

## Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**:
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:5001`

## API Endpoints

### Main Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /api-info` - Detailed API information

### Authentication

- `POST /api/v1/login` - User login
- `POST /api/v1/logout` - User logout

### User Management

- `GET /api/v1/users` - Get all users
- `GET /api/v1/users/{id}` - Get user by ID
- `POST /api/v1/users` - Create new user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### File Management

- `POST /api/v1/upload` - Upload XML files
- `POST /api/v1/schedule` - Upload schedule files
- `POST /api/v1/grades/upload` - Upload grades XML

### Reports

- `GET /api/v1/reports/grades` - Generate grade reports
- `GET /api/v1/storage/stats` - Get storage statistics (admin only)

### Example API Usage

#### Create a User
```bash
curl -X POST http://localhost:5001/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

#### Login
```bash
curl -X POST http://localhost:5001/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123"
  }'
```

#### Get Storage Statistics
```bash
curl -X GET http://localhost:5001/api/v1/storage/stats \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Storage System

The application uses a **sparse matrix storage system** instead of a traditional database:

### Key Features
- **In-Memory Storage**: All data stored in memory using sparse matrices
- **Efficient**: Only stores non-zero elements, saving memory
- **Fast Access**: O(1) access to user data
- **No Database**: No SQL or database dependencies
- **Scalable**: Supports up to 10,000 users efficiently

### Matrix Structure
- **Users Matrix**: Stores user attributes (user_id × attributes)
- **Index Matrices**: Fast lookups by username and email
- **Automatic Cleanup**: Removes deleted users from memory

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=app
```

## Environment Variables

Copy `env.example` to `.env` and configure:

- `SECRET_KEY`: Flask secret key
- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Debug mode
- `JWT_SECRET_KEY`: JWT signing key
- `JWT_ACCESS_TOKEN_EXPIRES`: Token expiration time
- `CORS_ORIGINS`: Allowed CORS origins

## Development

### Adding New Features

1. **New Storage Models**: Add to `app/models/` using sparse matrices
2. **Business Logic**: Implement in `app/services/`
3. **API Endpoints**: Add routes in `app/routes/api.py`
4. **Tests**: Add test cases in `tests/`

### Performance Considerations

- **Memory Usage**: Monitor sparse matrix density
- **User Limits**: System designed for up to 10,000 users
- **Persistence**: Data is lost on server restart (add file persistence if needed)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License. 