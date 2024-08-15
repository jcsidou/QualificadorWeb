from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from .models import Pessoa
from .forms import UploadFileForm
from PyPDF2 import PdfReader
import json
import re
import uuid
import random
import logging
import requests

def extract_address_info(text):
    # Ler a chave da API do Google Maps do arquivo configs.json
    with open('/configs.json') as config_file:
        config = json.load(config_file)
        api_key = config.get('Google_Maps_API_KEI')
    
    if not api_key:
        raise ValueError("API Key not found in /configs.json")
    
    # Extrair telefone fixo
    phone = re.search(r'Fone\s*\((\d{2})\)\s*(\d{4,5}-\d{4})', text)
    phone = f"({phone.group(1)}) {phone.group(2)}" if phone else None

    # Extrair celular
    mobile = re.search(r'Celular\s*\((\d{2})\)\s*(\d{5}-\d{4})', text)
    mobile = f"({mobile.group(1)}) {mobile.group(2)}" if mobile else None

    # Extrair e-mail (se houver)
    email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    email = email.group(0) if email else None

    # Remover telefone, celular e e-mail do texto
    clean_text = re.sub(r'Fone\s*\(\d{2}\)\s*\d{4,5}-\d{4}', '', text)
    clean_text = re.sub(r'Celular\s*\(\d{2}\)\s*\d{5}-\d{4}', '', clean_text)
    clean_text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', clean_text).strip()

    # Extrair CEP (se houver)
    cep = re.search(r'\d{5}-?\d{3}', clean_text)
    cep = cep.group(0) if cep else None

    # Extrair cidade e estado
    city_state = re.search(r'([^,]+)\s*-\s*([A-Z]{2})(?:,|\s*$)', clean_text)
    city = city_state.group(1).strip() if city_state else None
    state = city_state.group(2) if city_state else None

    # Remover cidade, estado e CEP do texto
    clean_text = re.sub(r'([^,]+)\s*-\s*[A-Z]{2}(?:,|\s*$)', '', clean_text).strip()
    clean_text = re.sub(r'\d{5}-?\d{3}', '', clean_text).strip()

    # Extrair número, complemento e bairro
    match = re.search(r',\s*(\d+)\s*([^,-]*)(?:-\s*([^,]+))?', clean_text)
    if match:
        number = match.group(1)
        complement = match.group(2).strip() if match.group(2) else None
        neighborhood = match.group(3).strip() if match.group(3) else None
        street = re.sub(r',\s*\d+.*$', '', clean_text).strip()
    else:
        number = None
        complement = None
        neighborhood = None
        street = clean_text

    # Formar o endereço completo para a consulta
    address_query = f"{street}, {number}, {city}, {state}, {cep}"
    response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={address_query}&key={api_key}")

    if response.status_code != 200:
        raise ValueError("Error contacting Google Maps API")

    address_data = response.json()
    
    if not address_data['results']:
        raise ValueError("No results found for the address")

    address_components = address_data['results'][0]['address_components']
    
    address_info = {
        'street': street,
        'number': number,
        'complement': complement,
        'neighborhood': neighborhood,
        'city': city,
        'state': state,
        'cep': cep,
        'phone': phone,
        'mobile': mobile,
        'email': email
    }

    # Preencher os campos do endereço com os dados retornados pela API
    for component in address_components:
        if 'route' in component['types']:
            address_info['street'] = component['long_name']
        if 'street_number' in component['types']:
            address_info['number'] = component['long_name']
        if 'sublocality' in component['types']:
            address_info['neighborhood'] = component['long_name']
        if 'administrative_area_level_2' in component['types']:
            address_info['city'] = component['long_name']
        if 'administrative_area_level_1' in component['types']:
            address_info['state'] = component['short_name']
        if 'postal_code' in component['types']:
            address_info['cep'] = component['long_name']
    
    return address_info

logger = logging.getLogger(__name__)

# Carregar a chave API do arquivo settings.json
with open('./configs.json') as f:
    settings = json.load(f)
    openai_api_key = settings.get('OpenAI_API_KEY')

# Substituições para as condições
CONDICOES_SUBSTITUICOES = {
    'Vítima': 'Vítima',
    'Vitima': 'Vítima',
    'Ofendida': 'Vítima',
    'Ofendido': 'Vítima',
    'Testemunha': 'Testemunha',
    'Comunicante': 'Testemunha',
    'Condutor': 'Testemunha',
    'Só Comunicante': 'Testemunha',
    'Flagrado': 'Agente',
    'Suspeito': 'Agente',
    'Indiciado': 'Agente',
    'Autor': 'Agente',
    'Adolescente': 'Agente',
    'Adolescente Infrator': 'Agente',
    'Acusado': 'Agente',
    'Denunciado': 'Agente',
    'Motorista': 'Agente',
    'Indiciado': 'Agente'
}

