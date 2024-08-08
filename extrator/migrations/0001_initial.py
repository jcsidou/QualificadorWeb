# Generated by Django 5.0.8 on 2024-08-07 02:31

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Pessoa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('condicao', models.CharField(choices=[('Indiciado Presente', 'Indiciado Presente'), ('Vítima', 'Vítima'), ('Testemunha', 'Testemunha')], max_length=50)),
                ('nome', models.CharField(max_length=100)),
                ('alcunha', models.CharField(blank=True, max_length=50)),
                ('nome_pai', models.CharField(max_length=100)),
                ('nome_mae', models.CharField(max_length=100)),
                ('data_nascimento', models.DateField()),
                ('sexo', models.CharField(choices=[('Masculino', 'Masculino'), ('Feminino', 'Feminino')], max_length=10)),
                ('cpf', models.CharField(max_length=14)),
                ('estado_civil', models.CharField(choices=[('Casado', 'Casado'), ('Solteiro', 'Solteiro')], max_length=10)),
                ('grau_instrucao', models.CharField(choices=[('Ensino Fundamental Incompleto', 'Ensino Fundamental Incompleto')], max_length=50)),
                ('cor_pele', models.CharField(choices=[('Preta', 'Preta'), ('Branca', 'Branca')], max_length=10)),
                ('naturalidade', models.CharField(max_length=50)),
                ('nacionalidade', models.CharField(max_length=50)),
                ('cor_olhos', models.CharField(choices=[('Castanho', 'Castanho')], max_length=10)),
                ('documento', models.CharField(max_length=50)),
                ('numero_documento', models.CharField(max_length=20)),
                ('endereco', models.CharField(max_length=200)),
                ('profissao', models.CharField(max_length=50)),
                ('cargo', models.CharField(max_length=50)),
                ('condicao_fisica', models.CharField(max_length=50)),
                ('end_profissional', models.CharField(max_length=200)),
                ('representa', models.BooleanField(default=False)),
            ],
        ),
    ]
