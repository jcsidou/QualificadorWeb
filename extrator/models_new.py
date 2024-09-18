

from django.db import models

# Definição das opções para sexo
SEXO_CHOICES = [
    ('Masculino', 'Masculino'),
    ('Feminino', 'Feminino'),
    ('Outro', 'Outro'),
]

# Definição das opções para cor da pele
COR_PELE_CHOICES = [
    ('Branca', 'Branca'),
    ('Preta', 'Preta'),
    ('Parda', 'Parda'),
    ('Mulata', 'Mulata'),
    ('Asiática', 'Asiática'),
]

# Definição das opções para condição
CONDICAO_CHOICES = [
    ('Agente', 'Agente'),
    ('Vítima', 'Vítima'),
    ('Testemunha', 'Testemunha'),
]

# Modelo para Pessoa
class Pessoa(models.Model):
    nome = models.CharField(max_length=255)  # Campo obrigatório
    nome_pai = models.CharField(max_length=255, blank=True, null=True)
    nome_mae = models.CharField(max_length=255, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=20, choices=SEXO_CHOICES, blank=True, null=True)
    cpf = models.CharField(max_length=20, blank=True, null=True)
    cor_pele = models.CharField(max_length=20, choices=COR_PELE_CHOICES, blank=True, null=True)
    estado_civil = models.CharField(max_length=20, blank=True, null=True)
    grau_instrucao = models.CharField(max_length=50, blank=True, null=True)
    naturalidade = models.CharField(max_length=100, blank=True, null=True)
    naturalidade_UF = models.CharField(max_length=2, blank=True, null=True)
    nacionalidade = models.CharField(max_length=50, blank=True, null=True)
    documento = models.CharField(max_length=50, blank=True, null=True)
    numero_documento = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nome

# Modelo para Fato
class Fato(models.Model):
    id = models.AutoField(primary_key=True)  # Campo chave primária
    data_fato = models.DateField()
    hora_fato = models.TimeField()
    local_fato = models.CharField(max_length=255)
    natureza_fato = models.CharField(max_length=255)
    tentado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.natureza_fato} - {self.data_fato}"

# Modelo para Ocorrência
class Ocorrencia(models.Model):
    no_orgao_op = models.CharField(max_length=6, verbose_name="Número do Órgão")
    orgao_op = models.TextField(verbose_name="Órgão")
    ano_op = models.CharField(max_length=4, verbose_name="Ano")
    no_op = models.CharField(max_length=8, verbose_name="Número da Ocorrência")
    data_registro = models.DateField(verbose_name="Data de Registro")
    hora_registro = models.TimeField(verbose_name="Hora de Registro")
    historico = models.TextField(verbose_name="Histórico")
    fatos = models.ManyToManyField(Fato, related_name="ocorrencias")  # Relacionamento com Fatos

    def __str__(self):
        return f"{self.no_op}/{self.ano_op} - {self.orgao_op}"

# Modelo para associar Pessoa com Ocorrência
class PessoaOcorrencia(models.Model):
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name="ocorrencias")
    ocorrencia = models.ForeignKey(Ocorrencia, on_delete=models.CASCADE, related_name="pessoas")
    condicao = models.CharField(max_length=255, choices=CONDICAO_CHOICES, blank=True, null=True)
    alcunha = models.CharField(max_length=255, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    end_profissional = models.CharField(max_length=255, blank=True, null=True)
    profissao = models.CharField(max_length=100, blank=True, null=True)
    representa = models.BooleanField(default=False, blank=True, null=True)
    requer_mpu = models.BooleanField(default=False, blank=True, null=True)
    telefone = models.CharField(max_length=100, blank=True, null=True)
    celular = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.pessoa.nome} - {self.ocorrencia.no_op}/{self.ocorrencia.ano_op}"

class FatoTipico(models.Model):
    id = models.AutoField(primary_key=True)  # Campo chave primária
    cdg_ssp = models.CharField(max_length=255)
    nomen_juris = models.CharField(max_length=255)
    dispositivo = models.TextField()
    infinitivo = models.TextField()
    conduta_singular = models.TextField()
    conduta_plural = models.TextField()
    pena_max_y = models.IntegerField()  # Anos da pena máxima
    pena_max_m = models.IntegerField()  # Meses da pena máxima
    pena_min_y = models.IntegerField()  # Anos da pena mínima
    pena_min_m = models.IntegerField()  # Meses da pena mínima

    violencia = models.BooleanField(default=False)
    grave_ameaca = models.BooleanField(default=False)
    imprescritivel = models.BooleanField(default=False)
    inafiancavel = models.BooleanField(default=False)
    admite_tentativa = models.BooleanField(default=False)

    prompt = models.TextField()

    def __str__(self):
        return f"{self.nomen_juris} ({self.cdg_ssp})"