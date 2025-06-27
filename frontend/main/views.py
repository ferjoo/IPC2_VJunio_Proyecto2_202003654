from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.conf import settings
import requests

def home(request):
    """Home page view"""
    return render(request, 'main/home.html')

def login_view(request):
    """Login page view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Backend API URL from settings
        backend_url = f'{settings.BACKEND_API_URL}/login'
        
        try:
            response = requests.post(backend_url, json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Store token in session
                    request.session['auth_token'] = data['token']
                    request.session['user_data'] = data['user']
                    return redirect('main:dashboard')
                else:
                    return render(request, 'main/login.html', {
                        'error': data.get('error', 'Login failed')
                    })
            else:
                return render(request, 'main/login.html', {
                    'error': 'Invalid credentials'
                })
                
        except requests.exceptions.RequestException as e:
            return render(request, 'main/login.html', {
                'error': f'Connection error: {str(e)}'
            })
    
    return render(request, 'main/login.html')

def dashboard(request):
    """Dashboard view - requires authentication"""
    if 'auth_token' not in request.session:
        return redirect('main:login')
    
    user_data = request.session.get('user_data', {})
    
    # Redirect tutors to their specific dashboard
    if user_data.get('username') and not user_data.get('is_admin'):
        return redirect('main:tutor_dashboard')
    
    # Admin dashboard logic
    input_xml = None
    output_xml = None
    if request.method == 'POST' and user_data.get('is_admin'):
        file = request.FILES.get('file')
        if file:
            input_xml = file.read().decode('utf-8')
            backend_url = f'{settings.BACKEND_API_URL}/config/upload'
            files = {'file': (file.name, input_xml, 'application/xml')}
            try:
                response = requests.post(backend_url, files=files)
                try:
                    data = response.json()
                    # Show output_xml from backend response
                    output_xml = data.get('output_xml') or data.get('message') or str(data)
                except Exception:
                    output_xml = response.text
            except Exception as e:
                output_xml = f'Error: {str(e)}'
    
    return render(request, 'main/dashboard.html', {
        'user': user_data,
        'input_xml': input_xml,
        'output_xml': output_xml
    })

def tutor_dashboard(request):
    """Tutor-specific dashboard view"""
    if 'auth_token' not in request.session:
        return redirect('main:login')
    
    user_data = request.session.get('user_data', {})
    token = request.session.get('auth_token')
    
    # Verify this is a tutor
    if not user_data.get('username') or user_data.get('is_admin'):
        return redirect('main:dashboard')
    
    # Get tutor's assignments and schedules
    tutor_id = user_data.get('user_id')
    headers = {'Authorization': f'Bearer {token}'}
    
    assignments = []
    schedules = []
    error = None
    message = None
    
    # Handle schedule upload
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        backend_url_upload = f"{settings.BACKEND_API_URL}/schedule"
        files = {'file': (file.name, file.read(), file.content_type)}
        form_data = {'tutor_id': tutor_id}
        
        try:
            response = requests.post(backend_url_upload, files=files, data=form_data, headers=headers)
            data = response.json()
            if data.get('success'):
                message = data.get('message', 'Horario cargado exitosamente')
            else:
                error = data.get('error', 'Error al cargar el archivo')
        except Exception as e:
            error = str(e)
    
    try:
        # Get tutor's course assignments
        backend_url_assignments = f"{settings.BACKEND_API_URL}/assignments/tutor/{tutor_id}"
        response = requests.get(backend_url_assignments, headers=headers)
        data = response.json()
        if data.get('success'):
            assignments = data['data']
        
        # Get tutor's schedules using the correct endpoint
        backend_url_schedules = f"{settings.BACKEND_API_URL}/schedules/tutor/{tutor_id}"
        print(f"DEBUG: Fetching schedules from: {backend_url_schedules}")
        print(f"DEBUG: Tutor ID: {tutor_id}")
        print(f"DEBUG: Headers: {headers}")
        
        response = requests.get(backend_url_schedules, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response text: {response.text}")
        
        data = response.json()
        if data.get('success'):
            schedules = data['data']
            print(f"DEBUG: Schedules found: {len(schedules)}")
            print(f"DEBUG: Schedules data: {schedules}")
        else:
            if not error:  # Only set error if there's no upload error
                error = data.get('error', 'No se pudieron obtener los horarios')
                print(f"DEBUG: Error getting schedules: {error}")
            
    except Exception as e:
        if not error:  # Only set error if there's no upload error
            error = str(e)
            print(f"DEBUG: Exception getting schedules: {error}")
    
    return render(request, 'main/tutor_dashboard.html', {
        'user': user_data,
        'assignments': assignments,
        'schedules': schedules,
        'error': error,
        'message': message
    })

def logout_view(request):
    """Logout view"""
    request.session.flush()
    return redirect('main:home')

def admin_upload_proxy(request):
    if request.method == 'POST' and request.FILES.get('file'):
        backend_url = f'{settings.BACKEND_API_URL}/config/upload'
        file = request.FILES['file']
        files = {'file': (file.name, file.read(), file.content_type)}
        try:
            response = requests.post(backend_url, files=files)
            try:
                data = response.json()
            except Exception:
                return JsonResponse({'error': 'Invalid response from backend', 'raw': response.text}, status=500)
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return HttpResponseBadRequest('Invalid request')

def ver_usuarios(request):
    # Require authentication
    token = request.session.get('auth_token')
    user_data = request.session.get('user_data', {})
    if not token:
        return redirect('main:login')

    print(f"DEBUG: ver_usuarios accessed by user: {user_data.get('username')}")
    print(f"DEBUG: Token exists: {bool(token)}")

    backend_url = f"{settings.BACKEND_API_URL}/users/list"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        print(f"DEBUG: Calling backend URL: {backend_url}")
        response = requests.get(backend_url, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response text: {response.text}")
        
        data = response.json()
        if data.get('success'):
            tutors = data['data']['tutors']
            students = data['data']['students']
            print(f"DEBUG: Found {len(tutors)} tutors and {len(students)} students")
        else:
            tutors = []
            students = []
            print(f"DEBUG: Backend returned error: {data.get('error')}")
    except Exception as e:
        tutors = []
        students = []
        print(f"DEBUG: Exception in ver_usuarios: {str(e)}")
    
    return render(request, 'main/ver_usuarios.html', {
        'tutors': tutors,
        'students': students,
        'user': user_data,
    })

def usuario_detalle(request, role, id):
    token = request.session.get('auth_token')
    user_data = request.session.get('user_data', {})
    if not token:
        return redirect('main:login')

    print(f"DEBUG: usuario_detalle accessed - role: {role}, id: {id}")

    backend_url = f"{settings.BACKEND_API_URL}/users/{role}/{id}"
    headers = {'Authorization': f'Bearer {token}'}
    user_info = None
    error = None
    try:
        print(f"DEBUG: Calling backend URL: {backend_url}")
        response = requests.get(backend_url, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")
        
        data = response.json()
        if data.get('success'):
            user_info = data['data']
            print(f"DEBUG: User info retrieved successfully")
        else:
            error = data.get('error', 'No se encontró el usuario')
            print(f"DEBUG: Backend error: {error}")
    except Exception as e:
        error = str(e)
        print(f"DEBUG: Exception in usuario_detalle: {error}")
    
    return render(request, 'main/usuario_card.html', {
        'user': user_data,
        'user_info': user_info,
        'role': role,
        'error': error,
    })

def mi_informacion(request):
    token = request.session.get('auth_token')
    user_data = request.session.get('user_data', {})
    if not token or not user_data:
        return redirect('main:login')

    print(f"DEBUG: mi_informacion accessed by user: {user_data.get('username')}")

    # Determine role and id
    if user_data.get('is_admin'):
        role = 'tutor'
        id = user_data.get('user_id')
    elif user_data.get('username'):
        role = 'tutor'
        id = user_data.get('user_id')
    elif user_data.get('carnet'):
        role = 'student'
        id = user_data.get('student_id')
    else:
        return redirect('main:login')

    print(f"DEBUG: Determined role: {role}, id: {id}")

    backend_url = f"{settings.BACKEND_API_URL}/users/{role}/{id}"
    headers = {'Authorization': f'Bearer {token}'}
    user_info = None
    error = None
    try:
        print(f"DEBUG: Calling backend URL: {backend_url}")
        response = requests.get(backend_url, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")
        
        data = response.json()
        if data.get('success'):
            user_info = data['data']
            print(f"DEBUG: User info retrieved successfully")
        else:
            error = data.get('error', 'No se encontró el usuario')
            print(f"DEBUG: Backend error: {error}")
    except Exception as e:
        error = str(e)
        print(f"DEBUG: Exception in mi_informacion: {error}")
    
    return render(request, 'main/usuario_card.html', {
        'user': user_data,
        'user_info': user_info,
        'role': role,
        'error': error,
    })

def tutor_horarios(request):
    token = request.session.get('auth_token')
    user_data = request.session.get('user_data', {})
    if not token or not user_data:
        return redirect('main:login')
    
    tutor_id = user_data.get('user_id')
    headers = {'Authorization': f'Bearer {token}'}
    backend_url_upload = f"{settings.BACKEND_API_URL}/schedule"
    backend_url_schedules = f"{settings.BACKEND_API_URL}/schedules/tutor/{tutor_id}"
    
    message = None
    error = None
    schedules = []
    
    # Handle file upload
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        files = {'file': (file.name, file.read(), file.content_type)}
        form_data = {'tutor_id': tutor_id}  # Add tutor_id to form data
        
        try:
            response = requests.post(backend_url_upload, files=files, data=form_data, headers=headers)
            data = response.json()
            if data.get('success'):
                message = data.get('message', 'Horario cargado exitosamente')
            else:
                error = data.get('error', 'Error al cargar el archivo')
        except Exception as e:
            error = str(e)
    
    # Always fetch current schedules (this will include newly uploaded ones)
    try:
        response = requests.get(backend_url_schedules, headers=headers)
        data = response.json()
        if data.get('success'):
            schedules = data['data']
        else:
            if not error:  # Only set error if there's no upload error
                error = data.get('error', 'No se pudieron obtener los horarios')
    except Exception as e:
        if not error:  # Only set error if there's no upload error
            error = str(e)
    
    return render(request, 'main/tutor_horarios.html', {
        'user': user_data,
        'schedules': schedules,
        'message': message,
        'error': error,
    })

def tutor_notas(request):
    """Tutor grades upload view"""
    if 'auth_token' not in request.session:
        return redirect('main:login')
    
    user_data = request.session.get('user_data', {})
    token = request.session.get('auth_token')
    
    # Verify this is a tutor
    if not user_data.get('username') or user_data.get('is_admin'):
        return redirect('main:dashboard')
    
    message = None
    error = None
    
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        backend_url = f"{settings.BACKEND_API_URL}/grades/upload"
        files = {'file': (file.name, file.read(), file.content_type)}
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = requests.post(backend_url, files=files, headers=headers)
            data = response.json()
            if data.get('success'):
                message = data.get('message', 'Notas cargadas exitosamente')
            else:
                error = data.get('error', 'Error al cargar las notas')
        except Exception as e:
            error = str(e)
    
    return render(request, 'main/tutor_notas.html', {
        'user': user_data,
        'message': message,
        'error': error
    })

def debug_schedules(request):
    """Debug view to test schedules endpoint"""
    if 'auth_token' not in request.session:
        return redirect('main:login')
    
    user_data = request.session.get('user_data', {})
    token = request.session.get('auth_token')
    tutor_id = user_data.get('user_id')
    headers = {'Authorization': f'Bearer {token}'}
    
    debug_info = {
        'tutor_id': tutor_id,
        'user_data': user_data,
        'token_exists': bool(token),
        'endpoints': {}
    }
    
    # Test all schedules endpoint
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/schedules", headers=headers)
        debug_info['endpoints']['all_schedules'] = {
            'status': response.status_code,
            'data': response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        debug_info['endpoints']['all_schedules'] = {'error': str(e)}
    
    # Test tutor schedules endpoint
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/schedules/tutor/{tutor_id}", headers=headers)
        debug_info['endpoints']['tutor_schedules'] = {
            'status': response.status_code,
            'data': response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        debug_info['endpoints']['tutor_schedules'] = {'error': str(e)}
    
    return JsonResponse(debug_info)

def grades_courses_api(request):
    """API endpoint to get tutor's courses with grades"""
    if 'auth_token' not in request.session:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/grades/courses", headers=headers)
        return JsonResponse(response.json(), status=response.status_code)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def grades_course_api(request, course_code):
    """API endpoint to get detailed grades for a specific course"""
    if 'auth_token' not in request.session:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/grades/course/{course_code}", headers=headers)
        return JsonResponse(response.json(), status=response.status_code)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def grades_report_api(request):
    """API endpoint to get grade reports"""
    if 'auth_token' not in request.session:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get query parameters
    course_id = request.GET.get('course_id')
    
    try:
        url = f"{settings.BACKEND_API_URL}/reports/grades"
        if course_id:
            url += f"?course_id={course_id}"
        
        response = requests.get(url, headers=headers)
        return JsonResponse(response.json(), status=response.status_code)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def tutor_reportes(request):
    if 'auth_token' not in request.session:
        return redirect('main:login')
    user_data = request.session.get('user_data', {})
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    # Fetch courses from backend
    backend_url = f"{settings.BACKEND_API_URL}/grades/courses"
    course_list = []
    try:
        response = requests.get(backend_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                course_list = list(data['data'].values())
    except Exception:
        pass
    return render(request, 'main/tutor_reportes.html', {'user': user_data, 'course_list': course_list})

def tutor_reporte_svg(request, course_code):
    if 'auth_token' not in request.session:
        return redirect('main:login')
    user_data = request.session.get('user_data', {})
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    backend_url = f"{settings.BACKEND_API_URL}/grades/report/graphviz/{course_code}"
    svg = None
    error = None
    try:
        import requests
        response = requests.get(backend_url, headers=headers)
        if response.status_code == 200:
            svg = response.text
        else:
            error = response.text or 'No se pudo generar el reporte.'
    except Exception as e:
        error = str(e)
    return render(request, 'main/tutor_reporte_svg.html', {'user': user_data, 'svg': svg, 'error': error, 'course_code': course_code})

def tutor_reporte_svg_descargar(request, course_code):
    if 'auth_token' not in request.session:
        return redirect('main:login')
    token = request.session.get('auth_token')
    headers = {'Authorization': f'Bearer {token}'}
    backend_url = f"{settings.BACKEND_API_URL}/grades/report/graphviz/{course_code}"
    try:
        import requests
        response = requests.get(backend_url, headers=headers)
        if response.status_code == 200:
            svg = response.text
            response = HttpResponse(svg, content_type='image/svg+xml')
            response['Content-Disposition'] = f'attachment; filename="reporte_{course_code}.svg"'
            return response
        else:
            return HttpResponse('No se pudo descargar el reporte.', status=400)
    except Exception as e:
        return HttpResponse(str(e), status=500)
