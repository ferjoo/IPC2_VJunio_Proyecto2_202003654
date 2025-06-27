from app.utils.sparse_matrix import SparseMatrix
import bcrypt
from datetime import datetime

class StudentStorage:
    """
    Sistema de almacenamiento de estudiantes usando matrices dispersas.
    """
    
    def __init__(self):
        # Matriz principal para almacenar estudiantes
        # Dimensiones: (student_id, attribute_index)
        self.students_matrix = SparseMatrix(10000, 8)  # 10k estudiantes, 8 atributos
        
        # Matriz de índices para búsquedas rápidas
        # carnet -> student_id
        self.carnet_index = SparseMatrix(10000, 1)
        
        # Contador de estudiantes
        self.next_student_id = 1
        
        # Mapeo de atributos a índices de columna
        self.attribute_map = {
            'student_id': 0,
            'carnet': 1,
            'password_hash': 2,
            'nombre': 3,
            'is_active': 4,
            'is_admin': 5,
            'created_at': 6,
            'updated_at': 7
        }
    
    def _hash_password(self, password):
        """Hashea una contraseña usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _check_password(self, password, hashed):
        """Verifica una contraseña contra su hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _get_student_data(self, student_id):
        """Obtiene todos los datos de un estudiante desde la matriz"""
        if student_id <= 0 or student_id >= self.next_student_id:
            return None
        
        student_data = {}
        for attr, col_idx in self.attribute_map.items():
            value = self.students_matrix.get_value(student_id, col_idx)
            if value != 0:
                # Convertir de vuelta a tipos apropiados
                if attr in ['is_active', 'is_admin']:
                    student_data[attr] = bool(value)
                elif attr in ['created_at', 'updated_at']:
                    student_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr == 'student_id':
                    student_data[attr] = int(value)
                else:
                    student_data[attr] = str(value) if value else None
        
        return student_data if student_data else None
    
    def _store_student_data(self, student_id, student_data):
        """Almacena los datos de un estudiante en la matriz"""
        for attr, value in student_data.items():
            if attr in self.attribute_map:
                col_idx = self.attribute_map[attr]
                if value is not None:
                    # Convertir a formato numérico para almacenamiento
                    if isinstance(value, bool):
                        self.students_matrix.set_value(student_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.students_matrix.set_value(student_id, col_idx, value.isoformat())
                    else:
                        self.students_matrix.set_value(student_id, col_idx, str(value))
    
    def create_student(self, student_data):
        """Crea un nuevo estudiante"""
        try:
            # Validar datos requeridos
            carnet = student_data.get('carnet')
            password = student_data.get('password')
            nombre = student_data.get('nombre')
            
            if not carnet or not password or not nombre:
                raise ValueError("Carnet, contraseña y nombre son requeridos")
            
            # Verificar que el carnet no exista
            existing_student = self.get_student_by_carnet(carnet)
            if existing_student:
                raise ValueError(f"El estudiante con carnet {carnet} ya existe")
            
            # Crear nuevo estudiante
            student_id = self.next_student_id
            self.next_student_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            student_data['student_id'] = student_id
            student_data['created_at'] = now
            student_data['updated_at'] = now
            student_data['is_active'] = student_data.get('is_active', True)
            student_data['is_admin'] = student_data.get('is_admin', False)
            
            # Hashear contraseña
            student_data['password_hash'] = self._hash_password(password)
            del student_data['password']
            
            # Almacenar en matriz principal
            self._store_student_data(student_id, student_data)
            
            # Actualizar índice
            carnet_hash = hash(carnet) % 10000
            self.carnet_index.set_value(carnet_hash, 0, student_id)
            
            return self._get_student_data(student_id)
            
        except Exception as e:
            raise Exception(f"Error creando estudiante: {str(e)}")
    
    def get_student_by_id(self, student_id):
        """Obtiene un estudiante por ID"""
        return self._get_student_data(student_id)
    
    def get_student_by_carnet(self, carnet):
        """Obtiene un estudiante por carnet"""
        if not carnet:
            return None
        
        carnet_hash = hash(carnet) % 10000
        student_id = self.carnet_index.get_value(carnet_hash, 0)
        
        if student_id > 0:
            student_data = self._get_student_data(student_id)
            if student_data and student_data.get('carnet') == carnet:
                return student_data
        
        return None
    
    def get_all_students(self):
        """Obtiene todos los estudiantes"""
        students = []
        for student_id in range(1, self.next_student_id):
            student_data = self._get_student_data(student_id)
            if student_data:
                students.append(student_data)
        return students
    
    def authenticate_student(self, carnet, password):
        """Autentica un estudiante con carnet y contraseña"""
        student_data = self.get_student_by_carnet(carnet)
        if student_data and student_data.get('is_active'):
            stored_hash = student_data.get('password_hash')
            if stored_hash and self._check_password(password, stored_hash):
                return student_data
        return None
    
    def bulk_create_students(self, students_list):
        """Crea múltiples estudiantes de una vez"""
        try:
            created_students = []
            for student_data in students_list:
                created_student = self.create_student(student_data)
                created_students.append(created_student)
            
            return created_students
            
        except Exception as e:
            raise Exception(f"Error creando estudiantes masivamente: {str(e)}")
    
    def get_matrix_stats(self):
        """Obtiene estadísticas de las matrices"""
        return {
            'students_matrix_density': self.students_matrix.get_density(),
            'carnet_index_density': self.carnet_index.get_density(),
            'total_students': self.next_student_id - 1,
            'non_zero_students': len(self.students_matrix.get_non_zero_elements())
        } 