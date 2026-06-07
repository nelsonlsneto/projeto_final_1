# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import shutil
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

############################################################################
# LENDO DADOS PARQUET DA DIMENSÃO DE AUTORIA
path_aut = Path(r".\Dados\Silver\slv_proposicoes_autoria.parquet")

try:
    df_aut = pd.read_parquet(path_aut)
except:
    print("Sem novas proposições")
    sys.exit()

# LENDO DADOS PARQUET PARTICIONADOS

path_prop = Path(r".\Dados\Silver\slv_proposicoes.parquet")

df_prop = pd.read_parquet(
    path_prop,
    filters=[
        ('dataApresentacao_data', '>=', start_date.strftime("%Y-%m-%d")),
        ('dataApresentacao_data', '<=', end_date.strftime("%Y-%m-%d"))
    ]
)

# TRATAMENTO DAS TABELAS

df_prop = df_prop[['id', 'codTipo', 'ementa', 'dataApresentacao_data']]

df_prop.rename(columns={'codTipo': 'codigo_tipo_sigla', 'dataApresentacao_data': 'data_apresentacao'}, inplace=True)

df_aut = df_aut[['proposicao', 'nome', 'codTipo']]

df_aut.rename(columns={'codTipo': 'codigo_tipo'}, inplace=True)


# Fazendo join entre as duas tabelas para trazer o autor de cada proposição na tabela final gold
df_merge = pd.merge(df_prop, df_aut, left_on='id', right_on='proposicao', how="left")

df_merge = df_merge[['id', 'codigo_tipo_sigla', 'ementa', 'data_apresentacao', 'nome', 'codigo_tipo']]

df_merge.rename(columns={'nome': 'nome_autor'}, inplace=True)

# SALVANDO OS DADOS

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_proposicoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_merge['data_apresentacao'].astype(str).drop_duplicates().tolist()

# 3) Deleta manualmente apenas as pastas que serão impactadas
for data in particoes_alvo:
    # Garante a conversão para string no formato YYYY-MM-DD se for do tipo date/datetime
    data_str = str(data) 
    pasta_particao = caminho_salvar / f"data_apresentacao={data_str}"
    print(pasta_particao)
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao)

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_merge.to_parquet(
    path = caminho_salvar,
    partition_cols = ['data_apresentacao'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")