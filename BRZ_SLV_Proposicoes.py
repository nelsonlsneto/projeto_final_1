# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_proposicoes.json")

# 1. Lê o arquivo de texto bruto
dados_brutos = path.read_text(encoding="utf-8")

# 2. Converte o texto em uma lista Python
dados_lista = json.loads(dados_brutos)

# 3. Extrai a lista interna [0] e cria o DataFrame diretamente
df_final = pd.DataFrame(dados_lista[0])

# 4. Filtra apenas as colunas desejadas
colunas = [
    "id",
    "siglaTipo",
    "codTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
]

df_final = df_final[colunas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")