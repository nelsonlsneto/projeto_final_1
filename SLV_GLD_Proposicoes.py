# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS

path_prop = Path(r".\Dados\Silver\slv_proposicoes.parquet")

path_aut = Path(r".\Dados\Silver\slv_proposicoes_autoria.parquet")

df_prop = pd.read_parquet(path_prop)

df_aut = pd.read_parquet(path_aut)

# TRATAMENTO DAS TABELAS

df_prop = df_prop[['id', 'codTipo', 'ementa', 'dataApresentacao']]

df_prop.rename(columns={'codTipo': 'codigo_tipo_sigla', 'dataApresentacao': 'data_apresentacao'}, inplace=True)

df_aut = df_aut[['proposicao_id', 'nome', 'codTipo']]

df_aut.rename(columns={'codTipo': 'codigo_tipo'}, inplace=True)

df_merge = pd.merge(df_prop, df_aut, left_on='id', right_on='proposicao_id', how='left')

df_merge = df_merge[['id', 'codigo_tipo_sigla', 'ementa', 'data_apresentacao', 'nome', 'codigo_tipo']]

# Tratando coluna de data
df_merge['data_apresentacao'] = pd.to_datetime(df_merge['data_apresentacao'])

df_merge['data_apresentacao'] = df_merge['data_apresentacao'].dt.date

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_proposicoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_merge.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")