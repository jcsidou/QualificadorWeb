from django.urls import path
from . import views
from .views import add_person, qualificar_todos, remove_person

urlpatterns = [
    path('upload/', views.upload_file_view, name='upload_file'),
    path('alterar-condicao/<int:pessoa_id>/', views.alterar_condicao, name='alterar_condicao'),
    path('alterar-pessoa/<int:pessoa_id>/', views.alterar_pessoa, name='alterar_pessoa'),
    path('add-person-api-endpoint', add_person, name='add_person'),
    path('api/qualificar-todos', qualificar_todos, name='qualificar_todos'),
    path('remove-person/<int:id>/', remove_person, name='remove_person'),
]

