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

# Desembrulha as listas internas (transforma lista de listas em lista única)
lista_achatada = [item for sublista in dados_json for item in sublista]

# Cria o DataFrame do Pandas
df = pd.DataFrame(lista_achatada)

# Extrai o último pedaço do texto da URI
df["proposicao_id"] = df["uri"].str.split("/").str[-1]

# Converte para número ignorando erros (textos vazios viram NaN)
df["proposicao_id"] = pd.to_numeric(df["proposicao_id"], errors="coerce")

# Remove as linhas que eram vazias/inválidas para poder transformar em int64
df = df.dropna(subset=["proposicao_id"])

# Agora converte com segurança para número inteiro
df["proposicao_id"] = df["proposicao_id"].astype("int64")

# Escolhendo as colunas no df final

colunas = ['proposicao_id', 'nome', 'codTipo', 'tipo', 'ordemAssinatura', 'proponente']

df_final = df[colunas]

df_final = df_final.drop_duplicates(subset=["proposicao_id"])

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")