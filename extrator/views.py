from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse  
from django.core import serializers
from .models import Pessoa, DadosGerais
from .forms import UploadFileForm
from PyPDF2 import PdfReader
import json
import re
import os
import uuid
import random
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime
from dynaconf import Dynaconf

logger = logging.getLogger(__name__)

#Carregar a chave API do arquivo settings.json
with open('./configs.json') as f:
    settings = json.load(f)

    openai_api_key = settings.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("API Key not found in /configs.json")

    google_maps_api_key = settings.get('GOOGLE_MAPS_API_KEI')
    if not google_maps_api_key:
        raise ValueError("API Key not found in /configs.json")

    ###Estou com problemas em importar essa regex do JSON.. Por ora, deixei fixo no codigo abaixo
    regex_pessoas = settings.get('REGEX_PESSOAS')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
    
    regex_cabecalho = settings.get('REGEX_CABECALHO')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
    
    regex_rodape = settings.get('REGEX_RODAPE')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
    
    solr_user = settings.get('SOLR_USER')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
    
    solr_pass = settings.get('SOLR_PASS')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
    
    solr_url = settings.get('SOLR_URL')
    if not regex_pessoas:
        raise ValueError("Regex not found in /configs.json")
###
regex_dados_gerais='Dados Gerais\\n.rg.o:\\s+(?P<no_orgao_op>\\d{6})\\s+-?\\s+(?P<orgao_op>[\\S\\s]*)\\s+Ano:\\s+(?P<ano_op>\\d{4})\\s+\\w+:\\s+(?P<no_op>\\d*)\\n.*\\n.ata\\s\\w+:\\s+(?P<data_registro>\\d{2}\\/\\d{2}\\/\\d{4})\\s\\w+\\s(?P<hora_registro>\\d{2}:\\d{2}).*\\n\\w+.\\s+(?P<fato>.*)\\n.\\w+:\\s+(?P<data_fato>\\d{2}\\/\\d{2}\\/\\d{4})[\\s\\w]+(?P<hora_fato>\\d{2}:\\d{2})[\\s\\w]+:\\s(?P<tipo_area>.*)(?P<consumacao>.onsumado|.entado)[\\S\\s\\w]+:.nder.*:\\s+(?P<endereco_fato>.*)\\n\\w+\\n(?P<historico>[\\w\\s\\S]*).rgão de |Participante'
regex_pessoas='Participante:\\s+(?P<no_participante>\\d+)\\s+-\\s+(?P<condicao>\\w*\\s?\\w*)\\s*(?P<presente>\\w+)?\\nEndere.o:\\s+(?P<endereco>.*\\n?.*)\\nEndere.o\\s\\w+:(?P<end_profissional>.*\\n?.*)(\\n?[\\w|\\s]*representar em juízo.\\s*(?P<representa>Sim|Não)\\n?)?([\\w*\\s]*\\?\\s?(?P<requer_mpu>Sim|Não))?Estado\\sCivil:\\s+(?P<estado_civil>.*).*\\sGrau\\sde\\s.nstru..o:\\s(?P<grau_instrucao>[\\s\\S]{,30})Cor.\\w+:\\s?(?P<cor_pele>.*)\\nNaturalidade:\\s((?P<naturalidade>.*)[\\n|\\s](?P<naturalidade_uf>[A-Z]{2}))?\\s?Nacionalidade:\\s(?P<nacionalidade>.*)\\sCor .lhos:\\s(?P<cor_olhos>[A-Z][a-z|\\s]*)(?P<nome>[\\w\\s]*)\\sNome:\\s(?P<nome_pai>[\\w|\\s|-]*)\\s\\/\\s(?P<nome_mae>[\\w|\\s|-]*)\\sPai.*\\n\\w*\\s\\w+:\\s(?P<data_nascimento>\\d{2}\\/\\d{2}\\/\\d{4})\\sSexo:\\s(?P<sexo>\\w*\\s?\\w*)\\sCPF:\\s?(?P<cpf>(\\d{3}\\.\\d{3}\\.\\d{3}.\\d{2})?)\\nDocumento:\\s(?P<documento>.*)\\sNúmero:\\s?(?P<numero_documento>\\d*)\\nProfi\\w+:\\s(?P<profissao>.*)?Cargo:\\s(?P<cargo>.*)?Cond\\w*\\s\\w*:\\s(?P<condicao_fisica>.*)?'
regex_cabecalho="(?P<Cabecalho>^.*?)\\nDados\\s"
regex_rodape="ROCP.*\\n"

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
    return condicao_ajustada

