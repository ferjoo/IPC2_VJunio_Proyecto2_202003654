from app.models.user_storage import UserStorage
from marshmallow import ValidationError

class UserService:
    """Servicio para operaciones de usuarios usando almacenamiento en matrices dispersas"""
    
    def __init__(self):
        self.user_storage = UserStorage()
    
    def get_all_users(self):
        """Obtiene todos los usuarios"""
        return self.user_storage.get_all_users()
    
    def get_user_by_id(self, user_id):
        """Obtiene un usuario por ID"""
        return self.user_storage.get_user_by_id(user_id)
    
    def get_user_by_username(self, username):
        """Obtiene un usuario por username"""
        return self.user_storage.get_user_by_username(username)
    
    def get_user_by_email(self, email):
        """Obtiene un usuario por email"""
        return self.user_storage.get_user_by_email(email)
    
    def create_user(self, data):
        """Crea un nuevo usuario"""
        try:
            # Validar datos requeridos
            if not data.get('username'):
                raise ValidationError('Username es requerido')
            if not data.get('email'):
                raise ValidationError('Email es requerido')
            if not data.get('password'):
                raise ValidationError('Password es requerido')
            
            # Validar longitud de campos
            if len(data['username']) < 3:
                raise ValidationError('Username debe tener al menos 3 caracteres')
            if len(data['password']) < 4:
                raise ValidationError('Password debe tener al menos 4 caracteres')
            
            # Crear usuario usando el almacenamiento en matrices
            user = self.user_storage.create_user(data)
            return user
            
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error creando usuario: {str(e)}")
    
    def update_user(self, user_id, data):
        """Actualiza un usuario existente"""
        try:
            # Validar que el usuario existe
            existing_user = self.user_storage.get_user_by_id(user_id)
            if not existing_user:
                return None
            
            # Validar datos si se están actualizando
            if 'username' in data and len(data['username']) < 3:
                raise ValidationError('Username debe tener al menos 3 caracteres')
            if 'password' in data and len(data['password']) < 4:
                raise ValidationError('Password debe tener al menos 4 caracteres')
            
            # Actualizar usuario
            user = self.user_storage.update_user(user_id, data)
            return user
            
        except ValidationError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error actualizando usuario: {str(e)}")
    
    def delete_user(self, user_id):
        """Elimina un usuario"""
        try:
            success = self.user_storage.delete_user(user_id)
            return success
            
        except Exception as e:
            raise Exception(f"Error eliminando usuario: {str(e)}")
    
    def authenticate_user(self, username, password):
        """Autentica un usuario con username y contraseña"""
        return self.user_storage.authenticate_user(username, password)
    
    def get_storage_stats(self):
        """Obtiene estadísticas del almacenamiento"""
        return self.user_storage.get_matrix_stats() 