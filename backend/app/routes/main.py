from flask import Blueprint, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Flask API Backend',
        'version': '1.0.0',
        'status': 'running'
    })

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is running successfully'
    })

@main_bp.route('/api-info')
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Flask API Backend',
        'version': '1.0.0',
        'description': 'A RESTful API built with Flask',
        'endpoints': {
            'main': '/',
            'health': '/health',
            'api_info': '/api-info',
            'api_v1': '/api/v1'
        }
    }) 