def extrair_texto_pdf(arquivo):
    # Função para extrair texto de um PDF
    leitor_pdf = PdfReader(arquivo)
    texto = ""
    for pagina in leitor_pdf.pages:
        texto += pagina.extract_text()
    texto = excluir_cabecalho(texto)
    texto = excluir_rodape(texto)
    return texto

def excluir_cabecalho(texto):
    match = re.search(regex_cabecalho, texto, flags=re.MULTILINE | re.DOTALL)
    cabecalho = match.group('Cabecalho')
    texto_limpo = texto.replace(cabecalho, '')
    return texto_limpo

def excluir_rodape(texto):
    texto_limpo = re.sub(regex_rodape, '', texto)
    return texto_limpo

def clean_string(input_string: str) -> str:
    if not input_string:
        return ''
    cleaned_string = input_string.replace('\n', ' ').replace('\r', ' ')
    while '  ' in cleaned_string:
        cleaned_string = cleaned_string.replace('  ', ' ')
    cleaned_string = cleaned_string.strip()
    return cleaned_string

def formatar_nome(nome):
    particulas = ['de', 'da', 'das', 'dos', 'e']
    palavras = nome.split()
    palavras_formatadas = [palavra.capitalize() if palavra.lower() not in particulas else palavra.lower() for palavra in palavras]
    return ' '.join(palavras_formatadas)

def convert_to_django_date(date_str):
    """
    Converts a date string in dd/mm/yyyy format to a valid Django DateField compatible date object.
    
    Args:
        date_str (str): A date string in the format dd/mm/yyyy.
    
    Returns:
        date (date): A date object that can be used in a Django DateField.
    """
    try:
        # Convert string to datetime object
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        # Return the date part only, compatible with Django DateField
        return date_obj.date()
    except ValueError as e:
        logger.debug(f"Não foi possível converter data {date_str}")
        raise ValueError(f"Incorrect date format: {date_str}. Expected format: dd/mm/yyyy") from e

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
    grau_instrucao = str(pessoa.get('grau_instrucao')).strip().lower() or f'''grau de instrução {random.choice(aleatorio_masculino)}'''
    numero_documento = str(pessoa.get('numero_documento')).strip().lower() or random.choice(aleatorio_masculino)
    nome_pai = formatar_nome(str(pessoa.get('nome_pai')).strip())
    nome_mae = formatar_nome(str(pessoa.get('nome_mae')).strip())
    
    naturalidade = formatar_nome(str(pessoa.get('naturalidade'))) or None
    if not naturalidade:
        naturalidade = f'localidade {random.choice(aleatorio_feminino)}'
    else:
        naturalidade_uf = pessoa.get('naturalidade_uf') or None
        if naturalidade_uf:
            naturalidade =f'''{naturalidade}/{naturalidade_uf.upper().strip()}'''
    
    cor_pele = str(pessoa.get('cor_pele')).strip().lower() or random.choice(aleatorio_feminino)
    documento = str(pessoa.get('documento')).strip().lower() or random.choice(aleatorio_masculino)
    sexo = str(pessoa.get('sexo', '')).strip().lower()
    

    if sexo == 'feminino':
        qualificacao = (f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
                        f"{grau_instrucao}, portadora do RG nº {numero_documento}, inscrita no CPF sob nº {cpf}, "
                        f"filha de {nome_pai} e de {nome_mae}, natural de {naturalidade}, de pele {cor_pele}, "
                        f"com endereço na {endereco}.")
    else:
        qualificacao = (f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
                        f"{grau_instrucao}, portador do RG nº {numero_documento}, inscrito no CPF sob nº {cpf}, "
                        f"filho de {nome_pai} e de {nome_mae}, natural de {naturalidade}, de pele {cor_pele}, "
                        f"com endereço na {endereco}.")
    
    logger.debug(f"Qualificação gerada: {qualificacao}")
    return qualificacao