def atualizar_condicao(condicao):
    logger.debug(f"Atualizando condição: {condicao}")
    condicao_ajustada = CONDICOES_SUBSTITUICOES.get(condicao.strip(), condicao.strip())
    print(condicao_ajustada)
    return condicao_ajustada

def extrair_texto_pdf(arquivo_pdf):
    leitor = PdfReader(arquivo_pdf)
    texto = ""
    for pagina in leitor.pages:
        texto += pagina.extract_text()
    return texto

def formatar_nome(nome):
    particulas = ['de', 'da', 'das', 'dos', 'e']
    palavras = nome.split()
    palavras_formatadas = [palavra.capitalize() if palavra.lower() not in particulas else palavra.lower() for palavra in palavras]
    return ' '.join(palavras_formatadas)

def obter_qualificacao(pessoa):
    logger.debug(f"Dados recebidos na função obter_qualificacao: {pessoa}")

    condicao = str(pessoa.get('condicao', 'não informada')).strip().lower()
    nome = str(pessoa.get('nome', 'Nome não informado')).strip()
    cpf = str(pessoa.get('cpf')).strip() or 'não informado'
    endereco = str(pessoa.get('endereco')).strip() or 'endereço não informado'

    if condicao == 'vítima':
        return f"{nome}, CPF {cpf}, vítima, com endereço na {endereco}"

    if condicao == 'testemunha':
        return f"{nome}, CPF {cpf}, com endereço na {endereco}"

    aleatorio_masculino1 = "não informado"
    aleatorio_masculino2 = "não apurado"
    aleatorio_masculino3 = "não esclarecido"
    aleatorio_masculino = [aleatorio_masculino1, aleatorio_masculino2, aleatorio_masculino3]
    
    aleatorio_feminino1 = "não informada"
    aleatorio_feminino2 = "não apurada"
    aleatorio_feminino3 = "não esclarecida"
    aleatorio_feminino = [aleatorio_feminino1, aleatorio_feminino2, aleatorio_feminino3]
    
    
    nacionalidade = str(pessoa.get('nacionalidade')).strip().lower() or f'nacionalidade {random.choice(aleatorio_feminino)}'.strip()
    estado_civil = str(pessoa.get('estado_civil')).strip().lower() or random.choice(aleatorio_masculino)
    profissao = str(pessoa.get('profissao')).strip().lower() or f'''profissão {random.choice(aleatorio_feminino)}'''.strip()
    grau_instrucao = str(pessoa.get('grau_instrucao')).strip().lower() or random.choice(aleatorio_masculino)
    numero_documento = str(pessoa.get('numero_documento')).strip().lower() or random.choice(aleatorio_masculino)
    nome_pai = formatar_nome(str(pessoa.get('nome_pai')).strip())
    nome_mae = formatar_nome(str(pessoa.get('nome_mae')).strip())
    naturalidade = formatar_nome(str(pessoa.get('naturalidade'+'/'+'naturalidade_uf', 'localidade'.lower())).strip()) or 'não esclarecida' or not naturalidade
    if naturalidade.lower() == 'localidade':
        naturalidade = f'localidade {random.choice(aleatorio_feminino)}'
    cor_pele = str(pessoa.get('cor_pele')).strip().lower() or random.choice(aleatorio_feminino)
    documento = str(pessoa.get('documento')).strip().lower() or  random.choice(aleatorio_masculino)
    sexo = str(pessoa.get('sexo', '')).strip().lower()

    if sexo == 'feminino':
        qualificacao = (f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
                        f"{grau_instrucao}, portadora do R.G. nº {numero_documento}, inscrita no C.P.F. sob nº {cpf}, "
                        f"filha de {nome_pai} e de {nome_mae}, natural de {naturalidade}, de pele {cor_pele}, "
                        f"com endereço na {endereco}.")
    else:
        qualificacao = (f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
                        f"{grau_instrucao}, portador do R.G. nº {numero_documento}, inscrito no C.P.F. sob nº {cpf}, "
                        f"filho de {nome_pai} e de {nome_mae}, natural de {naturalidade}, de pele {cor_pele}, "
                        f"com endereço na {endereco}.")
    
    logger.debug(f"Qualificação gerada: {qualificacao}")
    return qualificacao

