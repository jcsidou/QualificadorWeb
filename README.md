Para acessar a API, gere na raiz um arquivo configs.JSON com a seguinte estrutura
{
    "OpenAI_API_KEY": "YOUR_API_KEY",
    "Google_Maps_API_KEI": "GOOGLE_MAPS_API_KEY",
    "regex_pessoas": "" uma expressão regular que deve retornar grupos denominados para os valores:
    
    <no_participante>
    <condicao>
    <presente>
    <endereco>
    <end_profissional>
    <requer_protetiva>
    <estado_civil>
    <grau_instrucao>
    <cor_pele>
    <naturalidade>
    <naturalidade_uf>
    <nacionalidade>
    <cor_olhos>
    <nome>
    <nome_pai>
    <nome_mae>
    <data_nascimento>
    <sexo>
    <cpf>
    <documento>
    <numero_documento>
    <profissao>
    <cargo>
    <condicao_fisica>
    Exemplo:
    "Participante:\s+(?P<no_participante>\d+)\s+-\s+(?P<condicao>\w*\s?\w*)\s*(?P<presente>\w+)?\nEndere.o:\s+(?P<endereco>.*\n?.*\n)Endere.o\s\w+:(?P<end_profissional>.*)(\n?[\w|\s]*representar em juízo.\s*(?P<Representa>Sim|Não)\n?)?([\w*\s]*\?\s?(?P<requer_protetiva>Sim|Não))?Estado\sCivil:\s+(?P<estado_civil>.*).*\sGrau\sde\s.nstru..o:\s(?P<grau_instrucao>[\s\S\n]{,30})?Cor.\w+:\s(?P<cor_pele>.*)\nNaturalidade:\s((?P<naturalidade>.*)[\n|\s](?P<naturalidade_uf>[A-Z]{2}))?\s?Nacionalidade:\s(?P<nacionalidade>.*)\sCor\s.lhos:\s(?P<cor_olhos>[A-Z][a-z|\s]*)(?P<Nome>[\w\s]*)\sNome:\s(?P<nome_pai>[\w|\s|-]*)\s\/\s(?P<nome_mae>[\w|\s|-]*)\sPai.*\n\w*\s\w+:\s(?P<data_nascimento>\d{2}\/\d{2}\/\d{4})\sSexo:\s(?P<sexo>\w*\s?\w*)\sCPF:\s?(?P<cpf>(\d{3}\.\d{3}\.\d{3}.\d{2})?)\nDocumento:\s(?P<documento>.*)\sNúmero:\s?(?P<numero_documento>\d*)\nProfi\w+:\s(?P<profissao>.*)?Cargo:\s(?P<cargo>.*)?Cond\w*\s\w*:\s(?P<condicao_fisica>.*)?"
}
