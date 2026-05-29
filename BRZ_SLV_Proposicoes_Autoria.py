# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_proposicoes_autoria.json")

df_json = pd.read_json(path)

# Se o JSON vier no formato antigo, com a coluna 'autoria'
if "autoria" in df_json.columns:
    df_explodido = df_json.explode("autoria").reset_index(drop=True)
    df_autoria = pd.json_normalize(df_explodido["autoria"])

    df_final = pd.concat(
        [df_explodido["proposicao"], df_autoria],
        axis=1
    )

    df_final = df_final.rename(columns={
        "proposicao": "proposicao_id"
    })

# Se o JSON vier no formato novo, já aberto por autor
else:
    df_final = df_json.copy()

# Escolhendo as colunas no df final

colunas = ['proposicao_id', 'nome', 'codTipo', 'tipo', 'ordemAssinatura', 'proponente']

for coluna in colunas:
    if coluna not in df_final.columns:
        df_final[coluna] = None

df_final = df_final[colunas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")