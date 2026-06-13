# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_proposicoes_autoria.json")

try:
    with open(path, "r", encoding="utf-8") as f:
        dados_json = json.load(f)
except:
    print("Sem novas proposições")
    sys.exit()

df = pd.json_normalize(
    dados_json, 
    record_path=['autoria'], 
    meta=['proposicao']
)

# Escolhendo as colunas no df final

colunas = ['proposicao', 'nome', 'codTipo', 'tipo', 'ordemAssinatura', 'proponente']

df_final = df[colunas]


df_final = df_final.drop_duplicates(subset=["proposicao"])

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")