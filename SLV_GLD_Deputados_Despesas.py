# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Silver\slv_deputados_despesas.parquet")

df = pd.read_parquet(path)

# Escolhendo as colunas no df final

colunas = ['deputado', 'tipoDespesa', 'codDocumento', 'codTipoDocumento', 'dataDocumento', 'numDocumento', 'nomeFornecedor', 'valorLiquido']

df_final = df[colunas]

# Tratando coluna de data
df_final['dataDocumento'] = pd.to_datetime(df_final['dataDocumento'])

df_final['dataDocumento'] = df_final['dataDocumento'].dt.date

# Mantém apenas as linhas com valorLiquido maior ou igual a zero
df_final = df_final[df_final['valorLiquido'] >= 0]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_deputados_despesas.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Salvando
df_final.to_parquet(caminho_salvar, index=False)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")