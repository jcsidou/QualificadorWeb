from django.contrib import admin
from django.urls import include, path
from extrator import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('extrator/', include('extrator.urls')),
    path('', views.upload_file_view, name='home'),
    path('api/qualificar-todos', views.qualificar_todos, name='qualificar_todos'),
    path('extrator/remove-person/<int:id>/', views.remove_person, name='remove_person'),
    path('extrator/qualificar_pessoa/<int:pessoa_id>/', views.qualificar_pessoa, name='qualificar_pessoa'),
]
