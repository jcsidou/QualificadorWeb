# Generated by Django 5.0.8 on 2024-08-16 00:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extrator', '0004_remove_pessoa_cargo_remove_pessoa_condicao_fisica_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pessoa',
            name='celular',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='pessoa',
            name='email',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='pessoa',
            name='requerMPU',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name='pessoa',
            name='telefone',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
