from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file_view, name='upload_file'),
    path('success/', views.upload_success_view, name='upload_success'),
    # path('alterar-condicao/<str:pessoa_id>/', views.alterar_condicao, name='alterar_condicao'),
    path('add-person/', views.add_person, name='add_person'),
    path('alterar-pessoa/<str:pessoa_id>/', views.alterar_pessoa, name='alterar_pessoa'),
    path('remove-person/<str:id>/', views.remove_person, name='remove_person'),
    path('atualizar_qualificacao/<int:pessoa_id>/', views.atualizar_qualificacao, name='atualizar_qualificacao'),
    path('extract_address_info/', views.extract_address_info, name='extract_address_info'),
]
