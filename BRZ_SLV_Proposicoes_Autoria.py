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

df_explodido = df_json.explode('autoria').reset_index(drop=True)

df_autoria = pd.json_normalize(df_explodido['autoria'])

df_final = pd.concat([df_explodido[['proposicao']], df_autoria], axis=1)

# Escolhendo as colunas no df final

colunas = ['proposicao', 'nome', 'codTipo', 'tipo', 'ordemAssinatura', 'proponente']

df_final = df_final[colunas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")