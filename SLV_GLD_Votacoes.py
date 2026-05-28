# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS

path_vot = Path(r".\Dados\Silver\slv_votacoes.parquet")

path_det = Path(r".\Dados\Silver\slv_votacoes_detalhes.parquet")

df_vot = pd.read_parquet(path_vot)

df_det = pd.read_parquet(path_det)

# TRATAMENTO DAS TABELAS

df_vot = df_vot[['id', 'data', 'proposicaoObjeto', 'descricao', 'aprovacao']]

df_vot.rename(columns={'id': 'id_votacao', 'proposicaoObjeto': 'proposicao_objeto'}, inplace=True)

df_det = df_det[['votacao_id', 'votacao_idOrgao', 'votacao_descricao', 'origem_lista', 'id', 'ementa']]

df_det.rename(columns={'id': 'id_proposicao'}, inplace=True)

df_merge = pd.merge(df_vot, df_det, left_on='id_votacao', right_on='votacao_id', how="left")

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_votacoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_merge.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")