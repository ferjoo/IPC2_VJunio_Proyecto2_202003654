from app.utils.sparse_matrix import SparseMatrix
from datetime import datetime

class CourseStorage:
    """
    Sistema de almacenamiento de cursos usando matrices dispersas.
    """
    
    def __init__(self):
        # Matriz principal para almacenar cursos
        # Dimensiones: (course_id, attribute_index)
        self.courses_matrix = SparseMatrix(10000, 5)  # 10k cursos, 5 atributos
        
        # Matriz de índices para búsquedas rápidas
        # codigo_curso -> course_id
        self.course_code_index = SparseMatrix(10000, 1)
        
        # Contador de cursos
        self.next_course_id = 1
        
        # Mapeo de atributos a índices de columna
        self.attribute_map = {
            'course_id': 0,
            'codigo': 1,
            'nombre': 2,
            'is_active': 3,
            'created_at': 4
        }
    
    def _get_course_data(self, course_id):
        """Obtiene todos los datos de un curso desde la matriz"""
        if course_id <= 0 or course_id >= self.next_course_id:
            return None
        
        course_data = {}
        for attr, col_idx in self.attribute_map.items():
            value = self.courses_matrix.get_value(course_id, col_idx)
            if value != 0:
                # Convertir de vuelta a tipos apropiados
                if attr in ['is_active']:
                    course_data[attr] = bool(value)
                elif attr in ['created_at']:
                    course_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr == 'course_id':
                    course_data[attr] = int(value)
                else:
                    course_data[attr] = str(value) if value else None
        
        return course_data if course_data else None
    
    def _store_course_data(self, course_id, course_data):
        """Almacena los datos de un curso en la matriz"""
        for attr, value in course_data.items():
            if attr in self.attribute_map:
                col_idx = self.attribute_map[attr]
                if value is not None:
                    # Convertir a formato numérico para almacenamiento
                    if isinstance(value, bool):
                        self.courses_matrix.set_value(course_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.courses_matrix.set_value(course_id, col_idx, value.isoformat())
                    else:
                        self.courses_matrix.set_value(course_id, col_idx, str(value))
    
    def create_course(self, course_data):
        """Crea un nuevo curso"""
        try:
            # Validar datos requeridos
            codigo = course_data.get('codigo')
            nombre = course_data.get('nombre')
            
            if not codigo or not nombre:
                raise ValueError("Código y nombre del curso son requeridos")
            
            # Verificar que el código no exista
            existing_course = self.get_course_by_code(codigo)
            if existing_course:
                raise ValueError(f"El curso con código {codigo} ya existe")
            
            # Crear nuevo curso
            course_id = self.next_course_id
            self.next_course_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            course_data['course_id'] = course_id
            course_data['created_at'] = now
            course_data['is_active'] = course_data.get('is_active', True)
            
            # Almacenar en matriz principal
            self._store_course_data(course_id, course_data)
            
            # Actualizar índice
            course_hash = hash(codigo) % 10000
            self.course_code_index.set_value(course_hash, 0, course_id)
            
            return self._get_course_data(course_id)
            
        except Exception as e:
            raise Exception(f"Error creando curso: {str(e)}")
    
    def get_course_by_id(self, course_id):
        """Obtiene un curso por ID"""
        return self._get_course_data(course_id)
    
    def get_course_by_code(self, codigo):
        """Obtiene un curso por código"""
        if not codigo:
            return None
        
        course_hash = hash(codigo) % 10000
        course_id = self.course_code_index.get_value(course_hash, 0)
        
        if course_id > 0:
            course_data = self._get_course_data(course_id)
            if course_data and course_data.get('codigo') == codigo:
                return course_data
        
        # If hash lookup failed, do a linear search through all courses
        # This handles hash collisions
        all_courses = self.get_all_courses()
        for course in all_courses:
            if course.get('codigo') == codigo:
                return course
        
        return None
    
    def get_all_courses(self):
        """Obtiene todos los cursos"""
        courses = []
        for course_id in range(1, self.next_course_id):
            course_data = self._get_course_data(course_id)
            if course_data:
                courses.append(course_data)
        return courses
    
    def bulk_create_courses(self, courses_list):
        """Crea múltiples cursos de una vez"""
        try:
            created_courses = []
            for course_data in courses_list:
                created_course = self.create_course(course_data)
                created_courses.append(created_course)
            
            return created_courses
            
        except Exception as e:
            raise Exception(f"Error creando cursos masivamente: {str(e)}")
    
    def get_matrix_stats(self):
        """Obtiene estadísticas de las matrices"""
        return {
            'courses_matrix_density': self.courses_matrix.get_density(),
            'course_code_index_density': self.course_code_index.get_density(),
            'total_courses': self.next_course_id - 1,
            'non_zero_courses': len(self.courses_matrix.get_non_zero_elements())
        } 