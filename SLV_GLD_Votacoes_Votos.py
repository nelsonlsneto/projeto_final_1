# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS

path = Path(r".\Dados\Silver\slv_votacoes_votos.parquet")

df_vot = pd.read_parquet(path)

# TRATAMENTO DAS TABELAS

df_vot = df_vot[['votacao', 'tipoVoto', 'deputado_.id']]

df_vot.rename(columns={'votacao': 'id_votacao', 'tipoVoto': 'tipo_voto', 'deputado_.id': 'deputado_id'}, inplace=True)

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_votacoes_votos.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_vot.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")