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

path = Path(r".\Dados\Bronze\brz_votacoes_votos.json")

# 1. Carrega o arquivo JSON como uma lista/dicionário Python puro
try:
    with open(path, "r", encoding="utf-8") as f:
        dados_brutos = json.load(f)
except:
    print("Sem novas votações")
    sys.exit()

# 2. Agora o json_normalize funcionará perfeitamente
df_final = pd.json_normalize(
    dados_brutos, record_path=["votos"], meta=["votacao"]
)

# Criando coluna data para partição
df_final["dataRegistroVoto"] = pd.to_datetime(df_final["dataRegistroVoto"])

df_final["dataRegistroVoto_data"] = df_final["dataRegistroVoto"].dt.date

## Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_votacoes_votos.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_final['dataRegistroVoto_data'].astype(str).drop_duplicates().tolist()

# 3) Deleta manualmente apenas as pastas que serão impactadas
for data in particoes_alvo:
    # Garante a conversão para string no formato YYYY-MM-DD se for do tipo date/datetime
    data_str = str(data) 
    pasta_particao = caminho_salvar / f"dataRegistroVoto_data={data_str}"
    print(pasta_particao)
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao)

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_final.to_parquet(
    path = caminho_salvar,
    partition_cols = ['dataRegistroVoto_data'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")