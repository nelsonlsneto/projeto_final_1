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

path = Path(r".\Dados\Bronze\brz_votacoes_detalhes.json")

# 1. Carrega o arquivo JSON
try:
    with open(path, "r", encoding="utf-8") as f:
        dados_brutos = json.load(f)
except:
    print("Sem novas votações")
    sys.exit()

# Metadados que queremos repetir da votação principal
metadados = ["id", "data", "siglaOrgao", "idOrgao", "idEvento", "descricao", "aprovacao", "descUltimaAberturaVotacao"]

# 2. Explode a lista 'objetosPossiveis'
df_objetos = pd.json_normalize(
    dados_brutos,
    record_path=["objetosPossiveis"],
    meta=metadados,
    meta_prefix="votacao_",
)
df_objetos["origem_lista"] = "objetosPossiveis"  # Identificador da origem

# 3. Explode a lista 'proposicoesAfetadas'
df_afetadas = pd.json_normalize(
    dados_brutos,
    record_path=["proposicoesAfetadas"],
    meta=metadados,
    meta_prefix="votacao_",
)
df_afetadas["origem_lista"] = "proposicoesAfetadas"  # Identificador da origem

# 4. Junta os dois DataFrames verticalmente (empilhando as linhas)
df_junto = pd.concat([df_objetos, df_afetadas], ignore_index=True)

# Reorganiza as colunas colocando os dados da votação na frente
colunas_ordenadas = ["votacao_id", "votacao_data", "votacao_siglaOrgao", "votacao_idOrgao", "votacao_idEvento", "votacao_descricao", "votacao_aprovacao", "votacao_descUltimaAberturaVotacao", "origem_lista", "id", "siglaTipo", "numero", "ano", "ementa"]

df_final = df_junto[colunas_ordenadas]

# Salvando os dados

caminho_salvar = Path(__file__).parent / "Dados" / "Silver" / "slv_votacoes_detalhes.parquet"

# 1) Cria a pasta se ela não existir
caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

# 2) Identifica quais combinações de ano e mês existem no DataFrame atual
particoes_alvo = df_final['votacao_data'].astype(str).drop_duplicates().tolist()

# 3) Deleta manualmente apenas as pastas que serão impactadas
for data in particoes_alvo:
    # Garante a conversão para string no formato YYYY-MM-DD se for do tipo date/datetime
    data_str = str(data) 
    pasta_particao = caminho_salvar / f"votacao_data={data_str}"
    print(pasta_particao)
    
    if pasta_particao.exists():
        shutil.rmtree(pasta_particao)

# 4) Salvando
## Vamos particionar por ano/mês, pois a requisição apenas recebe parâmetro de ano e mês
df_final.to_parquet(
    path = caminho_salvar,
    partition_cols = ['votacao_data'],
    engine='pyarrow'
)

print(f"Sucesso! Arquivo parquet salvo em: {caminho_salvar}")