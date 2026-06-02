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
# 1) BAIXANDO DADOS DE TODOS OS PARTIDOS DEPUTADOS ATIVOS

url = 'https://dadosabertos.camara.leg.br/api/v2/partidos?ordem=ASC&ordenarPor=sigla&itens=100'

response = requests.get(url, timeout = 15)

dados_api = response.json()

if response.status_code == 200:
    print("A requisição dos partidos deu certo!")

    partiidos = dados_api['dados']
    
    # Salvando os dados json

    caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_partidos.json"

    # 1) Cria a pasta se ela não existir
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    # 2) Salvando
    with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
        json.dump(partiidos, arquivo, indent=4, ensure_ascii=False)

    print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

else:
    print("A requisição dos partiidos não deu certo  :(")