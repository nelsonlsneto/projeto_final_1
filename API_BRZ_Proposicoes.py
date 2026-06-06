# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import sys

# PARÂMETROS

############################################################################
# Podemos alterar manualmente a data inicial para pegar dados históricos (formato YYYY-MM-DD)

data_ini = ''

############################################################################

if data_ini == '':
    data_ini = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

data_ontem = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

start_date = datetime.strptime(data_ini, "%Y-%m-%d")
end_date = datetime.strptime(data_ontem, "%Y-%m-%d")

dates = []
current_date = start_date

while current_date <= end_date:
    dates.append(current_date)
    current_date = current_date + relativedelta(days=1)

############################################################################
# 1) BAIXANDO DADOS DE PROPOSIÇÕES

proposicao = []
contador = 1

for date in dates:
    while contador <= 100:
        url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes?dataApresentacaoInicio={date.strftime("%Y-%m-%d")}&ordem=ASC&ordenarPor=id&pagina={contador}&itens=100'

        response = requests.get(url, timeout = 60)

        if response.status_code == 200:
            print("A requisição das proposições deu certo!")

            if response.json()['dados'] != []:

                dados_api = response.json()['dados']

                print(date.strftime("%Y-%m-%d"), contador) #print para acompanhar as requisições

                proposicao.append(dados_api)

                contador += 1

                time.sleep(1)

            else:
                contador = 101  # Isto vai fazer o loop while parar

        else:
            print("A requisição das proposições não deu certo  :(")

# Salvando os dados json

caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_proposicoes.json"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
    json.dump(proposicao, arquivo, indent=4, ensure_ascii=False)

print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

###############################################################################
# 2) BAIXANDO DADOS DE AUTORIA DE CADA PROPOSIÇÃO

# Recuperando os ids de cada votação
try:
    ids = [registro["id"] for registro in proposicao[0]]
except:
    print("Sem novas proposições")
    sys.exit()

autoria_final = []

for id in ids:
    url = f'https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/autores'

    response = requests.get(url)

    if response.status_code == 200:
        print(f"A requisição da autoria da proposição {id} deu certo!")

        dados_json = response.json()

        autoria = {}
                
        autoria['proposicao'] = id
        autoria['autoria'] = dados_json['dados']
          
        autoria_final.append(autoria)

    else:
        print(f"A requisição da autoria da proposição {id} não deu certo  :(")
            
# Salvando os dados json
caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_proposicoes_autoria.json"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
    json.dump(autoria_final, arquivo, indent=4, ensure_ascii=False)

print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")