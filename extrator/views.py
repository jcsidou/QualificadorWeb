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
from openai import OpenAI

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
    'Motorista': 'Agente'
}

def limpar_texto(texto):
    try:
        # Substituir marcas de parágrafo e quebras de linha por espaços
        texto = re.sub(r'\n', ' ', texto)
        # Remover espaços duplos
        texto = re.sub(r'\s+', ' ', texto)
        # Remover espaços antes de sinais de pontuação
        texto = re.sub(r'\s+([.,;?!])', r'\1', texto)
        texto = texto.strip()
    except:
        print('Erro ao limpar o texto')
    finally:
        print(f'''"{texto}"''')
        return texto

def atualizar_condicao(condicao):
    for chave, valor in CONDICOES_SUBSTITUICOES.items():
        if chave in condicao:
            return valor
    return condicao

def formatar_ensino(grau_instrucao):
    try:
        return re.sub(r' completo', '', grau_instrucao)
    except:
        return None

def extrair_numeros(cpf):
    if (not cpf):
        return None
    return re.sub(r'\D', '', cpf)

def formatar_cpf(cpf):
    try:
        cpf = extrair_numeros(cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf
    except:
        return None

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
    if (not texto):
        return None
    # Função para limpar e extrair informações usando regex
    dados_extracao = {}
    for chave, padrao in regex_parametros.items():
        match = re.search(padrao, texto)
        if match:
            dados_extracao[chave] = match.group(1)
    return dados_extracao

def remove_newlines(d):
    return {k: (v.replace('\n', ' ').strip() if isinstance(v, str) else v) for k, v in d.items()}

# View para upload de arquivo
@csrf_exempt
def upload_file_view(request):
    if request.method == 'POST':
        # Limpar JSON da sessão
        request.session['participantes'] = json.dumps([])

        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = request.FILES['file']
            if arquivo.name.endswith('.pdf'):
                texto = extrair_texto_pdf(arquivo)
                regex = r"Participante:\s+(?P<No_Participante>\d+)\s+-\s+(?P<Condicao>\w*\s?\w*)\s*(?P<Presente>\w+)?\nEndere.o:\s+(?P<Endereco>.*\n?.*\n)Endere.o\s\w+:(?P<Endereco_Profissional>.*)([\w*\s]*\?\s?(?P<Requer_Protetiva>Sim|Não))?Estado\sCivil:\s+(?P<Estado_Civil>.*).*\sGrau\sde\s.nstru..o:\s(?P<Grau_de_Instrucao>[\s\S\n]{,30})?Cor.\w+:\s(?P<Cor_Pele>.*)\nNaturalidade:\s((?P<Natural_Cidade>.*)[\n|\s](?P<Natural_UF>[A-Z]{2}))?\s?Nacionalidade:\s(?P<Nacionalidade>.*)\sCor .lhos:\s(?P<Cor_olhos>[A-Z][a-z|\s]*)(?P<Nome>[[A-Z|\s]*)\sNome:\s(?P<Pai>[\w|\s|-]*)\s\/\s(?P<Mae>[\w|\s|-]*)\sPai.*\n\w*\s\w+:\s(?P<Data_Nascimento>\d{2}/\d{2}/\d{4})\sSexo:\s(?P<Sexo>\w*\s?\w*)\sCPF:\s?(?P<CPF>(\d{3}\.\d{3}\.\d{3}.\d{2})?)\nDocumento:\s(?P<Documento>.*)\sNúmero:\s?(?P<No_Documento>\d*)\nProfi\w+:\s(?P<Profissao>.*)?Cargo:\s(?P<Cargo>.*)?Cond\w*\s\w*:\s(?P<Condicao_Fisica>.*)?"
            else:
                texto = realizar_ocr(arquivo)
            
            matches = re.finditer(regex, texto, re.MULTILINE)
            participantes = []
            for matchNum, match in enumerate(matches, start=1):
                participante = match.groupdict()
                # for key, value in participante.items():
                #     if value:
                #         participante[key] = value.replace('\n', ' ') 
                #         participante[key] = value.replace('  ', ' ') 
                #     print(key, value)
                # Adicionar ID único para cada participante
                participante['id'] = matchNum
                participantes.append(participante)

                # data_nascimento_str = participante.get('Data_Nascimento')
                # data_nascimento = None
                # if data_nascimento_str:
                #     try:
                #         # Converte a data para o formato YYYY-MM-DD
                #         data_nascimento = datetime.strptime(data_nascimento_str, "%d/%m/%Y").date()
                #     except ValueError:
                #         # Trata o erro se o formato da data estiver incorreto
                #         raise ValidationError(f"Data de nascimento {data_nascimento_str} está em um formato inválido.")

                # Criar objeto Pessoa com os dados extraídos
                # pessoa = Pessoa(
                #     nome=limpar_texto(participante.get('Nome', '')),
                #     condicao=atualizar_condicao(limpar_texto(participante.get('Condicao', ''))),
                #     nome_pai=participante.get('Pai', '')),
                #     nome_mae=limpar_texto(participante.get('Mae', '')),
                #     data_nascimento=data_nascimento,
                #     sexo=limpar_texto(participante.get('Sexo', '')),
                #     cpf=formatar_cpf(extrair_numeros(limpar_texto(participante.get('CPF', '')))),
                #     estado_civil=limpar_texto(participante.get('Estado_Civil', '')),
                #     grau_instrucao=formatar_ensino(limpar_texto(participante.get('Grau_de_Instrucao', ''))),
                #     cor_pele=limpar_texto(participante.get('Cor_Pele', '')),
                #     naturalidade=limpar_texto(participante.get('Natural_Cidade', '')),
                #     naturalidade_UF=limpar_texto(participante.get('Natural_UF', '')),
                #     nacionalidade=limpar_texto(participante.get('Nacionalidade', '')),
                #     documento=limpar_texto(participante.get('Documento', '')),
                #     numero_documento=limpar_texto(participante.get('No_Documento', '')),
                #     endereco=limpar_texto(participante.get('Endereco', '')),
                #     profissao=limpar_texto(participante.get('Profissao', '')),
                #     end_profissional=limpar_texto(participante.get('Endereco_Profissional', '')),
                # )

                # pessoa.save()

            # Converter lista de dicionários para JSON
            participantes_sem_quebras = [remove_newlines(d) for d in participantes]
            # participantes_json = json.dumps(participantes_sem_quebras, indent=4, ensure_ascii=False)
            # print("Participantes JSON:", participantes_json)  # Adicionar print para depuração
            write_json_to_session(request, participantes_sem_quebras)

            # Verificar se os dados foram escritos na sessão
            # session_data = read_json_from_session(request)
            # print("Dados na sessão após escrita:", session_data)  # Adicionar print para depuração
            
            return redirect('upload_success')
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

# Atualizar pessoa
@csrf_exempt
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

        # Atualizar JSON na sessão
        json_data = read_json_from_session(request)
        for p in json_data:
            if p['id'] == pessoa.id:  # Use ID como identificador único
                p.update({
                    'nome': pessoa.nome,
                    'condicao': pessoa.condicao,
                    'alcunha': pessoa.alcunha,
                    'nome_pai': pessoa.nome_pai,
                    'nome_mae': pessoa.nome_mae,
                    'data_nascimento': pessoa.data_nascimento,
                    'sexo': pessoa.sexo,
                    'cpf': pessoa.cpf,
                    'estado_civil': pessoa.estado_civil,
                    'grau_instrucao': pessoa.grau_instrucao,
                    'cor_pele': pessoa.cor_pele,
                    'naturalidade': pessoa.naturalidade,
                    'naturalidade_UF': pessoa.naturalidade_UF,
                    'nacionalidade': pessoa.nacionalidade,
                    'cor_olhos': pessoa.cor_olhos,
                    'documento': pessoa.documento,
                    'numero_documento': pessoa.numero_documento,
                    'endereco': pessoa.endereco,
                    'profissao': pessoa.profissao,
                    'cargo': pessoa.cargo,
                    'condicao_fisica': pessoa.condicao_fisica,
                    'end_profissional': pessoa.end_profissional,
                    'representa': pessoa.representa
                })
                break
        write_json_to_session(request, json_data)

        # Atualizar qualificação
        qualificacao = qualificar_pessoa(pessoa)
        return JsonResponse({'qualificacao': qualificacao})
    return HttpResponseNotAllowed(['POST'])

# Adicionar pessoa
@csrf_exempt
def add_person(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Limpar os dados de entrada
        for key in data:
            if isinstance(data[key], str):
                data[key] = limpar_texto(data[key])
        # Atualizar condição
        data['condicao'] = atualizar_condicao(data.get('condicao', ''))
        # Atualizar grau de instrução
        data['grau_instrucao'] = formatar_ensino(data.get('grau_instrucao', ''))
        # Extrair apenas números do CPF
        data['cpf'] = extrair_numeros(data.get('cpf', ''))

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

        # Atualizar JSON na sessão
        json_data = read_json_from_session(request)
        pessoa_data = data
        pessoa_data['id'] = pessoa.id
        pessoa_data['cpf'] = formatar_cpf(pessoa_data['cpf'])
        json_data.append(pessoa_data)
        write_json_to_session(request, json_data)

        return JsonResponse(pessoa_data, status=201)
        
# Remover pessoa
@csrf_exempt
def remove_person(request, id):
    if request.method == 'DELETE':
        try:
            pessoa = Pessoa.objects.get(id=id)
            pessoa_id = pessoa.id  # Usar ID como identificador único
            pessoa.delete()

            # Atualizar JSON na sessão
            json_data = read_json_from_session(request)
            json_data = [p for p in json_data if p.get('id') != pessoa_id]
            write_json_to_session(request, json_data)

            return JsonResponse({'status': 'success'})
        except Pessoa.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Pessoa não encontrada'}, status=404)
    return HttpResponseNotAllowed(['DELETE'])

# Qualificar todas as pessoas
def qualificar_todos(request):
    client = OpenAI(api_key=openai_api_key)
    if request.method == 'POST':
        json_content = read_json_from_session(request)

        json_str = json.dumps(json_content)
        messages_to_model = [
            {"role": "system", "content": "Responda em português."},
            {"role": "assistant", "content": "Cumpra exatamente as instruções passadas e nao adicione informações de qualquer natureza, a menos que instruido a fazer isso."},
            {"role": "user", "content": "Qualifique todas as partes no arquivo Json que eu mandar em forma de texto fluido, de acordo com o exemplo fornecido."},
            {"role": "user", "content": "Eu nao quero dados estruturados, eu quero que voce os converta em um texto amigável e fluido."},
            {"role": "user", "content": "Se não obtiver alguma informação, indique que 'não foi esclarecida', 'não apurado', 'não informado' ou coisa semelhante."},
            {"role": "user", "content": "O nome deve vir completo, todo em letras maiúsculas."},
            {"role": "user", "content": "Na nacionalidade, não há necessidade de citar 'nato', em caso de brasileiro."},
            {"role": "user", "content": "Para introduzir o numero do CPF prefira formulas como 'inscrito no C.P.F. sob nº'"},
            {"role": "user", "content": "Para introduzir o numero do documento de identidade, 'portador do documento de identidade nº %NUMERO%,' e acrescente o órgão emissor, se houver a informação, 'emitido por %ORGAO%'."},
            {"role": "user", "content": "Ajuste o uso de maiusculas e minusculas na grafia do endereço."},
            {"role": "user", "content": "Forneça apenas o conteúdo solicitado, nenhum texto adicional."},
            {"role": "user", "content": "Para calcular a idade das pessoas, considera 12/04/2017 como data do fato."},
            {"role": "user", "content": f"Aqui está o arquivo JSON:\n{json_str}"},
            {"role": "user", "content": f"""Exemplo de formato, onde %% indicam uma variável fornecida: '%NOME%, %nacionalidade%, %estado_civil%, %profissao%, %Grau_de_Instrucao%, portador do %Documento_Tipo% nº %No_documento%, , inscrito no C.P.F. sob nº %CPF%, filho de %Pai% e de %Mae%, natural de %Natural_Cidade%/%Natural_UF%, nascido em %data_nascimento(por extenso)%, contando %idade_nos_fatos% anos na época do fato, de pele %pele%, com endereço na %endereço%'"""},            
        ]
        response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages_to_model,
                max_tokens=2000,
                n=1,
                stop=None,
                temperature=0.1,
            )

        resposta = response.choices[0].message.content
        print(resposta)

        return JsonResponse({'response': resposta})
    else:
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
# Função para ler JSON da sessão
def read_json_from_session(request):
    json_data = request.session.get('participantes', '[]')
    return json.loads(json_data) if isinstance(json_data, str) else json_data

# Função para escrever JSON na sessão
def write_json_to_session(request, data):
    request.session['participantes'] = json.dumps(data)
    json_data= request.session.get('participantes', '[]')
        
def qualificar_pessoa(pessoa):
    # Adicionar código para qualificar a pessoa
    # Certifique-se de que todos os campos necessários estejam sendo usados corretamente
    result = []
    feminino = False
    try:
        if pessoa.sexo.lower() == 'feminino':
            feminino = True
    except:
        pass

    nome = pessoa.nome.upper() if pessoa.nome else "Nome não informado"
    nacionalidade = pessoa.nacionalidade.lower() if pessoa.nacionalidade else "nacionalidade não esclarecida"
    estado_civil = pessoa.estado_civil.lower() if pessoa.estado_civil else "estado civil não informado"
    profissao = pessoa.profissao.lower() if pessoa.profissao else "profissão não informada"
    grau_instrucao = pessoa.grau_instrucao.lower().replace(" completo", "") if pessoa.grau_instrucao else "grau de instrução não apurado"
    
    result.append(f'{nome}, ')
    result.append(f'{nacionalidade}, ')
    result.append(f'{estado_civil}, ')
    result.append(f'{profissao}, ')
    result.append(f'de instrução {grau_instrucao}, ')

    pai_declarado = bool(pessoa.nome_pai and pessoa.nome_pai != "-" and pessoa.nome_pai.lower() != "desconhecido")
    mae_declarada = bool(pessoa.nome_mae and pessoa.nome_mae != "-" and pessoa.nome_mae.lower() != "desconhecida")

    if not pai_declarado and not mae_declarada:
        result.append('filiação desconhecida, ')
    else:
        if feminino:
            result.append('filha de ')
        else:
            result.append('filho de ')

        if pai_declarado:
            result.append(pessoa.nome_pai)

        if pai_declarado and mae_declarada:
            result.append(' e de ')

        if mae_declarada:
            result.append(f'{pessoa.nome_mae}, ')

    if feminino:
        result.append('nascida em ')
    else:
        result.append('nascido em ')
    
    if pessoa.data_nascimento:
        formatted_date = pessoa.data_nascimento.strftime('%d/%m/%Y')
        result.append(f'{formatted_date}, ')
    else:
        result.append('data não esclarecida, ')

    naturalidade = f'natural de {pessoa.naturalidade}, ' if pessoa.naturalidade else 'em local não informado, '
    result.append(naturalidade)

    if feminino:
        result.append('inscrita no C.P.F. sob nº ')
    else:
        result.append('inscrito no C.P.F. sob nº ')

    cpf = formatar_cpf(pessoa.cpf) if pessoa.cpf else 'não informado, '
    result.append(f'{cpf}, ')

    if pessoa.endereco:
        result.append(f'com endereço na {pessoa.endereco}, ')
    elif pessoa.end_profissional:
        result.append(f'com endereço profissional na {pessoa.end_profissional}, ')

    retorno = ' '.join(result).strip()

    retorno = flexiona(retorno, feminino)
    retorno = ajuste_geral(retorno)

    return retorno

def flexiona(texto, feminino):
    if feminino:
        texto = texto.replace("brasileiro", "brasileira")
        texto = texto.replace("nato", "nata")
        texto = texto.replace("solteiro", "solteira")
        texto = texto.replace("viúvo", "viúva")
        texto = texto.replace("separado", "separada")
        texto = texto.replace("divorciado", "divorciada")
        texto = texto.replace("amigado", "amigada")
    return texto

def ajuste_geral(texto):
    try:
        while ("  " in texto or
            " ," in texto or
            " ." in texto or
            " ;" in texto or
            "\n " in texto or
            " \n" in texto or
            "\n." in texto or
            "\n\n" in texto):
            texto = texto.replace("    ", "  ")
            texto = texto.replace("   ", "  ")
            texto = texto.replace("  ", " ")
            texto = texto.replace(" ,", ",")
            texto = texto.replace(" .", ".")
            texto = texto.replace(" ;", ";")
            texto = texto.replace("\n\n", "\n")
            texto = texto.replace("\n ", "\n")
            texto = texto.replace(" \n", "\n")
            texto = texto.replace("\n.", ".")
        return texto
    except Exception as e:
        raise ValueError("Erro no ajuste geral do texto") from e

def upload_success_view(request):
    # Ler JSON da sessão
    try:
        participantes_json = read_json_from_session(request)
        print("Dados da sessão lidos:", participantes_json)  # Adicionar print para depuração
    except json.JSONDecodeError as e:
        print("Erro ao decodificar JSON:", e)
        participantes_json = []

    pessoas = []

    for idx, p in enumerate(participantes_json):
        if not isinstance(p, dict):
            print(f"Ignorando participante {idx}: não é um dicionário")
            continue

        pessoa_id = p.get('id', idx)
        pessoa = Pessoa(
            id=pessoa_id,
            condicao=p.get('Condicao', '').strip(),
            alcunha=p.get('Alcunha', ''),
            nome=p.get('Nome', '').strip(),
            nome_pai=p.get('Pai', ''),
            nome_mae=p.get('Mae', ''),
            data_nascimento=datetime.strptime(p.get('Data_Nascimento', ''), "%d/%m/%Y").date() if p.get('Data_Nascimento') else None,
            sexo=p.get('Sexo', '').strip(),
            cpf=p.get('CPF', ''),
            cor_pele=p.get('Cor_Pele', ''),
            estado_civil=p.get('Estado_Civil', ''),
            grau_instrucao=p.get('Grau_de_Instrucao', ''),
            naturalidade=p.get('Natural_Cidade', ''),
            naturalidade_UF=p.get('Natural_UF', ''),
            nacionalidade=p.get('Nacionalidade', ''),
            documento=p.get('Documento', ''),
            numero_documento=p.get('No_Documento', ''),
            endereco=p.get('Endereco', ''),
            end_profissional=p.get('Endereco_Profissional', ''),
            profissao=p.get('Profissao', ''),
            representa=p.get('Representa', False)
        )

        pessoa.qualificacao = qualificar_pessoa(pessoa)
        pessoas.append(pessoa)

    print("Pessoas a serem passadas para o template:", pessoas)  # Adicionar print para depuração

    return render(request, 'extrator/success.html', {'pessoas': pessoas})

# Função para ler JSON da sessão
def read_json_from_session(request):
    json_data = request.session.get('participantes', '[]')
    print("Dados da sessão brutos:", json_data)  # Adicionar print para depuração
    if isinstance(json_data, str):
        try:
            return json.loads(json_data)
        except json.JSONDecodeError as e:
            print("Erro ao decodificar JSON da sessão:", e)
            return []
    return json_data

# Função para escrever JSON na sessão
def write_json_to_session(request, data):
    if not isinstance(data, list):
        print("Dados fornecidos não são uma lista.")
        return
    for item in data:
        if not isinstance(item, dict):
            print(f"Item não é um dicionário: {item}")
            return
    request.session['participantes'] = json.dumps(data)
