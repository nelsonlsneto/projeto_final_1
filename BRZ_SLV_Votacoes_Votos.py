# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_votacoes_votos.json")

# 1. Carrega o arquivo JSON como uma lista/dicionário Python puro
with open(path, "r", encoding="utf-8") as f:
    dados_brutos = json.load(f)

# 2. Agora o json_normalize funcionará perfeitamente
df_final = pd.json_normalize(
    dados_brutos, record_path=["votos"], meta=["votacao"]
)

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_votacoes_votos.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")