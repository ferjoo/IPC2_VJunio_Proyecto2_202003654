#!/usr/bin/env python3
"""
Script para inicializar la base de datos con usuarios de prueba.
Crea usuarios administradores y regulares para testing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.user_service import UserService

def init_database():
    """Inicializa la base de datos con usuarios de prueba"""
    app = create_app()
    
    with app.app_context():
        user_service = UserService()
        
        # Lista de usuarios de prueba
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@example.com',
                'password': 'admin123',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'is_admin': True,
                'is_active': True
            },
            {
                'username': 'tutor1',
                'email': 'tutor1@example.com',
                'password': 'tutor123',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'is_admin': False,
                'is_active': True
            },
            {
                'username': 'tutor2',
                'email': 'tutor2@example.com',
                'password': 'tutor123',
                'first_name': 'María',
                'last_name': 'García',
                'is_admin': False,
                'is_active': True
            },
            {
                'username': 'estudiante1',
                'email': 'estudiante1@example.com',
                'password': 'estudiante123',
                'first_name': 'Carlos',
                'last_name': 'López',
                'is_admin': False,
                'is_active': True
            },
            {
                'username': 'estudiante2',
                'email': 'estudiante2@example.com',
                'password': 'estudiante123',
                'first_name': 'Ana',
                'last_name': 'Martínez',
                'is_admin': False,
                'is_active': True
            }
        ]
        
        print("🚀 Inicializando base de datos...")
        
        created_users = []
        for user_data in test_users:
            try:
                # Verificar si el usuario ya existe
                existing_user = user_service.get_user_by_username(user_data['username'])
                if existing_user:
                    print(f"⚠️  Usuario {user_data['username']} ya existe, saltando...")
                    continue
                
                # Crear usuario
                user = user_service.create_user(user_data)
                created_users.append(user)
                print(f"✅ Usuario creado: {user['username']} (ID: {user['user_id']})")
                
            except Exception as e:
                print(f"❌ Error creando usuario {user_data['username']}: {str(e)}")
        
        # Mostrar estadísticas
        try:
            stats = user_service.get_storage_stats()
            print(f"\n📊 Estadísticas del sistema:")
            print(f"   - Total usuarios: {stats['total_users']}")
            print(f"   - Densidad matriz usuarios: {stats['users_matrix_density']:.2f}%")
            print(f"   - Densidad índice usernames: {stats['username_index_density']:.2f}%")
            print(f"   - Densidad índice emails: {stats['email_index_density']:.2f}%")
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {str(e)}")
        
        print(f"\n🎉 Inicialización completada!")
        print(f"   - Usuarios creados: {len(created_users)}")
        
        if created_users:
            print(f"\n🔑 Credenciales de acceso:")
            for user in created_users:
                if user['is_admin']:
                    print(f"   👑 ADMIN: {user['username']} / {user_data['password']}")
                else:
                    print(f"   👤 USER: {user['username']} / {user_data['password']}")

if __name__ == '__main__':
    init_database() 