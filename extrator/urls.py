from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file_view, name='upload_file'),
    path('success/', views.upload_success_view, name='upload_success'),
    path('add-person/', views.add_person, name='add_person'),
    path('alterar-pessoa/<str:pessoa_id>/', views.alterar_pessoa, name='alterar_pessoa'),
    path('alterar_dados_gerais/<str:no_op>/', views.alterar_dados_gerais, name='alterar_dados_gerais'),
    path('remove-person/<str:id>/', views.remove_person, name='remove_person'),
    # path('atualizar_qualificacao/<int:pessoa_id>/', views.atualizar_qualificacao, name='atualizar_qualificacao'),
    path('extract_address_info/', views.extract_address_info, name='extract_address_info'),
    path('buscar-dados-cpf/', views.buscar_dados_cpf, name='buscar_dados_cpf'),
    path('atualizar_qualificacao/<uuid:pessoa_id>/', views.atualizar_qualificacao, name='atualizar_qualificacao'),
    path('verificar-sessao/', views.verificar_sessao, name='verificar_sessao'),
]
