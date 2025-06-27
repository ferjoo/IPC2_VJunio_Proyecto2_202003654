from app.utils.sparse_matrix import SparseMatrix
import json
import hashlib
import bcrypt
from datetime import datetime

class UserStorage:
    """
    Sistema de almacenamiento de usuarios usando matrices dispersas.
    No utiliza SQL, todo se maneja en memoria con matrices dispersas.
    """
    
    def __init__(self):
        # Matriz principal para almacenar usuarios
        # Dimensiones: (user_id, attribute_index)
        self.users_matrix = SparseMatrix(10000, 10)  # 10k usuarios, 10 atributos
        
        # Matriz de índices para búsquedas rápidas
        # username -> user_id
        self.username_index = SparseMatrix(10000, 1)
        # email -> user_id  
        self.email_index = SparseMatrix(10000, 1)
        
        # Contador de usuarios
        self.next_user_id = 1
        
        # Mapeo de atributos a índices de columna
        self.attribute_map = {
            'username': 0,
            'email': 1,
            'password_hash': 2,
            'first_name': 3,
            'last_name': 4,
            'is_active': 5,
            'is_admin': 6,
            'created_at': 7,
            'updated_at': 8,
            'user_id': 9
        }
    
    def _hash_password(self, password):
        """Hashea una contraseña usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _check_password(self, password, hashed):
        """Verifica una contraseña contra su hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _get_user_data(self, user_id):
        """Obtiene todos los datos de un usuario desde la matriz"""
        if user_id <= 0 or user_id >= self.next_user_id:
            return None
        
        user_data = {}
        for attr, col_idx in self.attribute_map.items():
            value = self.users_matrix.get_value(user_id, col_idx)
            if value != 0:
                # Convertir de vuelta a tipos apropiados
                if attr in ['is_active', 'is_admin']:
                    user_data[attr] = bool(value)
                elif attr in ['created_at', 'updated_at']:
                    user_data[attr] = datetime.fromisoformat(str(value)) if value else None
                elif attr == 'user_id':
                    user_data[attr] = int(value)
                else:
                    user_data[attr] = str(value) if value else None
        
        return user_data if user_data else None
    
    def _store_user_data(self, user_id, user_data):
        """Almacena los datos de un usuario en la matriz"""
        for attr, value in user_data.items():
            if attr in self.attribute_map:
                col_idx = self.attribute_map[attr]
                if value is not None:
                    # Convertir a formato numérico para almacenamiento
                    if isinstance(value, bool):
                        self.users_matrix.set_value(user_id, col_idx, 1 if value else 0)
                    elif isinstance(value, datetime):
                        self.users_matrix.set_value(user_id, col_idx, value.isoformat())
                    else:
                        self.users_matrix.set_value(user_id, col_idx, str(value))
    
    def create_user(self, user_data):
        """Crea un nuevo usuario"""
        try:
            # Verificar que username y email no existan
            username = user_data.get('username')
            email = user_data.get('email')
            
            if not username or not email:
                raise ValueError("Username y email son requeridos")
            
            # Buscar si ya existe
            existing_user = self.get_user_by_username(username)
            if existing_user:
                raise ValueError("Username ya existe")
            
            existing_user = self.get_user_by_email(email)
            if existing_user:
                raise ValueError("Email ya existe")
            
            # Crear nuevo usuario
            user_id = self.next_user_id
            self.next_user_id += 1
            
            # Preparar datos
            now = datetime.utcnow()
            user_data['user_id'] = user_id
            user_data['created_at'] = now
            user_data['updated_at'] = now
            user_data['is_active'] = user_data.get('is_active', True)
            user_data['is_admin'] = user_data.get('is_admin', False)
            
            # Hashear contraseña si se proporciona
            if 'password' in user_data:
                user_data['password_hash'] = self._hash_password(user_data['password'])
                del user_data['password']
            
            # Almacenar en matriz principal
            self._store_user_data(user_id, user_data)
            
            # Actualizar índices
            self.username_index.set_value(hash(username) % 10000, 0, user_id)
            self.email_index.set_value(hash(email) % 10000, 0, user_id)
            
            return self._get_user_data(user_id)
            
        except Exception as e:
            raise Exception(f"Error creando usuario: {str(e)}")
    
    def get_user_by_id(self, user_id):
        """Obtiene un usuario por ID"""
        return self._get_user_data(user_id)
    
    def get_user_by_username(self, username):
        """Obtiene un usuario por username"""
        if not username:
            return None
        
        # Buscar en índice de usernames
        hash_value = hash(username) % 10000
        user_id = self.username_index.get_value(hash_value, 0)
        
        if user_id > 0:
            user_data = self._get_user_data(user_id)
            if user_data and user_data.get('username') == username:
                return user_data
        
        return None
    
    def get_user_by_email(self, email):
        """Obtiene un usuario por email"""
        if not email:
            return None
        
        # Buscar en índice de emails
        hash_value = hash(email) % 10000
        user_id = self.email_index.get_value(hash_value, 0)
        
        if user_id > 0:
            user_data = self._get_user_data(user_id)
            if user_data and user_data.get('email') == email:
                return user_data
        
        return None
    
    def get_all_users(self):
        """Obtiene todos los usuarios"""
        users = []
        for user_id in range(1, self.next_user_id):
            user_data = self._get_user_data(user_id)
            if user_data:
                users.append(user_data)
        return users
    
    def update_user(self, user_id, update_data):
        """Actualiza un usuario existente"""
        try:
            user_data = self._get_user_data(user_id)
            if not user_data:
                return None
            
            # Verificar unicidad de username/email si se están actualizando
            if 'username' in update_data:
                existing = self.get_user_by_username(update_data['username'])
                if existing and existing['user_id'] != user_id:
                    raise ValueError("Username ya existe")
            
            if 'email' in update_data:
                existing = self.get_user_by_email(update_data['email'])
                if existing and existing['user_id'] != user_id:
                    raise ValueError("Email ya existe")
            
            # Actualizar datos
            user_data.update(update_data)
            user_data['updated_at'] = datetime.utcnow()
            
            # Hashear nueva contraseña si se proporciona
            if 'password' in user_data:
                user_data['password_hash'] = self._hash_password(user_data['password'])
                del user_data['password']
            
            # Almacenar datos actualizados
            self._store_user_data(user_id, user_data)
            
            # Actualizar índices si username o email cambiaron
            if 'username' in update_data:
                old_username = user_data.get('username')
                if old_username:
                    self.username_index.set_value(hash(update_data['username']) % 10000, 0, user_id)
            
            if 'email' in update_data:
                old_email = user_data.get('email')
                if old_email:
                    self.email_index.set_value(hash(update_data['email']) % 10000, 0, user_id)
            
            return user_data
            
        except Exception as e:
            raise Exception(f"Error actualizando usuario: {str(e)}")
    
    def delete_user(self, user_id):
        """Elimina un usuario"""
        try:
            user_data = self._get_user_data(user_id)
            if not user_data:
                return False
            
            # Limpiar datos de la matriz principal
            for col_idx in self.attribute_map.values():
                self.users_matrix.set_value(user_id, col_idx, 0)
            
            # Limpiar índices
            username = user_data.get('username')
            email = user_data.get('email')
            
            if username:
                self.username_index.set_value(hash(username) % 10000, 0, 0)
            if email:
                self.email_index.set_value(hash(email) % 10000, 0, 0)
            
            return True
            
        except Exception as e:
            raise Exception(f"Error eliminando usuario: {str(e)}")
    
    def authenticate_user(self, username, password):
        """Autentica un usuario con username y contraseña"""
        user_data = self.get_user_by_username(username)
        if user_data and user_data.get('is_active'):
            stored_hash = user_data.get('password_hash')
            if stored_hash and self._check_password(password, stored_hash):
                return user_data
        return None
    
    def get_matrix_stats(self):
        """Obtiene estadísticas de las matrices"""
        return {
            'users_matrix_density': self.users_matrix.get_density(),
            'username_index_density': self.username_index.get_density(),
            'email_index_density': self.email_index.get_density(),
            'total_users': self.next_user_id - 1,
            'non_zero_users': len(self.users_matrix.get_non_zero_elements())
        } 