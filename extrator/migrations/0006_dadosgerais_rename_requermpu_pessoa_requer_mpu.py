# Generated by Django 5.0.8 on 2024-08-31 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extrator', '0005_pessoa_celular_pessoa_email_pessoa_requermpu_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DadosGerais',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('no_orgao_op', models.CharField(max_length=6, verbose_name='Número do Órgão')),
                ('orgao_op', models.TextField(verbose_name='Órgão')),
                ('ano_op', models.CharField(max_length=4, verbose_name='Ano')),
                ('no_op', models.CharField(max_length=8, verbose_name='Número da Ocorrência')),
                ('data_registro', models.DateField(verbose_name='Data de Registro')),
                ('hora_registro', models.TimeField(verbose_name='Hora de Registro')),
                ('fato', models.TextField(verbose_name='Descrição do Fato')),
                ('data_fato', models.DateField(verbose_name='Data do Fato')),
                ('hora_fato', models.TimeField(verbose_name='Hora do Fato')),
                ('tipo_area', models.CharField(max_length=255, verbose_name='Tipo de Área')),
                ('consumacao', models.CharField(choices=[('Cons', 'Consumado'), ('Tent', 'Tentado')], max_length=10, verbose_name='Consumação')),
                ('endereco_fato', models.TextField(verbose_name='Endereço do Fato')),
                ('historico', models.TextField(verbose_name='Histórico')),
            ],
        ),
        migrations.RenameField(
            model_name='pessoa',
            old_name='requerMPU',
            new_name='requer_mpu',
        ),
    ]
