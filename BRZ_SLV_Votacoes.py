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

path = Path(r".\Dados\Bronze\brz_votacoes.json")

try:
    with open(path, "r", encoding="utf-8") as f:
        dados_json = json.load(f)
except FileNotFoundError:
    print(f"Arquivo Bronze não encontrado em: {path}")
    sys.exit()

lista_achatada = dados_json

# Cria DataFrame
if not lista_achatada:
    print("Sem novas votações (JSON vazio).")
    sys.exit()

try:
    df_final = pd.DataFrame(lista_achatada)
except Exception as e:
    print(f"Erro ao criar DataFrame: {e}")
    sys.exit()

# Filtra apenas as colunas desejadas
colunas = [
    "id",
    "data",
    "dataHoraRegistro",
    "siglaOrgao",
    "proposicaoObjeto",
    "descricao",
    "aprovacao",
]

df_final = df_final[colunas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_votacoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_final['data'].astype(str).drop_duplicates().tolist()

# 3) Deleta manualmente apenas as pastas que serão impactadas
for data in particoes_alvo:
    # Garante a conversão para string no formato YYYY-MM-DD se for do tipo date/datetime
    data_str = str(data) 
    pasta_particao = caminho_salvar / f"data={data_str}"
    print(pasta_particao)
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao)

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_final.to_parquet(
    path = caminho_salvar,
    partition_cols = ['data'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")