@csrf_exempt
def upload_file_view(request):
    if request.method == 'POST':
        # Limpar JSON da sessão
        try:            
            logger.debug(f"Dados gerais antes da limpeza: {request.session['dados_gerais']}")
            logger.debug(f"Dados da sessão antes da limpeza: {request.session['participantes']}")
        except Exception as e:
            logger.debug(f"Não há dados da sessão.\n{e}")
        finally:
            request.session['dados_gerais'] = json.dumps([])
            request.session['participantes'] = json.dumps([])
            logger.debug(f"Dados gerais após a limpeza: {request.session['dados_gerais']}")
            logger.debug(f"Dados das pessoas após a limpeza: {request.session['participantes']}")
        
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['file']
            texto = extrair_texto_pdf(arquivo)
            
            #txt_path =  f"{arquivo}.txt"
            with open(f"{arquivo}.txt", "w", encoding="utf-8") as text_file:
                text_file.write(texto)
                
            match = re.search(regex_dados_gerais, texto, re.MULTILINE)    
            if match:
                # Extrair os dados capturados pelos grupos nomeados e armazenar em um dicionário
                dados_gerais = {
                    'no_orgao_op': match.group('no_orgao_op'),
                    'orgao_op': match.group('orgao_op').strip(),
                    'ano_op': match.group('ano_op'),
                    'no_op': match.group('no_op'),
                    'data_registro': datetime.strptime(match.group('data_registro'), "%d/%m/%Y").strftime('%Y-%m-%d'),
                    'hora_registro': match.group('hora_registro'),
                    'fato': match.group('fato').strip(),
                    'data_fato': datetime.strptime(match.group('data_fato'), "%d/%m/%Y").strftime('%Y-%m-%d'),
                    'hora_fato': match.group('hora_fato'),
                    'tipo_area': match.group('tipo_area').strip(),
                    'consumacao': 'Consumado' if 'onsumado' in match.group('consumacao') else 'Tentado',
                    'endereco_fato': match.group('endereco_fato').strip(),
                    'historico': match.group('historico').replace('\n', ' ').replace('  ', ' ').strip()
                }
                request.session['dados_gerais'] = dados_gerais
            
            matches = re.finditer(regex_pessoas, texto, re.MULTILINE)
            participantes = []
            for matchNum, match in enumerate(matches, start=1):
                participante = match.groupdict()
                participante['id'] = matchNum
                participante['condicao'] = atualizar_condicao(participante['condicao'])
                
                if participante['nome_pai'] and participante['nome_pai'].strip()!="-":
                    participante['nome_pai'] = formatar_nome(participante['nome_pai'])
                else: 
                    participante['nome_pai']=''
                
                if participante['nome_mae'] and participante['nome_mae'].strip()!="-":
                    participante['nome_mae'] = formatar_nome(participante['nome_mae'])
                else:
                    participante['nome_mae']=''
                                
                if participante['grau_instrucao']:
                    participante['grau_instrucao'] = clean_string(participante['grau_instrucao'])
                
                if participante['naturalidade']:
                    participante['naturalidade'] = formatar_nome(clean_string(participante['naturalidade']))
                else:
                    participante['naturalidade'] = ''

                if not participante['naturalidade_uf']:
                    participante['naturalidade_uf'] = clean_string(participante['naturalidade_uf'])
                else:
                    participante['naturalidade_uf'] = ''
                
                if participante['endereco']:
                    participante['endereco'] = clean_string(participante['endereco']).rstrip('.')
                
                participante['qualificacao'] = obter_qualificacao(participante)
                participantes.append(participante)
                
                participante['data_nascimento'] = datetime.strptime(participante['data_nascimento'], '%d/%m/%Y').date().isoformat()

            request.session['pessoas'] = participantes
            
            logger.debug(f"Pessoas gravadas na sessão: {participantes}")
            print(request.session)
            return JsonResponse({'success': True, 'redirect_url': reverse('upload_success')})
        else:
            return JsonResponse({'success': False, 'error': 'Formulário inválido'})
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
            # logger.debug(f"for pessoa in pessoas")
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
def alterar_dados_gerais(request, no_op):
    if request.method == 'POST':
        dados_gerais_str = request.session.get('dados_gerais', '[]')
        dados_gerais = json.loads(dados_gerais_str) if isinstance(dados_gerais_str, str) else dados_gerais_str
        
        
        pass        
    pass

