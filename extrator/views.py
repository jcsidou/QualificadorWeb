from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from .models import Pessoa
from .forms import UploadFileForm
from PyPDF2 import PdfReader
import pytesseract
import cv2
import re
import io
import json
import numpy as np
from datetime import datetime

def extrair_texto_pdf(arquivo):
    # Função para extrair texto de um PDF
    leitor_pdf = PdfReader(arquivo)
    texto = ""
    for pagina in leitor_pdf.pages:
        texto += pagina.extract_text()
    with open('original.txt', 'w') as arquivo:
        arquivo.write(texto)
    texto = excluir_cabecalho(texto)
    with open('cabecalho.txt', 'w') as arquivo:
        arquivo.write(texto)
    texto = excluir_rodape(texto)
    with open('rodape.txt', 'w') as arquivo:
        arquivo.write(texto)
    return texto

def excluir_cabecalho(texto):
    padrao = r"(?P<Cabecalho>^.*?)\nDados\s"
    match = re.search(padrao, texto, flags=re.MULTILINE | re.DOTALL)
    cabecalho = match.group('Cabecalho')
    with open('str_cabecalho.txt', 'w') as arquivo:
        arquivo.write(cabecalho)
    texto_limpo = texto.replace(cabecalho, '')
    return texto_limpo

def excluir_rodape(texto):
    padrao = r"ROCP.*\n"
    match = str(re.findall(padrao, texto))
    with open('str_rodape.txt', 'w') as arquivo:
        arquivo.write(match)
    texto_limpo = re.sub(r'ROCP.*\n', '', texto)
    return texto_limpo

def realizar_ocr(arquivo):
    # Função para realizar OCR em uma imagem
    arquivo.seek(0)
    imagem = cv2.imdecode(np.frombuffer(arquivo.read(), np.uint8), cv2.IMREAD_COLOR)
    texto = pytesseract.image_to_string(imagem)
    return texto

def limpar_e_extrair(texto, regex_parametros):
    # Função para limpar e extrair informações usando regex
    dados_extracao = {}
    for chave, padrao in regex_parametros.items():
        match = re.search(padrao, texto)
        if match:
            dados_extracao[chave] = match.group(1)
    return dados_extracao

