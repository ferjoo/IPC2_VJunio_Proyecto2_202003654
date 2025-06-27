from app.utils.sparse_matrix import SparseMatrix
from datetime import datetime

class AssignmentStorage:
    """
    Sistema de almacenamiento de asignaciones usando matrices dispersas.
    Maneja asignaciones tutor-curso y estudiante-curso.
    """
    
    def __init__(self):
        # Matriz principal para asignaciones tutor-curso
        # Dimensiones: (assignment_id, attribute_index)
        self.tutor_course_matrix = SparseMatrix(10000, 6)  # 10k asignaciones, 6 atributos
        
        # Matriz principal para asignaciones estudiante-curso
        self.student_course_matrix = SparseMatrix(10000, 6)  # 10k asignaciones, 6 atributos
        
        # Matriz de índices para búsquedas rápidas
        # tutor_id -> assignment_ids
        self.tutor_index = SparseMatrix(10000, 1)
        # student_id -> assignment_ids
        self.student_index = SparseMatrix(10000, 1)
        # course_code -> assignment_ids
        self.course_index = SparseMatrix(10000, 1)
        
        # Contadores
        self.next_tutor_assignment_id = 1
        self.next_student_assignment_id = 1
        
        # Mapeo de atributos para asignaciones tutor-curso
        self.tutor_assignment_map = {
            'assignment_id': 0,
            'tutor_id': 1,
            'course_code': 2,
            'is_active': 3,
            'created_at': 4,
            'updated_at': 5
        }
        
        # Mapeo de atributos para asignaciones estudiante-curso
        self.student_assignment_map = {
            'assignment_id': 0,
            'student_id': 1,
            'course_code': 2,
            'is_active': 3,
            'created_at': 4,
            'updated_at': 5
        }
    
    def _get_tutor_assignment_data(self, assignment_id):
        """Obtiene datos de asignación tutor-curso desde la matriz"""
        if assignment_id <= 0 or assignment_id >= self.next_tutor_assignment_id:
            return None
        
        assignment_data = {}
        for attr, col_idx in self.tutor_assignment_map.items():
            value = self.tutor_course_matrix.get_value(assignment_id, col_idx)
            if value != 0:
                if attr in ['is_active']:
                    assignment_data[attr] = bool(value)
                elif attr in ['created_at', 'updated_at']:
                    assignment_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr == 'assignment_id':
                    assignment_data[attr] = int(value)
                else:
                    assignment_data[attr] = str(value) if value else None
        
        return assignment_data if assignment_data else None
    
    def _get_student_assignment_data(self, assignment_id):
        """Obtiene datos de asignación estudiante-curso desde la matriz"""
        if assignment_id <= 0 or assignment_id >= self.next_student_assignment_id:
            return None
        
        assignment_data = {}
        for attr, col_idx in self.student_assignment_map.items():
            value = self.student_course_matrix.get_value(assignment_id, col_idx)
            if value != 0:
                if attr in ['is_active']:
                    assignment_data[attr] = bool(value)
                elif attr in ['created_at', 'updated_at']:
                    assignment_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr == 'assignment_id':
                    assignment_data[attr] = int(value)
                else:
                    assignment_data[attr] = str(value) if value else None
        
        return assignment_data if assignment_data else None
    
    def _store_tutor_assignment_data(self, assignment_id, assignment_data):
        """Almacena datos de asignación tutor-curso en la matriz"""
        for attr, value in assignment_data.items():
            if attr in self.tutor_assignment_map:
                col_idx = self.tutor_assignment_map[attr]
                if value is not None:
                    if isinstance(value, bool):
                        self.tutor_course_matrix.set_value(assignment_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.tutor_course_matrix.set_value(assignment_id, col_idx, value.isoformat())
                    else:
                        self.tutor_course_matrix.set_value(assignment_id, col_idx, str(value))
    
    def _store_student_assignment_data(self, assignment_id, assignment_data):
        """Almacena datos de asignación estudiante-curso en la matriz"""
        for attr, value in assignment_data.items():
            if attr in self.student_assignment_map:
                col_idx = self.student_assignment_map[attr]
                if value is not None:
                    if isinstance(value, bool):
                        self.student_course_matrix.set_value(assignment_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.student_course_matrix.set_value(assignment_id, col_idx, value.isoformat())
                    else:
                        self.student_course_matrix.set_value(assignment_id, col_idx, str(value))
    
    def create_tutor_course_assignment(self, tutor_id, course_code):
        """Crea una asignación tutor-curso"""
        try:
            # Verificar que no exista la asignación
            existing_assignments = self.get_tutor_assignments(tutor_id)
            for assignment in existing_assignments:
                if assignment.get('course_code') == course_code:
                    raise ValueError(f"El tutor {tutor_id} ya está asignado al curso {course_code}")
            
            # Crear nueva asignación
            assignment_id = self.next_tutor_assignment_id
            self.next_tutor_assignment_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            assignment_data = {
                'assignment_id': assignment_id,
                'tutor_id': tutor_id,
                'course_code': course_code,
                'is_active': True,
                'created_at': now,
                'updated_at': now
            }
            
            # Almacenar en matriz
            self._store_tutor_assignment_data(assignment_id, assignment_data)
            
            # Actualizar índices
            tutor_hash = hash(str(tutor_id)) % 10000
            self.tutor_index.set_value(tutor_hash, 0, assignment_id)
            
            course_hash = hash(course_code) % 10000
            self.course_index.set_value(course_hash, 0, assignment_id)
            
            return self._get_tutor_assignment_data(assignment_id)
            
        except Exception as e:
            raise Exception(f"Error creando asignación tutor-curso: {str(e)}")
    
    def create_student_course_assignment(self, student_id, course_code):
        """Crea una asignación estudiante-curso"""
        try:
            # Verificar que no exista la asignación
            existing_assignments = self.get_student_assignments(student_id)
            for assignment in existing_assignments:
                if assignment.get('course_code') == course_code:
                    raise ValueError(f"El estudiante {student_id} ya está asignado al curso {course_code}")
            
            # Crear nueva asignación
            assignment_id = self.next_student_assignment_id
            self.next_student_assignment_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            assignment_data = {
                'assignment_id': assignment_id,
                'student_id': student_id,
                'course_code': course_code,
                'is_active': True,
                'created_at': now,
                'updated_at': now
            }
            
            # Almacenar en matriz
            self._store_student_assignment_data(assignment_id, assignment_data)
            
            # Actualizar índices
            student_hash = hash(str(student_id)) % 10000
            self.student_index.set_value(student_hash, 0, assignment_id)
            
            course_hash = hash(course_code) % 10000
            self.course_index.set_value(course_hash, 0, assignment_id)
            
            return self._get_student_assignment_data(assignment_id)
            
        except Exception as e:
            raise Exception(f"Error creando asignación estudiante-curso: {str(e)}")
    
    def get_tutor_assignments(self, tutor_id):
        """Obtiene todas las asignaciones de un tutor"""
        assignments = []
        for assignment_id in range(1, self.next_tutor_assignment_id):
            assignment_data = self._get_tutor_assignment_data(assignment_id)
            if assignment_data and assignment_data.get('tutor_id') == str(tutor_id):
                assignments.append(assignment_data)
        return assignments
    
    def get_student_assignments(self, student_id):
        """Obtiene todas las asignaciones de un estudiante"""
        assignments = []
        for assignment_id in range(1, self.next_student_assignment_id):
            assignment_data = self._get_student_assignment_data(assignment_id)
            if assignment_data and assignment_data.get('student_id') == str(student_id):
                assignments.append(assignment_data)
        return assignments
    
    def get_course_assignments(self, course_code):
        """Obtiene todas las asignaciones de un curso"""
        tutor_assignments = []
        student_assignments = []
        
        # Buscar asignaciones de tutores
        for assignment_id in range(1, self.next_tutor_assignment_id):
            assignment_data = self._get_tutor_assignment_data(assignment_id)
            if assignment_data and assignment_data.get('course_code') == course_code:
                tutor_assignments.append(assignment_data)
        
        # Buscar asignaciones de estudiantes
        for assignment_id in range(1, self.next_student_assignment_id):
            assignment_data = self._get_student_assignment_data(assignment_id)
            if assignment_data and assignment_data.get('course_code') == course_code:
                student_assignments.append(assignment_data)
        
        return {
            'tutor_assignments': tutor_assignments,
            'student_assignments': student_assignments
        }
    
    def get_all_tutor_assignments(self):
        """Obtiene todas las asignaciones tutor-curso"""
        assignments = []
        for assignment_id in range(1, self.next_tutor_assignment_id):
            assignment_data = self._get_tutor_assignment_data(assignment_id)
            if assignment_data:
                assignments.append(assignment_data)
        return assignments
    
    def get_all_student_assignments(self):
        """Obtiene todas las asignaciones estudiante-curso"""
        assignments = []
        for assignment_id in range(1, self.next_student_assignment_id):
            assignment_data = self._get_student_assignment_data(assignment_id)
            if assignment_data:
                assignments.append(assignment_data)
        return assignments
    
    def get_matrix_stats(self):
        """Obtiene estadísticas de las matrices"""
        return {
            'tutor_course_matrix_density': self.tutor_course_matrix.get_density(),
            'student_course_matrix_density': self.student_course_matrix.get_density(),
            'tutor_index_density': self.tutor_index.get_density(),
            'student_index_density': self.student_index.get_density(),
            'course_index_density': self.course_index.get_density(),
            'total_tutor_assignments': self.next_tutor_assignment_id - 1,
            'total_student_assignments': self.next_student_assignment_id - 1,
            'non_zero_tutor_assignments': len(self.tutor_course_matrix.get_non_zero_elements()),
            'non_zero_student_assignments': len(self.student_course_matrix.get_non_zero_elements())
        } 