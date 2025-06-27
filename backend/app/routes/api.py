from flask import Blueprint, request, jsonify
from app.services.user_service import UserService
from app.models.schedule_storage import ScheduleStorage
from marshmallow import ValidationError
import jwt
import datetime
from flask import current_app
from functools import wraps
import xml.etree.ElementTree as ET
import os
from werkzeug.utils import secure_filename
from app.models.course_storage import CourseStorage
from app.models.student_storage import StudentStorage
from app.models.assignment_storage import AssignmentStorage

api_bp = Blueprint('api', __name__)
user_service = UserService()
schedule_storage = ScheduleStorage()
course_storage = CourseStorage()
student_storage = StudentStorage()
assignment_storage = AssignmentStorage()

# Helper: JWT encode/decode

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def decode_token(token):
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print(f"DEBUG: login_required called for endpoint: {request.endpoint}")  # Debug log
        auth_header = request.headers.get('Authorization')
        print(f"DEBUG: Authorization header: {auth_header}")  # Debug log
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid token'}), 401
        token = auth_header.split(' ')[1]
        print(f"DEBUG: Token extracted: {token[:20]}...")  # Debug log
        user_id = decode_token(token)
        print(f"DEBUG: Decoded user_id: {user_id}")  # Debug log
        if not user_id:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        return f(auth_user_id=user_id, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid token'}), 401
        token = auth_header.split(' ')[1]
        user_id = decode_token(token)
        if not user_id:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        # Check if user is admin using the new storage system
        user = user_service.get_user_by_id(user_id)
        print(f"DEBUG: User ID: {user_id}, User data: {user}")  # Debug log
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        is_admin = user.get('is_admin')
        print(f"DEBUG: is_admin value: {is_admin}, type: {type(is_admin)}")  # Debug log
        
        if not is_admin:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        return f(user_id=user_id, *args, **kwargs)
    return decorated

@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not (username or email) or not password:
        return jsonify({'success': False, 'error': 'Username/email and password required'}), 400
    
    # Try username first, then email
    user = None
    if username:
        user = user_service.authenticate_user(username, password)
    elif email:
        # For email login, we need to find the user first
        user_data = user_service.get_user_by_email(email)
        if user_data:
            user = user_service.authenticate_user(user_data['username'], password)
    
    if user:
        token = generate_token(user['user_id'])
        return jsonify({'success': True, 'token': token, 'user': user}), 200
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@api_bp.route('/logout', methods=['POST'])
@login_required
def logout(auth_user_id):
    # For JWT, logout is handled client-side (token discard). Optionally, implement token blacklist.
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

# Storage Statistics Endpoint
@api_bp.route('/storage/stats', methods=['GET'])
@admin_required
def get_storage_stats(user_id):
    """Get storage statistics for the sparse matrix system"""
    try:
        user_stats = user_service.get_storage_stats()
        schedule_stats = schedule_storage.get_matrix_stats()
        
        combined_stats = {
            'users': user_stats,
            'schedules': schedule_stats
        }
        
        return jsonify({
            'success': True,
            'data': combined_stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# File Upload Endpoint
@api_bp.route('/upload', methods=['POST'])
@login_required
def upload_file(auth_user_id):
    """Upload XML files containing academic information"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.xml'):
        return jsonify({'success': False, 'error': 'Only XML files are allowed'}), 400
    
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Parse XML to validate structure
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            # You can add specific XML validation here based on your schema
            
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'filename': filename,
                'file_size': os.path.getsize(file_path)
            }), 200
            
        except ET.ParseError as e:
            os.remove(file_path)  # Remove invalid file
            return jsonify({'success': False, 'error': f'Invalid XML file: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error uploading file: {str(e)}'}), 500

# User Management (Admin only)
@api_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users_admin(user_id):
    """Get all users (admin only)"""
    try:
        users = user_service.get_all_users()
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Schedule Management
@api_bp.route('/schedule', methods=['POST'])
@login_required
def upload_schedule(auth_user_id):
    """Upload schedule XML file for tutors (bulk schedule upload)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Only accept XML files for schedules
    if not file.filename.endswith('.xml'):
        return jsonify({'success': False, 'error': 'Only XML files are allowed for schedules'}), 400
    
    # Get tutor_id from form data (optional, defaults to user_id)
    tutor_id = request.form.get('tutor_id', auth_user_id)
    try:
        tutor_id = int(tutor_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'tutor_id must be a valid integer'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'schedules')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Parse XML to extract schedule information
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Validate root element
            if root.tag != 'horarios':
                raise ValueError("Root element must be 'horarios'")
            
            schedules_to_create = []
            processed_courses = 0
            invalid_courses = 0
            
            # Process each course
            for curso in root.findall('curso'):
                codigo = curso.get('codigo')
                if not codigo:
                    invalid_courses += 1
                    continue
                
                # Get the text content
                text_content = curso.text.strip() if curso.text else ""
                
                # Extract time ranges using regex
                import re
                horario_pattern = r'HorarioI:\s*(\d{1,2}:\d{2})\s*HorarioF:\s*(\d{1,2}:\d{2})'
                matches = re.findall(horario_pattern, text_content)
                
                if matches:
                    for horario_inicio, horario_fin in matches:
                        schedule_data = {
                            'codigo_curso': codigo,
                            'horario_inicio': horario_inicio,
                            'horario_fin': horario_fin,
                            'tutor_id': tutor_id
                        }
                        schedules_to_create.append(schedule_data)
                    processed_courses += 1
                else:
                    invalid_courses += 1
            
            # Store schedules in sparse matrix storage
            created_schedules = schedule_storage.bulk_create_schedules(schedules_to_create)
            
            return jsonify({
                'success': True,
                'message': 'Schedule file processed and stored successfully',
                'filename': filename,
                'processed_by': auth_user_id,
                'tutor_id_used': tutor_id,
                'summary': {
                    'total_courses_processed': processed_courses,
                    'total_schedules_created': len(created_schedules),
                    'invalid_courses': invalid_courses
                },
                'schedules': created_schedules
            }), 200
            
        except ET.ParseError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': f'Invalid XML file: {str(e)}'}), 400
        except ValueError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': str(e)}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error uploading schedule: {str(e)}'}), 500

# Schedule Management Endpoints
@api_bp.route('/schedules', methods=['GET'])
@login_required
def get_all_schedules(auth_user_id):
    """Get all schedules"""
    try:
        schedules = schedule_storage.get_all_schedules()
        return jsonify({
            'success': True,
            'data': schedules,
            'count': len(schedules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/schedules/course/<codigo_curso>', methods=['GET'])
@login_required
def get_schedules_by_course(auth_user_id, codigo_curso):
    """Get schedules by course code"""
    try:
        schedules = schedule_storage.get_schedules_by_course(codigo_curso)
        return jsonify({
            'success': True,
            'data': schedules,
            'count': len(schedules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/schedules/tutor/<int:tutor_id>', methods=['GET'])
@login_required
def get_schedules_by_tutor(auth_user_id, tutor_id):
    """Get schedules by tutor ID"""
    try:
        schedules = schedule_storage.get_schedules_by_tutor(tutor_id)
        return jsonify({
            'success': True,
            'data': schedules,
            'count': len(schedules)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Grades Upload
@api_bp.route('/grades/upload', methods=['POST'])
@login_required
def upload_grades(auth_user_id):
    """Upload grades XML file for student development in tutor's course"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.xml'):
        return jsonify({'success': False, 'error': 'Only XML files are allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'grades')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Parse XML to validate grades structure
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Basic validation - you can enhance this based on your XML schema
            if root.tag != 'grades':
                raise ValueError("Root element must be 'grades'")
            
            # Count students in the file
            students = root.findall('.//student')
            
            return jsonify({
                'success': True,
                'message': 'Grades file uploaded successfully',
                'filename': filename,
                'students_count': len(students),
                'uploaded_by': auth_user_id,
                'upload_date': datetime.datetime.utcnow().isoformat()
            }), 200
            
        except ET.ParseError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': f'Invalid XML file: {str(e)}'}), 400
        except ValueError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': str(e)}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error uploading grades: {str(e)}'}), 500

# Grade Reports
@api_bp.route('/reports/grades', methods=['GET'])
@login_required
def get_grade_reports(auth_user_id):
    """Generate grade summary report after tutor uploads grades"""
    try:
        # Get query parameters for filtering
        course_id = request.args.get('course_id')
        tutor_id = request.args.get('tutor_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Here you would query the sparse matrix storage for grade reports
        # For now, return a mock report structure
        
        report_data = {
            'report_id': f'RPT_{datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
            'generated_by': auth_user_id,
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'filters': {
                'course_id': course_id,
                'tutor_id': tutor_id,
                'date_from': date_from,
                'date_to': date_to
            },
            'summary': {
                'total_students': 25,
                'average_grade': 85.5,
                'highest_grade': 98,
                'lowest_grade': 72,
                'passing_rate': 92.0
            },
            'grade_distribution': {
                'A': 8,
                'B': 12,
                'C': 3,
                'D': 1,
                'F': 1
            }
        }
        
        return jsonify({
            'success': True,
            'data': report_data
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error generating report: {str(e)}'}), 500

@api_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        users = user_service.get_all_users()
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user_by_id(auth_user_id, user_id):
    """Get specific user by ID with full name and registro personal"""
    try:
        # First try to find as tutor (user)
        user = user_service.get_user_by_id(user_id)
        
        if user:
            # It's a tutor/user
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return jsonify({
                'success': True,
                'data': {
                    'user_id': user.get('user_id'),
                    'registro_personal': user.get('username'),
                    'full_name': full_name,
                    'email': user.get('email'),
                    'is_admin': user.get('is_admin'),
                    'is_active': user.get('is_active'),
                    'user_type': 'tutor'
                }
            }), 200
        
        # If not found as user, try as student
        student = student_storage.get_student_by_id(user_id)
        
        if student:
            # It's a student
            return jsonify({
                'success': True,
                'data': {
                    'student_id': student.get('student_id'),
                    'registro_personal': student.get('carnet'),
                    'full_name': student.get('nombre'),
                    'is_active': student.get('is_active'),
                    'is_admin': student.get('is_admin'),
                    'user_type': 'student'
                }
            }), 200
        
        # User not found
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user = user_service.create_user(data)
        return jsonify({
            'success': True,
            'data': user,
            'message': 'User created successfully'
        }), 201
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update a user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user = user_service.update_user(user_id, data)
        if user:
            return jsonify({
                'success': True,
                'data': user,
                'message': 'User updated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        success = user_service.delete_user(user_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Test endpoint without authentication
@api_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify routing works"""
    return jsonify({
        'success': True,
        'message': 'Test endpoint working!',
        'timestamp': datetime.datetime.utcnow().isoformat()
    }), 200

# Configuration Upload Endpoint
@api_bp.route('/config/upload', methods=['POST'])
def upload_configuration():
    """Upload initial configuration XML file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.xml'):
        return jsonify({'success': False, 'error': 'Only XML files are allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'config')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Parse XML and process configuration
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Validate root element
            if root.tag != 'configuraciones':
                raise ValueError("Root element must be 'configuraciones'")
            
            # Initialize counters
            stats = {
                'tutores_cargados': 0,
                'estudiantes_cargados': 0,
                'asignaciones': {
                    'tutores': {
                        'total': 0,
                        'correcto': 0,
                        'incorrecto': 0
                    },
                    'estudiantes': {
                        'total': 0,
                        'correcto': 0,
                        'incorrecto': 0
                    }
                }
            }
            
            # Process courses
            cursos_element = root.find('cursos')
            if cursos_element is not None:
                for curso in cursos_element.findall('curso'):
                    codigo = curso.get('codigo')
                    nombre = curso.text.strip() if curso.text else ""
                    
                    if codigo and nombre:
                        try:
                            course_data = {
                                'codigo': codigo,
                                'nombre': nombre
                            }
                            course_storage.create_course(course_data)
                        except Exception as e:
                            print(f"Error creating course {codigo}: {str(e)}")
            
            # Process tutors
            tutores_element = root.find('tutores')
            if tutores_element is not None:
                for tutor in tutores_element.findall('tutor'):
                    registro_personal = tutor.get('registro_personal')
                    contrasenia = tutor.get('contrasenia')
                    nombre = tutor.text.strip() if tutor.text else ""
                    
                    if registro_personal and contrasenia and nombre:
                        try:
                            tutor_data = {
                                'username': registro_personal,
                                'email': f"{registro_personal}@tutor.com",
                                'password': contrasenia,
                                'first_name': nombre,
                                'last_name': '',
                                'is_admin': False
                            }
                            user_service.create_user(tutor_data)
                            stats['tutores_cargados'] += 1
                        except Exception as e:
                            print(f"Error creating tutor {registro_personal}: {str(e)}")
            
            # Process students
            estudiantes_element = root.find('estudiantes')
            if estudiantes_element is not None:
                for estudiante in estudiantes_element.findall('estudiante'):
                    carnet = estudiante.get('carnet')
                    contrasenia = estudiante.get('contrasenia')
                    nombre = estudiante.text.strip() if estudiante.text else ""
                    
                    if carnet and contrasenia and nombre:
                        try:
                            student_data = {
                                'carnet': carnet,
                                'password': contrasenia,
                                'nombre': nombre
                            }
                            student_storage.create_student(student_data)
                            stats['estudiantes_cargados'] += 1
                        except Exception as e:
                            print(f"Error creating student {carnet}: {str(e)}")
            
            # Process assignments
            asignaciones_element = root.find('asignaciones')
            if asignaciones_element is not None:
                # Process tutor-course assignments
                c_tutores_element = asignaciones_element.find('c_tutores')
                if c_tutores_element is not None:
                    for tutor_curso in c_tutores_element.findall('tutor_curso'):
                        codigo = tutor_curso.get('codigo')
                        registro_personal = tutor_curso.text.strip() if tutor_curso.text else ""
                        
                        if codigo and registro_personal:
                            stats['asignaciones']['tutores']['total'] += 1
                            
                            # Check if course exists
                            course = course_storage.get_course_by_code(codigo)
                            if course:
                                try:
                                    # Find tutor by username
                                    tutor = user_service.get_user_by_username(registro_personal)
                                    if tutor:
                                        assignment_storage.create_tutor_course_assignment(
                                            tutor['user_id'], codigo
                                        )
                                        stats['asignaciones']['tutores']['correcto'] += 1
                                    else:
                                        stats['asignaciones']['tutores']['incorrecto'] += 1
                                except Exception as e:
                                    stats['asignaciones']['tutores']['incorrecto'] += 1
                            else:
                                stats['asignaciones']['tutores']['incorrecto'] += 1
                
                # Process student-course assignments
                c_estudiante_element = asignaciones_element.find('c_estudiante')
                if c_estudiante_element is not None:
                    for estudiante_curso in c_estudiante_element.findall('estudiante_curso'):
                        codigo = estudiante_curso.get('codigo')
                        carnet = estudiante_curso.text.strip() if estudiante_curso.text else ""
                        
                        if codigo and carnet:
                            stats['asignaciones']['estudiantes']['total'] += 1
                            
                            # Check if course exists
                            course = course_storage.get_course_by_code(codigo)
                            if course:
                                try:
                                    # Find student by carnet
                                    student = student_storage.get_student_by_carnet(carnet)
                                    if student:
                                        assignment_storage.create_student_course_assignment(
                                            student['student_id'], codigo
                                        )
                                        stats['asignaciones']['estudiantes']['correcto'] += 1
                                    else:
                                        stats['asignaciones']['estudiantes']['incorrecto'] += 1
                                except Exception as e:
                                    stats['asignaciones']['estudiantes']['incorrecto'] += 1
                            else:
                                stats['asignaciones']['estudiantes']['incorrecto'] += 1
            
            # Generate output XML
            output_xml = generate_configuration_output(stats)
            
            return jsonify({
                'success': True,
                'message': 'Configuration file processed successfully',
                'filename': filename,
                'stats': stats,
                'output_xml': output_xml
            }), 200
            
        except ET.ParseError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': f'Invalid XML file: {str(e)}'}), 400
        except ValueError as e:
            os.remove(file_path)
            return jsonify({'success': False, 'error': str(e)}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error uploading configuration: {str(e)}'}), 500

def generate_configuration_output(stats):
    """Generate output XML with configuration results"""
    output_xml = f'''<?xml version="1.0"?>
<configuraciones_aplicadas>
    <tutores_cargados>{stats['tutores_cargados']}</tutores_cargados>
    <estudiantes_cargados>{stats['estudiantes_cargados']}</estudiantes_cargados>
    <asignaciones>
        <tutores>
            <total>{stats['asignaciones']['tutores']['total']}</total>
            <correcto>{stats['asignaciones']['tutores']['correcto']}</correcto>
            <incorrecto>{stats['asignaciones']['tutores']['incorrecto']}</incorrecto>
        </tutores>
        <estudiantes>
            <total>{stats['asignaciones']['estudiantes']['total']}</total>
            <correcto>{stats['asignaciones']['estudiantes']['correcto']}</correcto>
            <incorrecto>{stats['asignaciones']['estudiantes']['incorrecto']}</incorrecto>
        </estudiantes>
    </asignaciones>
</configuraciones_aplicadas>'''
    
    return output_xml

# Get all courses
@api_bp.route('/courses', methods=['GET'])
@login_required
def get_all_courses(auth_user_id):
    """Get all courses"""
    try:
        courses = course_storage.get_all_courses()
        return jsonify({
            'success': True,
            'data': courses,
            'count': len(courses)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get all students
@api_bp.route('/students', methods=['GET'])
@login_required
def get_all_students(auth_user_id):
    """Get all students"""
    try:
        students = student_storage.get_all_students()
        return jsonify({
            'success': True,
            'data': students,
            'count': len(students)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get all assignments
@api_bp.route('/assignments', methods=['GET'])
@login_required
def get_all_assignments(auth_user_id):
    """Get all assignments (tutor-course and student-course)"""
    try:
        tutor_assignments = assignment_storage.get_all_tutor_assignments()
        student_assignments = assignment_storage.get_all_student_assignments()
        
        return jsonify({
            'success': True,
            'data': {
                'tutor_assignments': tutor_assignments,
                'student_assignments': student_assignments,
                'total_tutor_assignments': len(tutor_assignments),
                'total_student_assignments': len(student_assignments)
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get assignments by tutor
@api_bp.route('/assignments/tutor/<int:tutor_id>', methods=['GET'])
@login_required
def get_assignments_by_tutor(auth_user_id, tutor_id):
    """Get all assignments for a specific tutor"""
    try:
        assignments = assignment_storage.get_tutor_assignments(tutor_id)
        return jsonify({
            'success': True,
            'data': assignments,
            'count': len(assignments)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get assignments by student
@api_bp.route('/assignments/student/<int:student_id>', methods=['GET'])
@login_required
def get_assignments_by_student(auth_user_id, student_id):
    """Get all assignments for a specific student"""
    try:
        assignments = assignment_storage.get_student_assignments(student_id)
        return jsonify({
            'success': True,
            'data': assignments,
            'count': len(assignments)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get assignments by course
@api_bp.route('/assignments/course/<course_code>', methods=['GET'])
@login_required
def get_assignments_by_course(auth_user_id, course_code):
    """Get all assignments for a specific course"""
    try:
        assignments = assignment_storage.get_course_assignments(course_code)
        return jsonify({
            'success': True,
            'data': assignments,
            'course_code': course_code
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Comprehensive users overview endpoint
@api_bp.route('/users/overview', methods=['GET'])
@login_required
def get_users_overview(auth_user_id):
    """Get comprehensive overview of all users (tutors and students)"""
    try:
        # Get all users (tutors)
        tutors = user_service.get_all_users()
        
        # Get all students
        students = student_storage.get_all_students()
        
        # Get all courses
        courses = course_storage.get_all_courses()
        
        # Get all assignments
        tutor_assignments = assignment_storage.get_all_tutor_assignments()
        student_assignments = assignment_storage.get_all_student_assignments()
        
        # Process tutors with their assignments
        tutors_with_assignments = []
        for tutor in tutors:
            tutor_id = tutor.get('user_id')
            tutor_assignments_list = assignment_storage.get_tutor_assignments(tutor_id)
            
            # Get course names for assignments
            assigned_courses = []
            for assignment in tutor_assignments_list:
                course_code = assignment.get('course_code')
                course = course_storage.get_course_by_code(course_code)
                if course:
                    assigned_courses.append({
                        'course_code': course_code,
                        'course_name': course.get('nombre')
                    })
            
            tutors_with_assignments.append({
                'user_id': tutor.get('user_id'),
                'username': tutor.get('username'),
                'email': tutor.get('email'),
                'first_name': tutor.get('first_name'),
                'last_name': tutor.get('last_name'),
                'is_admin': tutor.get('is_admin'),
                'is_active': tutor.get('is_active'),
                'created_at': tutor.get('created_at'),
                'assigned_courses': assigned_courses,
                'total_courses': len(assigned_courses)
            })
        
        # Process students with their assignments
        students_with_assignments = []
        for student in students:
            student_id = student.get('student_id')
            student_assignments_list = assignment_storage.get_student_assignments(student_id)
            
            # Get course names for assignments
            assigned_courses = []
            for assignment in student_assignments_list:
                course_code = assignment.get('course_code')
                course = course_storage.get_course_by_code(course_code)
                if course:
                    assigned_courses.append({
                        'course_code': course_code,
                        'course_name': course.get('nombre')
                    })
            
            students_with_assignments.append({
                'student_id': student.get('student_id'),
                'carnet': student.get('carnet'),
                'nombre': student.get('nombre'),
                'is_active': student.get('is_active'),
                'is_admin': student.get('is_admin'),
                'created_at': student.get('created_at'),
                'assigned_courses': assigned_courses,
                'total_courses': len(assigned_courses)
            })
        
        # Summary statistics
        summary = {
            'total_tutors': len(tutors),
            'total_students': len(students),
            'total_courses': len(courses),
            'total_tutor_assignments': len(tutor_assignments),
            'total_student_assignments': len(student_assignments),
            'tutors_with_assignments': len([t for t in tutors_with_assignments if t['total_courses'] > 0]),
            'students_with_assignments': len([s for s in students_with_assignments if s['total_courses'] > 0])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'summary': summary,
                'tutors': tutors_with_assignments,
                'students': students_with_assignments,
                'courses': courses
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Simple users list endpoint
@api_bp.route('/users/list', methods=['GET'])
@login_required
def get_users_list(auth_user_id):
    """Get simple list of users with basic info"""
    try:
        # Get all users (tutors)
        tutors = user_service.get_all_users()
        
        # Get all students
        students = student_storage.get_all_students()
        
        # Format tutors data
        tutors_list = []
        for tutor in tutors:
            tutors_list.append({
                'user_id': tutor.get('user_id'),
                'username': tutor.get('username'),
                'password': '****'  # Don't show actual password for security
            })
        
        # Format students data
        students_list = []
        for student in students:
            students_list.append({
                'student_id': student.get('student_id'),
                'carnet': student.get('carnet'),
                'password': '****'  # Don't show actual password for security
            })
        
        return jsonify({
            'success': True,
            'data': {
                'tutors': tutors_list,
                'students': students_list,
                'total_tutors': len(tutors_list),
                'total_students': len(students_list)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500 