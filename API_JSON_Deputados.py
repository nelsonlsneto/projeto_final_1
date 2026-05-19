# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

# PARÂMETROS

############################################################################
# Podemos alterar manualmente a data inicial para pegar dados históricos (formato YYYY-MM-DD)

data_ini = ''

############################################################################

if data_ini == '':
    data_ini = datetime.now().strftime("%Y-%m-%d")

data_hoje = datetime.now().strftime("%Y-%m-%d")

start_date = datetime.strptime(data_ini, "%Y-%m-%d")
end_date = datetime.strptime(data_hoje, "%Y-%m-%d")

dates = []
current_date = start_date

while current_date <= end_date:
    dates.append(current_date)
    current_date = current_date + relativedelta(months=1)

############################################################################
# 1) BAIXANDO DADOS DE TODOS OS DEPUTADOS ATIVOS

url = 'https://dadosabertos.camara.leg.br/api/v2/deputados'

response = requests.get(url, timeout = 15)

dados_api = response.json()

if response.status_code == 200:
    print("A requisição dos deputados deu certo!")
    
    # Salvando os dados json

    caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_deputados.json"

    # 1) Cria a pasta se ela não existir
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    # 2) Salvando
    with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
        json.dump(dados_api, arquivo, indent=4, ensure_ascii=False)

    print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

else:
    print("A requisição dos deputados não deu certo  :(")

###############################################################################
# 2) BAIXANDO DADOS DE DESPESAS DE CADA DEPUTADO

if response.status_code == 200:
    print("A requisição das despesas dos deputados deu certo!")

    # Recuperando os ids de cada deputado
    ids = []

    for d in dados_api['dados']:
        ids.append(d['id'])

    despesas_final = []

    for i in ids:
        for date in dates:
            for pag in range(1, 3):
                url = f'https://dadosabertos.camara.leg.br/api/v2/deputados/{i}/despesas?ano={date.year}&mes={date.month}&ordem=ASC&ordenarPor=ano&pagina={pag}&itens=100'
                response = requests.get(url)

                dados_json = response.json()

                if dados_json['dados'] != []:
                    despesas = {}
                
                    despesas['deputado'] = i
                    despesas['periodo'] = date.strftime("%Y-%m")
                    despesas['despesa'] = dados_json['dados']

                    despesas_final.append(despesas)

    # Salvando os dados json

    caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_despesas_deputados.json"

    # 1) Cria a pasta se ela não existir
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    # 2) Salvando
    with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
        json.dump(despesas_final, arquivo, indent=4, ensure_ascii=False)

    print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

else:
    print("A requisição das depesas dos deputados não deu certo  :(")