@csrf_exempt
def upload_file_view(request):
    if request.method == 'POST':
        # Limpar JSON da sessão
        request.session['participantes'] = json.dumps([])

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['file']
            texto = extrair_texto_pdf(arquivo)

            regex = r"Participante:\s+(?P<no_participante>\d+)\s+-\s+(?P<condicao>\w*\s?\w*)\s*(?P<presente>\w+)?\nEndere.o:\s+(?P<endereco>.*\n?.*\n)Endere.o\s\w+:(?P<end_profissional>.*)([\w*\s]*\?\s?(?P<requer_protetiva>Sim|Não))?Estado\sCivil:\s+(?P<estado_civil>.*).*\sGrau\sde\s.nstru..o:\s(?P<grau_instrucao>[\s\S\n]{,30})?Cor.\w+:\s(?P<cor_pele>.*)\nNaturalidade:\s((?P<naturalidade>.*)[\n|\s](?P<naturalidade_uf>[A-Z]{2}))?\s?Nacionalidade:\s(?P<nacionalidade>.*)\sCor .lhos:\s(?P<cor_olhos>[A-Z][a-z|\s]*)(?P<nome>[[A-Z|\s]*)\sNome:\s(?P<nome_pai>[\w|\s|-]*)\s\/\s(?P<nome_mae>[\w|\s|-]*)\sPai.*\n\w*\s\w+:\s(?P<data_nascimento>\d{2}/\d{2}/\d{4})\sSexo:\s(?P<sexo>\w*\s?\w*)\sCPF:\s?(?P<cpf>(\d{3}\.\d{3}\.\d{3}.\d{2})?)\nDocumento:\s(?P<documento>.*)\sNúmero:\s?(?P<numero_documento>\d*)\nProfi\w+:\s(?P<profissao>.*)?Cargo:\s(?P<cargo>.*)?Cond\w*\s\w*:\s(?P<condicao_fisica>.*)?"
            
            matches = re.finditer(regex, texto, re.MULTILINE)
            participantes = []
            for matchNum, match in enumerate(matches, start=1):
                participante = match.groupdict()
                print(participante['condicao'])
                participante['condicao'] = atualizar_condicao(participante['condicao'])
                print(participante['condicao'])
                participante['id'] = matchNum
                participante['qualificacao'] = obter_qualificacao(participante)
                participantes.append(participante)

            request.session['pessoas'] = participantes
            return redirect('upload_success')
    else:
        form = UploadFileForm()
    return render(request, 'extrator/upload.html', {'form': form})

@csrf_exempt
def alterar_pessoa(request, pessoa_id):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Log dos dados recebidos
        logger.debug(f"Dados recebidos para atualização da pessoa {pessoa_id}: {data}")

        # Atualizar JSON na sessão
        pessoas_str = request.session.get('pessoas', '[]')
        pessoas = json.loads(pessoas_str) if isinstance(pessoas_str, str) else pessoas_str

        pessoa_atualizada = None
        for pessoa in pessoas:
            logger.debug(f"Verificando pessoa com ID: {pessoa['id']} contra {pessoa_id}")
            if str(pessoa['id']) == str(pessoa_id):
                pessoa.update(data)
                pessoa['condicao'] = atualizar_condicao(pessoa['condicao'])
                pessoa['qualificacao'] = obter_qualificacao(pessoa)
                pessoa_atualizada = pessoa
                break

        if pessoa_atualizada:
            request.session['pessoas'] = json.dumps(pessoas)
            logger.debug(f"Pessoa atualizada: {pessoa_atualizada}")
            return JsonResponse(pessoa_atualizada, status=200)
        else:
            logger.error(f"Pessoa com ID {pessoa_id} não encontrada.")
            return JsonResponse({'error': 'Pessoa não encontrada'}, status=404)
    return HttpResponseNotAllowed(['POST'])

