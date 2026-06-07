# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import shutil
import sys

############################################################################
# LENDO DADOS JSON

path = Path(r".\Dados\Bronze\brz_deputados_despesas.json")

try:
    df_json = pd.read_json(path)
except:
    print("Sem novas despesas")
    sys.exit()

df_explodido = df_json.explode('despesa').reset_index(drop=True)

df_despesas = pd.json_normalize(df_explodido['despesa'])

df_final = pd.concat([df_explodido[['deputado']], df_despesas], axis=1)

# Escolhendo as colunas no df final

colunas = ['deputado', 'tipoDespesa', 'codDocumento', 'codTipoDocumento', 'dataDocumento', 'numDocumento', 'valorDocumento', 'nomeFornecedor', 'valorLiquido', 'valorGlosa', 'numRessarcimento', 'codLote', 'parcela', 'ano', 'mes']

df_final = df_final[colunas]

# SALVANDO OS DADOS

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_deputados_despesas.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_final[['ano', 'mes']].drop_duplicates().values

# 3) Deleta manualmente apenas as pastas que serão impactadas
for ano, mes in particoes_alvo:
    pasta_particao = caminho_salvar / f"ano={ano}" / f"mes={mes}"
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao) # Limpa a pasta específica

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_final.to_parquet(
    path = caminho_salvar,
    partition_cols = ['ano', 'mes'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")