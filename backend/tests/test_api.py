import pytest
import json
from app import create_app

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    app.config['TESTING'] = True
    
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123',
        'first_name': 'Test',
        'last_name': 'User'
    }

def test_index_endpoint(client):
    """Test root endpoint"""
    response = client.get('/')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['message'] == 'Flask API Backend'
    assert data['status'] == 'running'

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['status'] == 'healthy'

def test_api_info(client):
    """Test API info endpoint"""
    response = client.get('/api-info')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['name'] == 'Flask API Backend'
    assert 'endpoints' in data

def test_get_users_empty(client):
    """Test getting users when none exist"""
    response = client.get('/api/v1/users')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['success'] is True
    assert data['data'] == []
    assert data['count'] == 0

def test_create_user(client, sample_user_data):
    """Test creating a new user"""
    response = client.post('/api/v1/users',
                          data=json.dumps(sample_user_data),
                          content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert data['success'] is True
    assert data['data']['username'] == sample_user_data['username']
    assert data['data']['email'] == sample_user_data['email']
    assert 'password' not in data['data']

def test_create_user_duplicate_username(client, sample_user_data):
    """Test creating user with duplicate username"""
    # Create first user
    client.post('/api/v1/users',
                data=json.dumps(sample_user_data),
                content_type='application/json')
    
    # Try to create second user with same username
    sample_user_data['email'] = 'test2@example.com'
    response = client.post('/api/v1/users',
                          data=json.dumps(sample_user_data),
                          content_type='application/json')
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data['success'] is False
    assert 'Username ya existe' in data['error']

def test_get_user_by_id(client, sample_user_data):
    """Test getting a specific user by ID"""
    # Create user first
    create_response = client.post('/api/v1/users',
                                 data=json.dumps(sample_user_data),
                                 content_type='application/json')
    user_data = json.loads(create_response.data)
    user_id = user_data['data']['user_id']
    
    # Get user by ID
    response = client.get(f'/api/v1/users/{user_id}')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data['success'] is True
    assert data['data']['user_id'] == user_id
    assert data['data']['username'] == sample_user_data['username']

def test_get_user_not_found(client):
    """Test getting a user that doesn't exist"""
    response = client.get('/api/v1/users/999')
    data = json.loads(response.data)
    
    assert response.status_code == 404
    assert data['success'] is False
    assert data['error'] == 'User not found' 