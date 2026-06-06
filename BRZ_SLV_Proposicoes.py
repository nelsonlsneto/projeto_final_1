# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import shutil
import sys

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_proposicoes.json")

# 1. Lê o arquivo de texto bruto
dados_brutos = path.read_text(encoding="utf-8")

# 2. Converte o texto em uma lista Python
dados_lista = json.loads(dados_brutos)

# 3. Extrai a lista interna [0] e cria o DataFrame diretamente
try:
    df = pd.DataFrame(dados_lista[0])
except:
    print("Sem novas proposições")
    sys.exit()

# 4. Filtra apenas as colunas desejadas
colunas = [
    "id",
    "siglaTipo",
    "codTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
]

df = df[colunas]

# Criando coluna data para partição
df["dataApresentacao"] = pd.to_datetime(df["dataApresentacao"])

df["dataApresentacao_data"] = df["dataApresentacao"].dt.date

colunas = [
    "id",
    "siglaTipo",
    "codTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
    "dataApresentacao_data"
]

df_final = df[colunas]

# SALVANDO OS DADOS

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_final['dataApresentacao_data'].astype(str).drop_duplicates().tolist()

# 3) Deleta manualmente apenas as pastas que serão impactadas
for data in particoes_alvo:
    # Garante a conversão para string no formato YYYY-MM-DD se for do tipo date/datetime
    data_str = str(data) 
    pasta_particao = caminho_salvar / f"dataApresentacao_data={data_str}"
    print(pasta_particao)
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao)

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_final.to_parquet(
    path = caminho_salvar,
    partition_cols = ['dataApresentacao_data'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")