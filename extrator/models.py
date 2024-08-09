from django.db import models

class Pessoa(models.Model):
    CONDICOES = [
        ('Agente', 'Agente'),
        ('Vítima', 'Vítima'),
        ('Testemunha', 'Testemunha'),
        # Adicione outras condições necessárias
    ]
    SEXOS = [('Masculino', 'Masculino'), ('Feminino', 'Feminino'), ('Outro', 'Outro')]
    ESTADOS_CIVIS = [('Casado', 'Casado'), ('Solteiro', 'Solteiro')]
    GRAUS_INSTRUCAO = [('Ensino Fundamental Incompleto', 'Ensino Fundamental Incompleto')]
    CORES_PELE = [('Preta', 'Preta'), ('Branca', 'Branca'),('Pardo', 'Pardo'), ('Mulato', 'Mulato')  ]

    condicao = models.CharField(max_length=255, blank=True, null=True)
    alcunha = models.CharField(max_length=255, blank=True, null=True)
    nome = models.CharField(max_length=255)  # Campo obrigatório
    nome_pai = models.CharField(max_length=255, blank=True, null=True)
    nome_mae = models.CharField(max_length=255, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=20, blank=True, null=True)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    cor_pele = models.CharField(max_length=20, blank=True, null=True)
    estado_civil = models.CharField(max_length=20, blank=True, null=True)
    grau_instrucao = models.CharField(max_length=50, blank=True, null=True)
    naturalidade = models.CharField(max_length=100, blank=True, null=True)
    naturalidade_UF = models.CharField(max_length=2, blank=True, null=True)
    nacionalidade = models.CharField(max_length=50, blank=True, null=True)
    documento = models.CharField(max_length=50, blank=True, null=True)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    end_profissional = models.CharField(max_length=255, blank=True, null=True)
    profissao = models.CharField(max_length=100, blank=True, null=True)
    representa = models.BooleanField(default=False, blank=True, null=True)
    
    def __str__(self):
        return self.nome if self.nome else "Pessoa sem nome"
