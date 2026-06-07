# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import shutil
import sys

# PARÂMETROS

############################################################################
# Podemos alterar manualmente a data inicial para pegar dados históricos (formato YYYY-MM-DD)

data_ini = ''

############################################################################

if data_ini == '':
    data_ini = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

data_ontem = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

start_date = datetime.strptime(data_ini, "%Y-%m-%d")
end_date = datetime.strptime(data_ontem, "%Y-%m-%d")

############################################################################
# LENDO DADOS PARQUET PARTICIONADOS

path = Path(r".\Dados\Silver\slv_deputados_despesas.parquet")

#Filtro das partições
periodo = pd.date_range(start=start_date, end=end_date, freq='D')

anos_meses = list(dict.fromkeys((data.year, data.month) for data in periodo))

filtros_particao = [
    [('ano', '==', ano), ('mes', '==', mes)] 
    for ano, mes in anos_meses
]

#Lendo parquet
try:
    df = pd.read_parquet(
    path,
    filters = filtros_particao
)
except:
    print("Sem novas despesas")
    sys.exit()

# Escolhendo as colunas no df final

colunas = ['deputado', 'tipoDespesa', 'codDocumento', 'codTipoDocumento', 'dataDocumento', 'numDocumento', 'nomeFornecedor', 'valorLiquido', 'ano', 'mes']

df_final = df[colunas]

# Tratando coluna de data
df_final['dataDocumento'] = pd.to_datetime(df_final['dataDocumento'])

df_final['dataDocumento'] = df_final['dataDocumento'].dt.date

# Mantém apenas as linhas com valorLiquido maior ou igual a zero
df_final = df_final[df_final['valorLiquido'] >= 0]

# SALVANDO OS DADOS

caminho_salvar = Path(__file__).parent / "Dados" / "Gold" / "gld_deputados_despesas.parquet"

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