@csrf_exempt
def add_person(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Gerar um ID único para a nova pessoa
        # if not pessoa_id:
        pessoa_id = len(request.session['pessoas'])+1 # str(uuid.uuid4())
        pessoa = {**data, 'id': pessoa_id}
        pessoa['no_participante'] = len(request.session['pessoas'])+1
        pessoa['condicao'] = atualizar_condicao(pessoa['condicao'])
        pessoa['qualificacao'] = obter_qualificacao(pessoa)

        # Certifique-se de que 'pessoas' é uma lista
        pessoas_str = request.session.get('pessoas', '[]')
        pessoas = json.loads(pessoas_str) if isinstance(pessoas_str, str) else pessoas_str

        if not isinstance(pessoas, list):
            pessoas = []  # Caso haja algum erro e 'pessoas' não seja uma lista

        # Adicionar a nova pessoa à lista
        pessoas.append(pessoa)
        request.session['pessoas'] = json.dumps(pessoas)  # Salvar a lista de volta na sessão

        return JsonResponse(pessoa, status=201)
    return HttpResponseNotAllowed(['POST'])

@csrf_exempt
def remove_person(request, id):
    if request.method == 'DELETE':
        # Carregar pessoas como uma lista de dicionários
        pessoas_str = request.session.get('pessoas', '[]')
        pessoas = json.loads(pessoas_str) if isinstance(pessoas_str, str) else pessoas_str

        if not isinstance(pessoas, list):
            pessoas = []  # Caso haja algum erro e 'pessoas' não seja uma lista

        # Filtrar a lista removendo a pessoa com o ID fornecido
        pessoas = [p for p in pessoas if p['id'] != id]

        # Salvar a lista de volta na sessão
        request.session['pessoas'] = json.dumps(pessoas)

        return JsonResponse({'status': 'success'})
    return HttpResponseNotAllowed(['DELETE'])


def upload_success_view(request):
    pessoas = request.session.get('pessoas', [])
    dados_gerais = request.session.get('dados_gerais', [])
    logger.debug(f"Dados Gerais para a view: {dados_gerais}")
    logger.debug(f"Pessoas no contexto: {pessoas}")
    return render(request, 'extrator/success.html', {'pessoas': pessoas, 'dados_gerais': dados_gerais})

@csrf_exempt
def atualizar_qualificacao(request, pessoa_id):
    logger.debug(f"Recebido pedido para atualizar qualificação para pessoa_id: {pessoa_id}")
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.debug(f"Dados recebidos: {data}")

            # Atualizar JSON na sessão
            pessoas_str = request.session.get('pessoas', '[]')
            pessoas = json.loads(pessoas_str) if isinstance(pessoas_str, str) else pessoas_str
            logger.debug(f"Pessoas na sessão: {pessoas}")

            pessoa_atualizada = None
            for pessoa in pessoas:
                logger.debug(f"Verificando pessoa: {pessoa}")
                if str(pessoa['id']) == str(pessoa_id):  # Usando pessoa_id aqui
                    pessoa['qualificacao'] = obter_qualificacao(pessoa)
                    pessoa_atualizada = pessoa
                    break

            if pessoa_atualizada:
                request.session['pessoas'] = json.dumps(pessoas)
                logger.debug(f"Pessoa encontrada e qualificação atualizada: {pessoa_atualizada}")
                return JsonResponse({'qualificacao': pessoa_atualizada['qualificacao']}, status=200)
            else:
                logger.warning(f"Pessoa com id {pessoa_id} não encontrada")
                return JsonResponse({'error': 'Pessoa não encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Erro ao processar a solicitação: {e}")
            return JsonResponse({'error': 'Erro ao processar a solicitação'}, status=500)
    return HttpResponseNotAllowed(['POST'])

def extract_address_info(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            text = body.get('text', '')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dados JSON inválidos'}, status=400)
        
        # Verificando se o texto foi fornecido
        if not text:
            return JsonResponse({'error': 'Texto não fornecido'}, status=400)

        def extract_phone_numbers(text):
            # Remover prefixo internacional +55
            text = re.sub(r'\+55', '', text)
            
            # Padrão para telefone fixo e celular
            pattern = r'(?:(?:Telefone|Fone|Celular|Cel)[:\s]*)?(?:\(?\d{2}\)?[\s.-]?)?(?:\d{4,5}[-.\s]?\d{4})'
            
            numbers = re.findall(pattern, text, re.IGNORECASE)
            
            phones = []
            cellphones = []
            
            for number in numbers:
                # Limpar o número
                clean_number = re.sub(r'\D', '', number)
                
                if len(clean_number) == 10:  # Telefone fixo
                    formatted = f"({clean_number[:2]}) {clean_number[2:6]}-{clean_number[6:]}"
                    phones.append(formatted)
                elif len(clean_number) == 11:  # Celular
                    formatted = f"({clean_number[:2]}) {clean_number[2:7]}-{clean_number[7:]}"
                    cellphones.append(formatted)
            
            return phones, cellphones
        
        phones, cellphones = extract_phone_numbers(text)

        # Extrair e-mail (se houver)
        email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        email = email.group(0) if email else None

        # Remover telefones, celulares e e-mail do texto
        for phone in phones + cellphones:
            text = text.replace(phone, '')
        if email:
            text = text.replace(email, '')

        # Extrair CEP (se houver)
        cep = re.search(r'\d{5}-?\d{3}', text)
        cep = cep.group(0) if cep else None
        
        # Extrair cidade e estado
        city_state = re.search(r'([^,]+)\s*-\s*([A-Z]{2})(?:,|\s*$)', text)
        city = city_state.group(1).strip() if city_state else None
        state = city_state.group(2) if city_state else None

        # Remover cidade, estado e CEP do texto
        if city and state:
            # Correção: Use uma string bruta (r'...') para a expressão regular
            text = re.sub(rf'{re.escape(city)}\s*-\s*{re.escape(state)}', '', text).strip()
        if cep:
            text = text.replace(cep, '').strip()

        # Extrair número, complemento e bairro
        match = re.search(r',\s*(\d+)\s*([^,-]*)(?:-\s*([^,]+))?', text)
        if match:
            number = match.group(1)
            complement = match.group(2).strip() if match.group(2) else None
            neighborhood = match.group(3).strip() if match.group(3) else None
            street = re.sub(r',\s*\d+.*$', '', text).strip()
        else:
            number = None
            complement = None
            neighborhood = None
            street = text

        # Formar o endereço completo para a consulta
        address_query = f"{street}, {number}, {city}, {state}, {cep}"
        response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json?address={address_query}&key={google_maps_api_key}")

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
            'phones': phones,
            'cellphones': cellphones,
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
            if 'postal_code' in component['types'] and 'postal_code' in component['types'] !=None and 'postal_code' in component['types'] !="None":
                address_info['cep'] = component['long_name']
            else: 
                address_info['cep'] = "não localizado"
        
        # Formatar o endereço completo de forma amigável
        friendly_address = f"{address_info['street']}"
        if address_info['number']:
            friendly_address += f" nº {address_info['number']}"
        if address_info['complement']:
            friendly_address += f" {address_info['complement']}"
        friendly_address += f", bairro {address_info['neighborhood']}, {address_info['city']}/{address_info['state']}, CEP {address_info['cep']}"
        
        contact_info = []
        if address_info['phones']:
            phone_text = "telefone" if len(address_info['phones']) == 1 else "telefones"
            contact_info.append(f"{phone_text} {', '.join(address_info['phones'])}")
        if address_info['cellphones']:
            cell_text = "celular" if len(address_info['cellphones']) == 1 else "celulares"
            contact_info.append(f"{cell_text} {', '.join(address_info['cellphones'])}")
        if address_info['email']:
            contact_info.append(f"e-mail {address_info['email']}")
        
        if contact_info:
            contact_info_text = ", " + ", ".join(contact_info)
            friendly_address += contact_info_text
        return JsonResponse({'endereco': friendly_address})
    else:
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
@csrf_exempt
def buscar_dados_cpf(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        cpf = data.get('cpf')

        if not cpf:
            return JsonResponse({'success': False, 'error': 'CPF não fornecido'})

        # Código da função pesquisa_pessoa_cpf adaptado
        def pesquisa_pessoa_cpf(q='', rows=10, start=0):
            
            settings = Dynaconf(
                settings_files=['/opt/mprs/datalake-hadoop/config/RFB_LOAD_BCADASTRO.toml'],
            )

            q = q.replace('/', ' ')
            url = f'{solr_url}/dev-bcadastro-cpf/select/'
            query = f'(cpfId_s:"{q}"^10)'

            params = {
                'q': query,
                'rows': rows,
                'start': start,
                'q.op': 'AND',
                'fl': [
                    'id',
                    'nomeContribuinte_s',
                    'nomeMae_s',
                    "telefone_s",
                    "cpfId_s",
                    "cep_s",
                    "nomeMunDomic_s",
                    "logradouro_s",
                    "bairro_s",
                    "complemento_s",
                    "nroLogradouro_s",
                    "tipoLogradouro_s",
                    "ufMunDomic_s",
                    "nomePaisRes_s",
                    "anoObito_s",
                    "dtUltAtualiz_dt",
                    "dtInscricao_dt",
                    "codSexo_i",
                    "dtNasc_dt",
                    "nomeMunNat_s",
                    "ufMunNat_s",
                    "nomePaisNac"
                ],
            }

            res = requests.get(
                url,
                params=params,
                verify=False,
                auth=(solr_user, solr_pass),
            )

            try:
                res = res.json()
                res = res['response']
            except ValueError as e:
                print("Erro ao converter resposta para JSON:", e)
                return None

            return {
                'status': 'ok',
                'hits': res['numFound'],
                'docs': res['docs'],
                'params': params
            }

        response_data = pesquisa_pessoa_cpf((cpf).replace('.','').replace('-',''))
        print(response_data)
        if response_data and 'docs' in response_data and len(response_data['docs']) > 0:
            pessoa_data = response_data['docs'][0]
            if pessoa_data.get('anoObito_s'):
                return JsonResponse({
                    'success': True,
                    'pessoa': pessoa_data,
                    'mensagem_obito': f"Consta na base da Receita Federal o óbito de {pessoa_data.get('nomeContribuinte_s')}, responsável pelo CPF {cpf}, em {pessoa_data.get('anoObito_s')}."
                    })
            else:
                # print(pessoa_data)
                return JsonResponse({'success': True, 'pessoa': pessoa_data})
        else:
            return JsonResponse({'success': False, 'error': 'Nenhum dado encontrado'})

    return JsonResponse({'success': False, 'error': 'Método não permitido'})

def verificar_sessao(request):
    pessoas = json.loads(request.session.get('pessoas', '[]'))
    return JsonResponse({'pessoas': pessoas})