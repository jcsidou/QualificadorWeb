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
    requer_mpu = models.BooleanField(default=False, blank=True, null=True)
    telefone = models.CharField(max_length=100, blank=True, null=True)
    celular = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.nome if self.nome else "Nome não informado"

class DadosGerais(models.Model):
    no_orgao_op = models.CharField(max_length=6, verbose_name="Número do Órgão")
    orgao_op = models.TextField(verbose_name="Órgão")
    ano_op = models.CharField(max_length=4, verbose_name="Ano")
    no_op = models.CharField(max_length=8, verbose_name="Número da Ocorrência")
    data_registro = models.DateField(verbose_name="Data de Registro")
    hora_registro = models.TimeField(verbose_name="Hora de Registro")
    fato = models.TextField(verbose_name="Descrição do Fato")
    data_fato = models.DateField(verbose_name="Data do Fato")
    hora_fato = models.TimeField(verbose_name="Hora do Fato")
    tipo_area = models.CharField(max_length=255, verbose_name="Tipo de Área")
    consumacao = models.CharField(max_length=10, choices=[('Cons', 'Consumado'), ('Tent', 'Tentado')], verbose_name="Consumação")
    endereco_fato = models.TextField(verbose_name="Endereço do Fato")
    historico = models.TextField(verbose_name="Histórico")

    def __str__(self):
        return f'Ocorrência {self.no_orgao_op}/{self.no_op}/{self.ano_op}'