@csrf_exempt
def add_person(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Gerar um ID único para a nova pessoa
        pessoa_id = str(uuid.uuid4())

        pessoa = {**data, 'id': pessoa_id}
        pessoa['condicao'] = atualizar_condicao(pessoa['condicao'])
        pessoa['qualificacao'] = obter_qualificacao(pessoa)

        # Atualizar JSON na sessão
        pessoas = request.session.get('pessoas', [])
        pessoas.append(pessoa)
        request.session['pessoas'] = pessoas

        return JsonResponse(pessoa, status=201)
    return HttpResponseNotAllowed(['POST'])

@csrf_exempt
def remove_person(request, id):
    if request.method == 'DELETE':
        # Atualizar JSON na sessão
        pessoas = request.session.get('pessoas', [])
        pessoas = [p for p in pessoas if p['id'] != id]
        request.session['pessoas'] = pessoas

        return JsonResponse({'status': 'success'})
    return HttpResponseNotAllowed(['DELETE'])

def upload_success_view(request):
    pessoas = request.session.get('pessoas', [])
    return render(request, 'extrator/success.html', {'pessoas': pessoas})

@csrf_exempt
def atualizar_qualificacao(request, pessoa_id):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Atualizar JSON na sessão
        pessoas = request.session.get('pessoas', [])
        for pessoa in pessoas:
            if pessoa['id'] == pessoa_id:
                pessoa.update(data)
                pessoa['qualificacao'] = obter_qualificacao(pessoa)
                break
        request.session['pessoas'] = pessoas

        return JsonResponse({'qualificacao': pessoa['qualificacao']})
    return HttpResponseNotAllowed(['POST'])

def extract_address_info(text):
    # Ler a chave da API do Google Maps do arquivo configs.json
    with open('/configs.json') as config_file:
        config = json.load(config_file)
        api_key = config.get('Google_Maps_API_KEI')
    
    if not api_key:
        raise ValueError("API Key not found in /configs.json")
    
    # Extrair telefone fixo
    phone = re.search(r'Fone\s*\((\d{2})\)\s*(\d{4,5}-\d{4})', text)
    phone = f"({phone.group(1)}) {phone.group(2)}" if phone else None

    # Extrair celular
    mobile = re.search(r'Celular\s*\((\d{2})\)\s*(\d{5}-\d{4})', text)
    mobile = f"({mobile.group(1)}) {mobile.group(2)}" if mobile else None

    # Extrair e-mail (se houver)
    email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    email = email.group(0) if email else None

    # Remover telefone, celular e e-mail do texto
    clean_text = re.sub(r'Fone\s*\(\d{2}\)\s*\d{4,5}-\d{4}', '', text)
    clean_text = re.sub(r'Celular\s*\(\d{2}\)\s*\d{5}-\d{4}', '', clean_text)
    clean_text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', clean_text).strip()

    # Extrair CEP (se houver)
    cep = re.search(r'\d{5}-?\d{3}', clean_text)
    cep = cep.group(0) if cep else None

    # Extrair cidade e estado
    city_state = re.search(r'([^,]+)\s*-\s*([A-Z]{2})(?:,|\s*$)', clean_text)
    city = city_state.group(1).strip() if city_state else None
    state = city_state.group(2) if city_state else None

    # Remover cidade, estado e CEP do texto
    clean_text = re.sub(r'([^,]+)\s*-\s*[A-Z]{2}(?:,|\s*$)', '', clean_text).strip()
    clean_text = re.sub(r'\d{5}-?\d{3}', '', clean_text).strip()

    # Extrair número, complemento e bairro
    match = re.search(r',\s*(\d+)\s*([^,-]*)(?:-\s*([^,]+))?', clean_text)
    if match:
        number = match.group(1)
        complement = match.group(2).strip() if match.group(2) else None
        neighborhood = match.group(3).strip() if match.group(3) else None
        street = re.sub(r',\s*\d+.*$', '', clean_text).strip()
    else:
        number = None
        complement = None
        neighborhood = None
        street = clean_text

    # Formar o endereço completo para a consulta
    address_query = f"{street}, {number}, {city}, {state}, {cep}"
    response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={address_query}&key={api_key}")

    if response.status_code != 200:
        raise ValueError("Error contacting Google Maps API")

    address_data = response.json()
    
    if not address_data['results']:
        raise ValueError("No results found for the address")

    address_components = address_data['results'][0]['address_components']
    
    address_info = {
        'street': street,
        'number': number,
        'complement': complement,
        'neighborhood': neighborhood,
        'city': city,
        'state': state,
        'cep': cep,
        'phone': phone,
        'mobile': mobile,
        'email': email
    }

    # Preencher os campos do endereço com os dados retornados pela API
    for component in address_components:
        if 'route' in component['types']:
            address_info['street'] = component['long_name']
        if 'street_number' in component['types']:
            address_info['number'] = component['long_name']
        if 'sublocality' in component['types']:
            address_info['neighborhood'] = component['long_name']
        if 'administrative_area_level_2' in component['types']:
            address_info['city'] = component['long_name']
        if 'administrative_area_level_1' in component['types']:
            address_info['state'] = component['short_name']
        if 'postal_code' in component['types']:
            address_info['cep'] = component['long_name']
    
    return address_info