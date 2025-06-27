app_name = 'main'

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tutor/dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('tutor/notas/', views.tutor_notas, name='tutor_notas'),
    path('debug/schedules/', views.debug_schedules, name='debug_schedules'),
    path('logout/', views.logout_view, name='logout'),
    path('ver-usuarios/', views.ver_usuarios, name='ver_usuarios'),
    path('usuario/<str:role>/<int:id>/', views.usuario_detalle, name='usuario_detalle'),
    path('mi-informacion/', views.mi_informacion, name='mi_informacion'),
    path('tutor/horarios/', views.tutor_horarios, name='tutor_horarios'),
    path('tutor/reportes/', views.tutor_reportes, name='tutor_reportes'),
    path('tutor/reportes/<str:course_code>/', views.tutor_reporte_svg, name='tutor_reporte_svg'),
    path('tutor/reportes/<str:course_code>/descargar/', views.tutor_reporte_svg_descargar, name='tutor_reporte_svg_descargar'),
    # API endpoints for grades
    path('api/grades/courses/', views.grades_courses_api, name='grades_courses_api'),
    path('api/grades/course/<str:course_code>/', views.grades_course_api, name='grades_course_api'),
    path('api/reports/grades/', views.grades_report_api, name='grades_report_api'),
] 