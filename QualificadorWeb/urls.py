from django.contrib import admin
from django.urls import include, path
from extrator import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('extrator/', include('extrator.urls')),
    path('', views.upload_file_view, name='home'),  # Define a rota padrão
]