def upload_file_view(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['file']
            if arquivo.name.endswith('.pdf'):
                texto = extrair_texto_pdf(arquivo)
                regex = r"Participante:\s+(?P<Np_Participante>\d+)\s+-\s+(?P<Condicao>\w*\s?\w*)\s*(?P<Presente>\w+)?\nEndere.o:\s+(?P<Endereco>.*\n?.*\n)Endere.o\s\w+:(?P<Endereco_Profissional>.*)([\w*\s]*\?\s?(?P<Requer_Protetiva>Sim|Não))?Estado\sCivil:\s+(?P<Estado_Civil>.*).*\sGrau\sde\s.nstru..o:\s(?P<Grau_de_Instrucao>[\s\S\n]{,30})?Cor.\w+:\s(?P<Cor_Pele>.*)\nNaturalidade:\s((?P<Natural_Cidade>.*)[\n|\s](?P<Natural_UF>[A-Z]{2}))?\s?Nacionalidade:\s(?P<Nacionalidade>.*)\sCor .lhos:\s(?P<Cor_olhos>[A-Z][a-z|\s]*)(?P<Nome>[[A-Z|\s]*)\sNome:\s(?P<Pai>[\w|\s|-]*)\s\/\s(?P<Mae>[\w|\s|-]*)\sPai.*\n\w*\s\w+:\s(?P<Data_Nascimento>\d{2}/\d{2}/\d{4})\sSexo:\s(?P<Sexo>\w*\s?\w*)\sCPF:\s?(?P<CPF>(\d{3}\.\d{3}\.\d{3}.\d{2})?)\nDocumento:\s(?P<Documento>.*)\sNúmero:\s?(?P<No_Documento>\d*)\nProfi\w+:\s(?P<Profissao>.*)?Cargo:\s(?P<Cargo>.*)?Cond\w*\s\w*:\s(?P<Condicao_Fisica>.*)?"
            else:
                texto = realizar_ocr(arquivo)

            matches = re.finditer(regex, texto, re.MULTILINE)
            participantes = []
            pessoas_criadas = []
            for matchNum, match in enumerate(matches, start=1):
                participante = match.groupdict()
                participantes.append(participante)
                
                data_nascimento_str = participante.get('Data_Nascimento')
                data_nascimento = None
                if data_nascimento_str:
                    try:
                        # Converte a data para o formato YYYY-MM-DD
                        data_nascimento = datetime.strptime(data_nascimento_str, "%d/%m/%Y").date()
                    except ValueError:
                        # Trata o erro se o formato da data estiver incorreto
                        raise ValidationError(f"Data de nascimento {data_nascimento_str} está em um formato inválido.")

                # Criar objeto Pessoa com os dados extraídos
                pessoa = Pessoa(
                    nome=participante.get('Nome', ''),
                    condicao=participante.get('Condicao', ''),
                    alcunha='',
                    nome_pai=participante.get('Pai', ''),
                    nome_mae=participante.get('Mae', ''),
                    data_nascimento=data_nascimento,
                    sexo=participante.get('Sexo', ''),
                    cpf=participante.get('CPF', ''),
                    estado_civil=participante.get('Estado_Civil', ''),
                    grau_instrucao=participante.get('Grau_de_Instrucao', ''),
                    cor_pele=participante.get('Cor_Pele', ''),
                    naturalidade=participante.get('Natural_Cidade', ''),
                    naturalidade_UF = participante.get('Natural_UF', ''),
                    nacionalidade=participante.get('Nacionalidade', ''),
                    documento=participante.get('Documento', ''),
                    numero_documento=participante.get('No_Documento', ''),
                    endereco=participante.get('Endereco', ''),
                    profissao=participante.get('Profissao', ''),
                    end_profissional=participante.get('Endereco_Profissional', ''),
                    representa=False,
                    )
                pessoa.save()
                pessoas_criadas.append(pessoa)
                
            # Converter lista de dicionários para JSON
            participantes_json = json.dumps(participantes, indent=4, ensure_ascii=False)
            print(participantes_json)
            with open("participantes.json", "w", encoding='utf-8') as f:
                f.write(participantes_json)

            return render(request, 'extrator/success.html', {'pessoas': pessoas_criadas})
    else:
        form = UploadFileForm()
    return render(request, 'extrator/upload.html', {'form': form})

def alterar_condicao(request, pessoa_id):
    if request.method == "POST":
        pessoa = get_object_or_404(Pessoa, id=pessoa_id)
        nova_condicao = request.POST.get('condicao')
        pessoa.condicao = nova_condicao
        pessoa.save()
        return redirect('success')  # Ajuste o nome da URL para a página de sucesso conforme necessário
    return redirect('success')

def alterar_pessoa(request, pessoa_id):
    if request.method == "POST":
        pessoa = get_object_or_404(Pessoa, id=pessoa_id)
        pessoa.nome = request.POST.get('nome')
        pessoa.condicao = request.POST.get('condicao')
        pessoa.alcunha = request.POST.get('alcunha')
        pessoa.nome_pai = request.POST.get('nome_pai')
        pessoa.nome_mae = request.POST.get('nome_mae')
        pessoa.data_nascimento = request.POST.get('data_nascimento')
        pessoa.sexo = request.POST.get('sexo')
        pessoa.cpf = request.POST.get('cpf')
        pessoa.estado_civil = request.POST.get('estado_civil')
        pessoa.grau_instrucao = request.POST.get('grau_instrucao')
        pessoa.cor_pele = request.POST.get('cor_pele')
        pessoa.naturalidade = request.POST.get('naturalidade')
        pessoa.naturalidade_UF = request.POST.get('naturalidade_UF')
        pessoa.nacionalidade = request.POST.get('nacionalidade')
        pessoa.cor_olhos = request.POST.get('cor_olhos')
        pessoa.documento = request.POST.get('documento')
        pessoa.numero_documento = request.POST.get('numero_documento')
        pessoa.endereco = request.POST.get('endereco')
        pessoa.profissao = request.POST.get('profissao')
        pessoa.cargo = request.POST.get('cargo')
        pessoa.condicao_fisica = request.POST.get('condicao_fisica')
        pessoa.end_profissional = request.POST.get('end_profissional')
        pessoa.representa = bool(request.POST.get('representa'))
        pessoa.save()
        return redirect('success')  # Ajuste o nome da URL para a página de sucesso conforme necessário
    return redirect('success')

@csrf_exempt
def add_person(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        pessoa = Pessoa.objects.create(
            condicao=data['condicao'],
            alcunha=data['alcunha'],
            nome=data['nome'],
            nome_pai=data['nome_pai'],
            nome_mae=data['nome_mae'],
            data_nascimento=data['data_nascimento'],
            sexo=data['sexo'],
            cpf=data['cpf'],
            cor_pele=data['cor_pele'],
            estado_civil=data['estado_civil'],
            grau_instrucao=data['grau_instrucao'],
            naturalidade=data['naturalidade'],
            naturalidade_UF=data['naturalidade_UF'],
            nacionalidade=data['nacionalidade'],
            documento=data['documento'],
            numero_documento=data['numero_documento'],
            endereco=data['endereco'],
            end_profissional=data['end_profissional'],
            profissao=data['profissao'],
            representa=data.get('representa', False)
        )
        pessoa.save()
        return JsonResponse({
            'id': pessoa.id,
            'condicao': pessoa.condicao,
            'alcunha': pessoa.alcunha,
            'nome': pessoa.nome,
            'nome_pai': pessoa.nome_pai,
            'nome_mae': pessoa.nome_mae,
            'data_nascimento': pessoa.data_nascimento,
            'sexo': pessoa.sexo,
            'cpf': pessoa.cpf,
            'cor_pele': pessoa.cor_pele,
            'estado_civil': pessoa.estado_civil,
            'grau_instrucao': pessoa.grau_instrucao,
            'naturalidade': pessoa.naturalidade,
            'naturalidade_UF': pessoa.naturalidade_UF,
            'nacionalidade': pessoa.nacionalidade,
            'documento': pessoa.documento,
            'numero_documento': pessoa.numero_documento,
            'endereco': pessoa.endereco,
            'end_profissional': pessoa.end_profissional,
            'profissao': pessoa.profissao,
            'representa': pessoa.representa,
        }, status=201)
        
def qualificar_todos(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        prompt = data['prompt']
        pessoas = data['pessoas']
        
        # Sua lógica para qualificar as pessoas
        # Aqui, apenas retornamos as pessoas como exemplo
        return JsonResponse(pessoas, status=200)

def remove_person(request, id):
    if request.method == 'DELETE':
        try:
            pessoa = Pessoa.objects.get(id=id)
            pessoa.delete()
            return JsonResponse({'status': 'success'})
        except Pessoa.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Pessoa não encontrada'}, status=404)
    return HttpResponseNotAllowed(['DELETE'])