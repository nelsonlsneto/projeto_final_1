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
    current_date = current_date + relativedelta(months=1)

############################################################################
# 1) BAIXANDO DADOS DE VOTAÇÕES

votacao = []
contador = 1

while contador <= 100:
    
    url = f'https://dadosabertos.camara.leg.br/api/v2/votacoes?dataInicio={data_ini}&ordem=DESC&ordenarPor=dataHoraRegistro&pagina={contador}&itens=100'

    response = requests.get(url, timeout = 60)

    if response.status_code == 200:
        print("A requisição das votações deu certo!")

        if response.json()['dados'] != []:

            dados_api = response.json()['dados']

            print(contador) #print para acompanhar as requisições

            votacao.append(dados_api)

            contador += 1

            time.sleep(1)
                
        else:
            contador = 101  # Isto vai fazer o loop while parar

    else:
        print("A requisição das votações não deu certo  :(")

# Salvando os dados json

caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes.json"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
    json.dump(votacao, arquivo, indent=4, ensure_ascii=False)

print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

###############################################################################
# 2) BAIXANDO DADOS DE CADA ID DE VOTAÇÃO

# Recuperando os ids de cada votação
try:
    ids = [registro["id"] for registro in votacao[0]]
except:
    print("Sem novas votações")
    sys.exit()

votacao_final = []

for id in ids:
    url = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id}'

    response = requests.get(url)

    if response.status_code == 200:
        print(f"A requisição da votação {id} deu certo!")

        dados_json = response.json()['dados']
          
        votacao_final.append(dados_json)

    else:
        print(f"A requisição da votação {id} não deu certo  :(")
            
# Salvando os dados json
caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes_detalhes.json"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
    json.dump(votacao_final, arquivo, indent=4, ensure_ascii=False)

print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")

###############################################################################
# 3) BAIXANDO DADOS DE CADA VOTO

votos_final = []

for id in ids:
    url = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{id}/votos'

    response = requests.get(url)

    if response.status_code == 200:
        print(f"A requisição dos votos da votação {id} deu certo!")

        dados_json = response.json()

        if response.json()['dados'] != []:

            votos = {}

            votos['votacao'] = id
            votos['votos'] = dados_json['dados']
          
            votos_final.append(votos)

    else:
        print(f"A requisição dos votos da votação {id} não deu certo  :(")
            
# Salvando os dados json
caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes_votos.json"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
    json.dump(votos_final, arquivo, indent=4, ensure_ascii=False)

print(f"Sucesso! Arquivo JSON salvo em: {caminho_salvar}")