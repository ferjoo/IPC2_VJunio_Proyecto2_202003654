import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from ..utils.sparse_matrix import SparseMatrix, create_sparse_matrix_from_data

class GradesStorage:
    """
    Storage class for managing student grades using sparse matrices.
    Stores grades data from XML files uploaded by tutors.
    """
    
    def __init__(self, storage_file='grades_data.json'):
        self.storage_file = storage_file
        self.grades_data = self._load_data()
    
    def _load_data(self):
        """Load grades data from storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert string keys back to tuples for sparse matrix reconstruction
                for course_key in data.get('sparse_matrices', {}):
                    matrix_data = data['sparse_matrices'][course_key].get('matrix_data', {})
                    # Convert string keys back to tuple format
                    data['sparse_matrices'][course_key]['matrix_data'] = {
                        tuple(map(int, key.split(','))): value for key, value in matrix_data.items()
                    }
                    
                return data
            except (json.JSONDecodeError, FileNotFoundError):
                return {
                    'courses': {},
                    'sparse_matrices': {},
                    'metadata': {
                        'created_at': datetime.utcnow().isoformat(),
                        'last_updated': datetime.utcnow().isoformat()
                    }
                }
        return {
            'courses': {},
            'sparse_matrices': {},
            'metadata': {
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat()
            }
        }
    
    def _save_data(self):
        """Save grades data to storage file"""
        self.grades_data['metadata']['last_updated'] = datetime.utcnow().isoformat()
        # Convert tuple keys to strings for JSON serialization
        serializable_data = self.grades_data.copy()
        for course_key in serializable_data['sparse_matrices']:
            matrix_data = serializable_data['sparse_matrices'][course_key]['matrix_data']
            # Robustly convert tuple keys to string format, leave string keys as is
            serializable_data['sparse_matrices'][course_key]['matrix_data'] = {
                (f"{key[0]},{key[1]}" if isinstance(key, tuple) else str(key)): value
                for key, value in matrix_data.items()
            }
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
    
    def parse_grades_xml(self, xml_content, tutor_id):
        """
        Parse XML grades file and create sparse matrix
        
        Expected XML format:
        <?xml version="1.0"?>
        <curso codigo="XXXX">Nombre_del_curso</curso>
        <notas>
            <actividad nombre="Tarea1" carnet="XXXX">90</actividad>
            <actividad nombre="Tarea2" carnet="XXX">60</actividad>
            ...
        </notas>
        """
        try:
            print(f"DEBUG: parse_grades_xml called with tutor_id: {tutor_id}")
            print(f"DEBUG: XML content length: {len(xml_content)}")
            print(f"DEBUG: XML content preview: {xml_content[:200]}...")
            
            # Remove XML declaration if present and wrap in root element
            if xml_content.strip().startswith('<?xml'):
                # Find the end of the XML declaration
                end_declaration = xml_content.find('?>') + 2
                xml_content = xml_content[end_declaration:].strip()
            
            # Wrap the XML content in a root element since XML needs one
            wrapped_xml = f"<root>{xml_content}</root>"
            print(f"DEBUG: Wrapped XML: {wrapped_xml[:200]}...")
            
            root = ET.fromstring(wrapped_xml)
            print(f"DEBUG: Root tag: {root.tag}")
            
            # Extract course information
            curso_elem = root.find('curso')
            print(f"DEBUG: curso_elem found: {curso_elem is not None}")
            if curso_elem is None:
                raise ValueError("Missing 'curso' element in XML")
            
            course_code = curso_elem.get('codigo')
            course_name = curso_elem.text.strip()
            print(f"DEBUG: Course code: {course_code}, Course name: {course_name}")
            
            if not course_code:
                raise ValueError("Course code is required in 'curso' element")
            
            # Extract grades
            notas_elem = root.find('notas')
            print(f"DEBUG: notas_elem found: {notas_elem is not None}")
            if notas_elem is None:
                raise ValueError("Missing 'notas' element in XML")
            
            activities = []
            students = set()
            grades_data = {}
            
            actividades = notas_elem.findall('actividad')
            print(f"DEBUG: Found {len(actividades)} actividades")
            
            for actividad in actividades:
                activity_name = actividad.get('nombre')
                student_carnet = actividad.get('carnet')
                grade_value = actividad.text.strip()
                
                print(f"DEBUG: Processing actividad - nombre: {activity_name}, carnet: {student_carnet}, grade: {grade_value}")
                
                if not activity_name or not student_carnet or not grade_value:
                    raise ValueError("Missing required attributes in 'actividad' element")
                
                try:
                    grade = float(grade_value)
                    if grade < 0 or grade > 100:
                        raise ValueError(f"Grade {grade} is out of valid range (0-100)")
                except ValueError:
                    raise ValueError(f"Invalid grade value: {grade_value}")
                
                activities.append(activity_name)
                students.add(student_carnet)
                
                if activity_name not in grades_data:
                    grades_data[activity_name] = {}
                grades_data[activity_name][student_carnet] = grade
            
            print(f"DEBUG: Unique activities: {list(set(activities))}")
            print(f"DEBUG: Unique students: {list(students)}")
            print(f"DEBUG: Grades data: {grades_data}")
            
            # Create sparse matrix
            activities = list(set(activities))  # Remove duplicates and maintain order
            students = list(students)
            
            print(f"DEBUG: Creating sparse matrix with {len(activities)} activities and {len(students)} students")
            sparse_matrix = SparseMatrix(len(activities), len(students))
            
            # Fill sparse matrix
            for i, activity in enumerate(activities):
                for j, student in enumerate(students):
                    if activity in grades_data and student in grades_data[activity]:
                        grade_value = grades_data[activity][student]
                        print(f"DEBUG: Setting matrix[{i}][{j}] = {grade_value} for activity '{activity}' and student '{student}'")
                        sparse_matrix.set_value(i, j, grade_value)
            
            # Store course information
            course_key = f"{course_code}_{tutor_id}"
            print(f"DEBUG: Course key: {course_key}")
            
            self.grades_data['courses'][course_key] = {
                'course_code': course_code,
                'course_name': course_name,
                'tutor_id': tutor_id,
                'activities': activities,
                'students': students,
                'upload_date': datetime.utcnow().isoformat(),
                'total_activities': len(activities),
                'total_students': len(students)
            }
            
            # Store sparse matrix data
            self.grades_data['sparse_matrices'][course_key] = {
                'matrix_data': sparse_matrix.get_non_zero_elements(),
                'rows': sparse_matrix.rows,
                'cols': sparse_matrix.cols,
                'density': sparse_matrix.get_density()
            }
            
            print(f"DEBUG: Saving data to storage")
            self._save_data()
            
            result = {
                'success': True,
                'course_code': course_code,
                'course_name': course_name,
                'activities_count': len(activities),
                'students_count': len(students),
                'matrix_density': sparse_matrix.get_density(),
                'upload_date': datetime.utcnow().isoformat()
            }
            
            print(f"DEBUG: Returning result: {result}")
            return result
            
        except ET.ParseError as e:
            print(f"DEBUG: ET.ParseError: {str(e)}")
            raise ValueError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            print(f"DEBUG: Exception in parse_grades_xml: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error parsing XML: {str(e)}")
    
    def get_course_grades(self, course_code, tutor_id):
        """Get grades for a specific course"""
        course_key = f"{course_code}_{tutor_id}"
        
        if course_key not in self.grades_data['courses']:
            return None
        
        course_info = self.grades_data['courses'][course_key]
        matrix_info = self.grades_data['sparse_matrices'][course_key]
        
        # Reconstruct sparse matrix using robust function
        sparse_matrix = create_sparse_matrix_from_data(matrix_info['rows'], matrix_info['cols'], matrix_info['matrix_data'])
        
        return {
            'course_info': course_info,
            'sparse_matrix': sparse_matrix,
            'matrix_info': matrix_info
        }
    
    def get_all_courses(self):
        """Get all courses with grades"""
        return self.grades_data['courses']
    
    def get_tutor_courses(self, tutor_id):
        """Get all courses for a specific tutor"""
        tutor_courses = {}
        for course_key, course_info in self.grades_data['courses'].items():
            if course_info['tutor_id'] == tutor_id:
                tutor_courses[course_key] = course_info
        return tutor_courses
    
    def generate_grade_report(self, course_code, tutor_id):
        """Generate a comprehensive grade report for a course"""
        course_data = self.get_course_grades(course_code, tutor_id)
        if not course_data:
            return None
        
        course_info = course_data['course_info']
        sparse_matrix = course_data['sparse_matrix']
        
        # Calculate statistics
        all_grades = []
        student_averages = {}
        activity_averages = {}
        
        # Collect all grades and calculate averages
        for row in range(sparse_matrix.rows):
            activity_grades = []
            for col in range(sparse_matrix.cols):
                grade = sparse_matrix.get_value(row, col)
                if grade > 0:
                    all_grades.append(grade)
                    activity_grades.append(grade)
                    
                    # Student average
                    student = course_info['students'][col]
                    if student not in student_averages:
                        student_averages[student] = []
                    student_averages[student].append(grade)
            
            # Activity average
            if activity_grades:
                activity_averages[course_info['activities'][row]] = sum(activity_grades) / len(activity_grades)
        
        # Calculate overall statistics
        if all_grades:
            overall_average = sum(all_grades) / len(all_grades)
            highest_grade = max(all_grades)
            lowest_grade = min(all_grades)
            passing_count = len([g for g in all_grades if g >= 60])
            passing_rate = (passing_count / len(all_grades)) * 100
        else:
            overall_average = highest_grade = lowest_grade = passing_rate = 0
        
        # Calculate student averages
        for student in student_averages:
            student_averages[student] = sum(student_averages[student]) / len(student_averages[student])
        
        return {
            'course_info': course_info,
            'statistics': {
                'overall_average': round(overall_average, 2),
                'highest_grade': highest_grade,
                'lowest_grade': lowest_grade,
                'passing_rate': round(passing_rate, 2),
                'total_grades': len(all_grades)
            },
            'student_averages': student_averages,
            'activity_averages': activity_averages,
            'matrix_density': sparse_matrix.get_density(),
            'report_date': datetime.utcnow().isoformat()
        }
    
    def delete_course_grades(self, course_code, tutor_id):
        """Delete grades for a specific course"""
        course_key = f"{course_code}_{tutor_id}"
        
        if course_key in self.grades_data['courses']:
            del self.grades_data['courses'][course_key]
        
        if course_key in self.grades_data['sparse_matrices']:
            del self.grades_data['sparse_matrices'][course_key]
        
        self._save_data()
        return True
    
    def get_storage_stats(self):
        """Get storage statistics"""
        total_courses = len(self.grades_data['courses'])
        total_matrices = len(self.grades_data['sparse_matrices'])
        
        total_activities = 0
        total_students = 0
        total_grades = 0
        
        for course_info in self.grades_data['courses'].values():
            total_activities += course_info.get('total_activities', 0)
            total_students += course_info.get('total_students', 0)
        
        for matrix_info in self.grades_data['sparse_matrices'].values():
            total_grades += len(matrix_info.get('matrix_data', {}))
        
        return {
            'total_courses': total_courses,
            'total_matrices': total_matrices,
            'total_activities': total_activities,
            'total_students': total_students,
            'total_grades': total_grades,
            'created_at': self.grades_data['metadata']['created_at'],
            'last_updated': self.grades_data['metadata']['last_updated']
        }

# Global instance
grades_storage = GradesStorage() 