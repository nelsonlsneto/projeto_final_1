# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_deputados.json")

df_json = pd.read_json(path)

# Escolhendo as colunas no df final

colunas = ["id", "nome", "siglaPartido", "siglaUf", "urlFoto"]

df_final = df_json[colunas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_deputados.csv"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_csv(caminho_salvar, index=False)

print(f"Sucesso! Arquivo CSV salvo em: {caminho_salvar}")