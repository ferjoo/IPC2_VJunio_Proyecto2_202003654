from app.utils.sparse_matrix import SparseMatrix
from datetime import datetime
import json

class ScheduleStorage:
    """
    Sistema de almacenamiento de horarios usando matrices dispersas.
    Almacena los horarios de tutoría por curso.
    """
    
    def __init__(self):
        # Matriz principal para almacenar horarios
        # Dimensiones: (schedule_id, attribute_index)
        self.schedules_matrix = SparseMatrix(10000, 8)  # 10k horarios, 8 atributos
        
        # Matriz de índices para búsquedas rápidas
        # codigo_curso -> schedule_ids
        self.course_index = SparseMatrix(10000, 1)
        # tutor_id -> schedule_ids
        self.tutor_index = SparseMatrix(10000, 1)
        
        # Contador de horarios
        self.next_schedule_id = 1
        
        # Mapeo de atributos a índices de columna
        self.attribute_map = {
            'schedule_id': 0,
            'codigo_curso': 1,
            'horario_inicio': 2,
            'horario_fin': 3,
            'tutor_id': 4,
            'upload_date': 5,
            'is_active': 6,
            'created_at': 7
        }
    
    def _get_schedule_data(self, schedule_id):
        """Obtiene todos los datos de un horario desde la matriz"""
        if schedule_id <= 0 or schedule_id >= self.next_schedule_id:
            return None
        
        schedule_data = {}
        for attr, col_idx in self.attribute_map.items():
            value = self.schedules_matrix.get_value(schedule_id, col_idx)
            if value != 0:
                # Convertir de vuelta a tipos apropiados
                if attr in ['is_active']:
                    schedule_data[attr] = bool(value)
                elif attr in ['created_at', 'upload_date']:
                    schedule_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr in ['schedule_id', 'tutor_id']:
                    schedule_data[attr] = int(value)
                else:
                    schedule_data[attr] = str(value) if value else None
        
        return schedule_data if schedule_data else None
    
    def _store_schedule_data(self, schedule_id, schedule_data):
        """Almacena los datos de un horario en la matriz"""
        for attr, value in schedule_data.items():
            if attr in self.attribute_map:
                col_idx = self.attribute_map[attr]
                if value is not None:
                    # Convertir a formato numérico para almacenamiento
                    if isinstance(value, bool):
                        self.schedules_matrix.set_value(schedule_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.schedules_matrix.set_value(schedule_id, col_idx, value.isoformat())
                    elif isinstance(value, int):
                        self.schedules_matrix.set_value(schedule_id, col_idx, str(value))
                    else:
                        self.schedules_matrix.set_value(schedule_id, col_idx, str(value))
    
    def create_schedule(self, schedule_data):
        """Crea un nuevo horario"""
        try:
            # Validar datos requeridos
            codigo_curso = schedule_data.get('codigo_curso')
            horario_inicio = schedule_data.get('horario_inicio')
            horario_fin = schedule_data.get('horario_fin')
            tutor_id = schedule_data.get('tutor_id')
            
            if not all([codigo_curso, horario_inicio, horario_fin, tutor_id]):
                raise ValueError("Todos los campos son requeridos: codigo_curso, horario_inicio, horario_fin, tutor_id")
            
            # Crear nuevo horario
            schedule_id = self.next_schedule_id
            self.next_schedule_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            schedule_data['schedule_id'] = schedule_id
            schedule_data['created_at'] = now
            schedule_data['upload_date'] = schedule_data.get('upload_date', now)
            schedule_data['is_active'] = schedule_data.get('is_active', True)
            
            # Almacenar en matriz principal
            self._store_schedule_data(schedule_id, schedule_data)
            
            # Actualizar índices
            course_hash = hash(codigo_curso) % 10000
            self.course_index.set_value(course_hash, 0, schedule_id)
            
            tutor_hash = hash(str(tutor_id)) % 10000
            self.tutor_index.set_value(tutor_hash, 0, schedule_id)
            
            return self._get_schedule_data(schedule_id)
            
        except Exception as e:
            raise Exception(f"Error creando horario: {str(e)}")
    
    def get_schedule_by_id(self, schedule_id):
        """Obtiene un horario por ID"""
        return self._get_schedule_data(schedule_id)
    
    def get_schedules_by_course(self, codigo_curso):
        """Obtiene todos los horarios de un curso específico"""
        if not codigo_curso:
            return []
        
        schedules = []
        course_hash = hash(codigo_curso) % 10000
        schedule_id = self.course_index.get_value(course_hash, 0)
        
        if schedule_id > 0:
            schedule_data = self._get_schedule_data(schedule_id)
            if schedule_data and schedule_data.get('codigo_curso') == codigo_curso:
                schedules.append(schedule_data)
        
        return schedules
    
    def get_schedules_by_tutor(self, tutor_id):
        """Obtiene todos los horarios de un tutor específico"""
        if not tutor_id:
            return []
        
        schedules = []
        tutor_hash = hash(str(tutor_id)) % 10000
        schedule_id = self.tutor_index.get_value(tutor_hash, 0)
        
        if schedule_id > 0:
            schedule_data = self._get_schedule_data(schedule_id)
            if schedule_data and schedule_data.get('tutor_id') == tutor_id:
                schedules.append(schedule_data)
        
        return schedules
    
    def get_all_schedules(self):
        """Obtiene todos los horarios"""
        schedules = []
        for schedule_id in range(1, self.next_schedule_id):
            schedule_data = self._get_schedule_data(schedule_id)
            if schedule_data:
                schedules.append(schedule_data)
        return schedules
    
    def update_schedule(self, schedule_id, update_data):
        """Actualiza un horario existente"""
        try:
            schedule_data = self._get_schedule_data(schedule_id)
            if not schedule_data:
                return None
            
            # Actualizar datos
            schedule_data.update(update_data)
            schedule_data['upload_date'] = datetime.utcnow()
            
            # Almacenar datos actualizados
            self._store_schedule_data(schedule_id, schedule_data)
            
            return schedule_data
            
        except Exception as e:
            raise Exception(f"Error actualizando horario: {str(e)}")
    
    def delete_schedule(self, schedule_id):
        """Elimina un horario"""
        try:
            schedule_data = self._get_schedule_data(schedule_id)
            if not schedule_data:
                return False
            
            # Limpiar datos de la matriz principal
            for col_idx in self.attribute_map.values():
                self.schedules_matrix.set_value(schedule_id, col_idx, 0)
            
            # Limpiar índices
            codigo_curso = schedule_data.get('codigo_curso')
            tutor_id = schedule_data.get('tutor_id')
            
            if codigo_curso:
                course_hash = hash(codigo_curso) % 10000
                self.course_index.set_value(course_hash, 0, 0)
            
            if tutor_id:
                tutor_hash = hash(str(tutor_id)) % 10000
                self.tutor_index.set_value(tutor_hash, 0, 0)
            
            return True
            
        except Exception as e:
            raise Exception(f"Error eliminando horario: {str(e)}")
    
    def bulk_create_schedules(self, schedules_list):
        """Crea múltiples horarios de una vez"""
        try:
            created_schedules = []
            for schedule_data in schedules_list:
                created_schedule = self.create_schedule(schedule_data)
                created_schedules.append(created_schedule)
            
            return created_schedules
            
        except Exception as e:
            raise Exception(f"Error creando horarios masivamente: {str(e)}")
    
    def get_matrix_stats(self):
        """Obtiene estadísticas de las matrices"""
        return {
            'schedules_matrix_density': self.schedules_matrix.get_density(),
            'course_index_density': self.course_index.get_density(),
            'tutor_index_density': self.tutor_index.get_density(),
            'total_schedules': self.next_schedule_id - 1,
            'non_zero_schedules': len(self.schedules_matrix.get_non_zero_elements())
        } 