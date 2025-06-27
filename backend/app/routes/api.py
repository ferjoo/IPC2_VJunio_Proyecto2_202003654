from flask import Blueprint, request, jsonify, Response
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
from ..models.grades_storage import grades_storage
import graphviz

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
    print(f"DEBUG: Login data received: {data}")
    if not data:
        print("DEBUG: No data provided")
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    print(f"DEBUG: username={username}, email={email}, password={'*' * len(password) if password else None}")
    if not (username or email) or not password:
        print("DEBUG: Username/email and password required")
        return jsonify({'success': False, 'error': 'Username/email and password required'}), 400
    
    user = None
    if username:
        print(f"DEBUG: Trying login as username: {username}")
        user = user_service.authenticate_user(username, password)
        print(f"DEBUG: Result of authenticate_user: {user}")
        if not user:
            print(f"DEBUG: Username login failed, searching all users for username match: {username}")
            all_users = user_service.get_all_users()
            for u in all_users:
                print(f"DEBUG: Checking user: {u.get('username')}")
                if u.get('username') == username:
                    user = user_service.authenticate_user(u.get('username'), password)
                    print(f"DEBUG: Result of authenticate_user for user {u.get('username')}: {user}")
                    if user:
                        break
        if not user:
            print(f"DEBUG: Trying as student carnet: {username}")
            student = student_storage.authenticate_student(username, password)
            print(f"DEBUG: Result of authenticate_student: {student}")
            if student:
                print(f"DEBUG: Student login successful: {student}")
                return jsonify({'success': True, 'token': generate_token(student['student_id']), 'user': student}), 200
    elif email:
        print(f"DEBUG: Trying login as email: {email}")
        user_data = user_service.get_user_by_email(email)
        print(f"DEBUG: Result of get_user_by_email: {user_data}")
        if user_data:
            user = user_service.authenticate_user(user_data['username'], password)
            print(f"DEBUG: Result of authenticate_user by email: {user}")
    
    if user:
        print(f"DEBUG: Login successful for user: {user}")
        token = generate_token(user['user_id'])
        return jsonify({'success': True, 'token': token, 'user': user}), 200
    print("DEBUG: Invalid credentials")
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
    print(f"DEBUG: upload_grades called with auth_user_id: {auth_user_id}")
    print(f"DEBUG: request.files: {request.files}")
    print(f"DEBUG: request.form: {request.form}")
    
    if 'file' not in request.files:
        print("DEBUG: No file in request.files")
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    print(f"DEBUG: File received: {file.filename}")
    
    if file.filename == '':
        print("DEBUG: Empty filename")
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.xml'):
        print("DEBUG: File is not XML")
        return jsonify({'success': False, 'error': 'Only XML files are allowed'}), 400
    
    try:
        # Read XML content
        print("DEBUG: Reading XML content")
        xml_content = file.read().decode('utf-8')
        print(f"DEBUG: XML content length: {len(xml_content)}")
        print(f"DEBUG: XML content preview: {xml_content[:200]}...")
        
        # Parse and store grades using sparse matrix
        print("DEBUG: Calling grades_storage.parse_grades_xml")
        result = grades_storage.parse_grades_xml(xml_content, auth_user_id)
        print(f"DEBUG: Parse result: {result}")
        
        return jsonify({
            'success': True,
            'message': 'Grades uploaded and processed successfully using sparse matrix',
            'data': result
        }), 200
        
    except ValueError as e:
        print(f"DEBUG: ValueError caught: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"DEBUG: Exception caught: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error uploading grades: {str(e)}'}), 500

# Grade Reports
@api_bp.route('/reports/grades', methods=['GET'])
@login_required
def get_grade_reports(auth_user_id):
    """Generate grade summary report after tutor uploads grades"""
    try:
        # Get query parameters for filtering
        course_id = request.args.get('course_id')
        tutor_id = request.args.get('tutor_id', auth_user_id)
        
        if course_id:
            # Generate report for specific course
            report = grades_storage.generate_grade_report(course_id, tutor_id)
            if not report:
                return jsonify({'success': False, 'error': 'Course not found or no grades available'}), 404
            
            return jsonify({
                'success': True,
                'data': report
            }), 200
        else:
            # Get all courses for the tutor
            tutor_courses = grades_storage.get_tutor_courses(tutor_id)
            reports = {}
            
            for course_key, course_info in tutor_courses.items():
                course_code = course_info['course_code']
                report = grades_storage.generate_grade_report(course_code, tutor_id)
                if report:
                    reports[course_code] = report
            
            return jsonify({
                'success': True,
                'data': {
                    'tutor_id': tutor_id,
                    'courses': reports,
                    'total_courses': len(reports)
                }
            }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error generating report: {str(e)}'}), 500

@api_bp.route('/grades/courses', methods=['GET'])
@login_required
def get_tutor_courses(auth_user_id):
    """Get all courses with grades for a tutor"""
    try:
        tutor_courses = grades_storage.get_tutor_courses(auth_user_id)
        
        return jsonify({
            'success': True,
            'data': tutor_courses,
            'count': len(tutor_courses)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting courses: {str(e)}'}), 500

@api_bp.route('/grades/course/<course_code>', methods=['GET'])
@login_required
def get_course_grades(auth_user_id, course_code):
    """Get detailed grades for a specific course"""
    try:
        course_data = grades_storage.get_course_grades(course_code, auth_user_id)
        
        if not course_data:
            return jsonify({'success': False, 'error': 'Course not found or no grades available'}), 404
        
        # Convert sparse matrix to readable format
        course_info = course_data['course_info']
        sparse_matrix = course_data['sparse_matrix']
        
        # Create grades table
        grades_table = []
        for i, activity in enumerate(course_info['activities']):
            row = {'activity': activity}
            for j, student in enumerate(course_info['students']):
                grade = sparse_matrix.get_value(i, j)
                row[student] = grade if grade > 0 else None
            grades_table.append(row)
        
        return jsonify({
            'success': True,
            'data': {
                'course_info': course_info,
                'grades_table': grades_table,
                'matrix_info': course_data['matrix_info']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting course grades: {str(e)}'}), 500

@api_bp.route('/grades/stats', methods=['GET'])
@login_required
def get_grades_stats(auth_user_id):
    """Get grades storage statistics"""
    try:
        stats = grades_storage.get_storage_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error getting stats: {str(e)}'}), 500

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
                'cursos_cargados': 0,
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
            
            # Process courses first
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
                            stats['cursos_cargados'] += 1
                            print(f"Created course: {codigo} - {nombre}")
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
                            existing_tutor = user_service.get_user_by_username(registro_personal)
                            if existing_tutor:
                                # Update password and name
                                user_service.update_user(existing_tutor['user_id'], {
                                    'password': contrasenia,
                                    'first_name': nombre,
                                    'last_name': ''
                                })
                                print(f"Updated tutor: {registro_personal} - {nombre}")
                            else:
                                user_service.create_user(tutor_data)
                                stats['tutores_cargados'] += 1
                                print(f"Created tutor: {registro_personal} - {nombre}")
                        except Exception as e:
                            print(f"Error creating/updating tutor {registro_personal}: {str(e)}")
            
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
                            print(f"Created student: {carnet} - {nombre}")
                        except Exception as e:
                            print(f"Error creating student {carnet}: {str(e)}")
            
            # Process assignments - improved logic
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
                            
                            try:
                                # Check if course exists
                                course = course_storage.get_course_by_code(codigo)
                                if not course:
                                    print(f"Course {codigo} not found")
                                    stats['asignaciones']['tutores']['incorrecto'] += 1
                                    continue
                                
                                # Find tutor by username - improved lookup
                                tutor = user_service.get_user_by_username(registro_personal)
                                
                                if not tutor:
                                    print(f"Tutor {registro_personal} not found")
                                    stats['asignaciones']['tutores']['incorrecto'] += 1
                                    continue
                                
                                # Create assignment
                                assignment_storage.create_tutor_course_assignment(
                                    tutor['user_id'], codigo
                                )
                                stats['asignaciones']['tutores']['correcto'] += 1
                                print(f"Created tutor assignment: {registro_personal} -> {codigo}")
                                
                            except Exception as e:
                                print(f"Error creating tutor assignment {registro_personal} -> {codigo}: {str(e)}")
                                stats['asignaciones']['tutores']['incorrecto'] += 1
                
                # Process student-course assignments
                c_estudiante_element = asignaciones_element.find('c_estudiante')
                if c_estudiante_element is not None:
                    for estudiante_curso in c_estudiante_element.findall('estudiante_curso'):
                        codigo = estudiante_curso.get('codigo')
                        carnet = estudiante_curso.text.strip() if estudiante_curso.text else ""
                        
                        if codigo and carnet:
                            stats['asignaciones']['estudiantes']['total'] += 1
                            
                            try:
                                # Check if course exists
                                course = course_storage.get_course_by_code(codigo)
                                if not course:
                                    print(f"Course {codigo} not found")
                                    stats['asignaciones']['estudiantes']['incorrecto'] += 1
                                    continue
                                
                                # Find student by carnet - improved lookup
                                student = student_storage.get_student_by_carnet(carnet)
                                
                                if not student:
                                    print(f"Student {carnet} not found")
                                    stats['asignaciones']['estudiantes']['incorrecto'] += 1
                                    continue
                                
                                # Create assignment
                                assignment_storage.create_student_course_assignment(
                                    student['student_id'], codigo
                                )
                                stats['asignaciones']['estudiantes']['correcto'] += 1
                                print(f"Created student assignment: {carnet} -> {codigo}")
                                
                            except Exception as e:
                                print(f"Error creating student assignment {carnet} -> {codigo}: {str(e)}")
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
    <cursos_cargados>{stats['cursos_cargados']}</cursos_cargados>
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

        # Determine the role of the requesting user
        requested_user_role = None
        user = user_service.get_user_by_id(auth_user_id)
        if user:
            if user.get('is_admin'):
                requested_user_role = 'admin'
            else:
                requested_user_role = 'tutor'
        else:
            student = student_storage.get_student_by_id(auth_user_id)
            if student:
                requested_user_role = 'student'

        # Format tutors data
        tutors_list = []
        for tutor in tutors:
            display_name = tutor.get('username') or f"{tutor.get('first_name', '')} {tutor.get('last_name', '')}".strip()
            tutors_list.append({
                'user_id': tutor.get('user_id'),
                'username': tutor.get('username'),
                'display_name': display_name,
                'password': '****',
                'role': 'tutor'
            })
        # Format students data
        students_list = []
        for student in students:
            display_name = student.get('nombre')
            students_list.append({
                'student_id': student.get('student_id'),
                'carnet': student.get('carnet'),
                'display_name': display_name,
                'password': '****',
                'role': 'student'
            })
        return jsonify({
            'success': True,
            'requested_user_role': requested_user_role,
            'data': {
                'tutors': tutors_list,
                'students': students_list,
                'total_tutors': len(tutors_list),
                'total_students': len(students_list)
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users/<role>/<int:id>', methods=['GET'])
@login_required
def get_user_by_role_and_id(auth_user_id, role, id):
    """Get a user by role (tutor or student) and ID, avoiding ambiguity if IDs overlap."""
    try:
        if role == 'tutor':
            user = user_service.get_user_by_id(id)
            if user:
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
            else:
                return jsonify({'success': False, 'error': 'Tutor not found'}), 404
        elif role == 'student':
            student = student_storage.get_student_by_id(id)
            if student:
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
            else:
                return jsonify({'success': False, 'error': 'Student not found'}), 404
        else:
            return jsonify({'success': False, 'error': 'Invalid role'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/tutor/schedule/upload', methods=['POST'])
@login_required
def upload_tutor_schedule(auth_user_id):
    """Upload schedule XML file for a tutor (bulk schedule upload)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    if not file.filename.endswith('.xml'):
        return jsonify({'success': False, 'error': 'Only XML files are allowed for schedules'}), 400

    tutor_id = auth_user_id
    try:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'tutor_schedules')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Parse XML to extract schedule information
        import re
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            if root.tag != 'horarios':
                raise ValueError("Root element must be 'horarios'")

            # Get courses assigned to this tutor
            assigned_courses = [a['course_code'] for a in assignment_storage.get_tutor_assignments(tutor_id)]
            schedules_to_create = []
            processed_courses = 0
            ignored_courses = 0
            invalid_courses = 0

            for curso in root.findall('curso'):
                codigo = curso.get('codigo')
                if not codigo or codigo not in assigned_courses:
                    ignored_courses += 1
                    continue
                text_content = curso.text.strip() if curso.text else ""
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
                'processed_by': tutor_id,
                'summary': {
                    'total_courses_processed': processed_courses,
                    'total_schedules_created': len(created_schedules),
                    'ignored_courses': ignored_courses,
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

@api_bp.route('/debug/reset_password', methods=['POST'])
def debug_reset_password():
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('password')
    if not username or not new_password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    user = user_service.get_user_by_username(username)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    user_service.update_user(user['user_id'], {'password': new_password})
    return jsonify({'success': True, 'message': f'Password for {username} reset.'}), 200

@api_bp.route('/grades/report/graphviz/<course_code>', methods=['GET'])
@login_required
def graphviz_grades_report(auth_user_id, course_code):
    """Generate a Graphviz SVG report for the grades matrix of a course, as a node-based table-like grid."""
    course_data = grades_storage.get_course_grades(course_code, auth_user_id)
    if not course_data:
        return jsonify({'success': False, 'error': 'Course not found or no grades available'}), 404

    course_info = course_data['course_info']
    sparse_matrix = course_data['sparse_matrix']
    activities = course_info['activities']
    students = course_info['students']

    import graphviz
    dot = graphviz.Digraph(format='svg')
    dot.attr(rankdir='LR', nodesep='0.7', ranksep='0.7', splines='ortho')
    dot.attr('node', shape='box', style='filled', fontname='Arial')

    # Header node
    dot.node('header', 'RESUMEN NOTAS', fillcolor='#f9f9b6', width='2.2', height='0.7')

    # Student nodes (columns, green)
    student_nodes = []
    for idx, student in enumerate(students):
        node_id = f'stud_{idx}'
        dot.node(node_id, student, fillcolor='#b6f9b6', width='1.2', height='0.7')
        dot.edge('header', node_id)
        student_nodes.append(node_id)

    # Activity nodes (rows, orange)
    activity_nodes = []
    for idx, activity in enumerate(activities):
        node_id = f'act_{idx}'
        dot.node(node_id, activity, fillcolor='#ff9966', width='1.5', height='0.7')
        dot.edge('header', node_id)
        activity_nodes.append(node_id)

    # Rank students (columns) on the same level (top row)
    if student_nodes:
        dot.body.append('{rank=same; ' + ' '.join(['header'] + student_nodes) + ';}')
    # Rank activities (rows) on the same level (first column)
    for idx, activity_node in enumerate(activity_nodes):
        dot.body.append('{rank=same; ' + activity_node + ' ' + ' '.join([f'g_{idx}_{j}' for j in range(len(students)) if 0 <= sparse_matrix.get_value(idx, j) <= 100]) + ';}')

    # Grade nodes (white) and edges
    for i, activity in enumerate(activities):
        for j, student in enumerate(students):
            grade = sparse_matrix.get_value(i, j)
            if grade is not None and 0 <= grade <= 100:
                grade_label = str(int(grade)) if grade == int(grade) else str(grade)
                grade_node = f'g_{i}_{j}'
                dot.node(grade_node, grade_label, fillcolor='white', width='1', height='0.7')
                dot.edge(f'act_{i}', grade_node)
                dot.edge(f'stud_{j}', grade_node)

    # Invisible edges to force grid alignment (down columns)
    for j in range(len(students)):
        prev = f'stud_{j}'
        for i in range(len(activities)):
            grade_node = f'g_{i}_{j}'
            grade = sparse_matrix.get_value(i, j)
            if grade is not None and 0 <= grade <= 100:
                dot.edge(prev, grade_node, style='invis')
                prev = grade_node

    # Invisible edges to force grid alignment (across rows)
    for i in range(len(activities)):
        prev = f'act_{i}'
        for j in range(len(students)):
            grade_node = f'g_{i}_{j}'
            grade = sparse_matrix.get_value(i, j)
            if grade is not None and 0 <= grade <= 100:
                dot.edge(prev, grade_node, style='invis')
                prev = grade_node

    svg = dot.pipe(format='svg')
    return Response(svg, mimetype='image/svg+xml') 