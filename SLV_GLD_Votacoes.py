# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
import shutil

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
# LENDO DADOS PARQUET DA DIMENSÃO DE DETALHES

path_det = Path(r".\Dados\Silver\slv_votacoes_detalhes.parquet")

try:
    df_det = pd.read_parquet(path_det)
except:
    print("Sem novas votações")
    sys.exit()


# LENDO DADOS PARQUET PARTICIONADOS
path_vot = Path(r".\Dados\Silver\slv_votacoes.parquet")

df_vot = pd.read_parquet(
    path_vot,
    filters=[
        ('data', '>=', start_date.strftime("%Y-%m-%d")),
        ('data', '<=', end_date.strftime("%Y-%m-%d"))
    ]
)


# TRATAMENTO DAS TABELAS

df_vot = df_vot[['id', 'data', 'proposicaoObjeto', 'descricao', 'aprovacao']]

df_vot.rename(columns={'id': 'id_votacao', 'proposicaoObjeto': 'proposicao_objeto'}, inplace=True)

df_det = df_det[['votacao_id', 'votacao_idOrgao', 'votacao_descricao', 'origem_lista', 'id', 'ementa']]

df_det.rename(columns={'id': 'id_proposicao'}, inplace=True)

df_merge = pd.merge(df_vot, df_det, left_on='id_votacao', right_on='votacao_id', how="left")

df_merge.drop_duplicates(subset=["id_votacao"], inplace=True)

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_votacoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_merge['data'].astype(str).drop_duplicates().tolist()

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
df_merge.to_parquet(
    path = caminho_salvar,
    partition_cols = ['data'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")