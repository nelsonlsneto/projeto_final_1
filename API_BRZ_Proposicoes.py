# IMPORTS

import requests
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import sys
import asyncio
import httpx
from tqdm.asyncio import tqdm_asyncio

# PARÂMETROS

############################################################################
# Podemos alterar manualmente a data inicial para pegar dados históricos (formato YYYY-MM-DD)

data_ini = ''
data_ontem = ''

############################################################################

if data_ini == '':
    data_ini = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

if data_ontem == '':
    data_ontem = (datetime.now() - relativedelta(days=1)).strftime("%Y-%m-%d")

start_date = datetime.strptime(data_ini, "%Y-%m-%d")
end_date = datetime.strptime(data_ontem, "%Y-%m-%d")

dates = []
current_date = start_date

while current_date <= end_date:
    dates.append(current_date)
    current_date = current_date + relativedelta(days=1)

############################################################################
# 1) BAIXANDO DADOS DE PROPOSIÇÕES

async def baixar_pagina_data(client, date_str, pagina, semaphore):
    """Baixa uma página específica de uma data."""
    url = (
        f"https://dadosabertos.camara.leg.br/api/v2/proposicoes?dataApresentacaoInicio={date_str}&dataApresentacaoFim={date_str}&ordem=ASC&ordenarPor=id&pagina={pagina}&itens=100"
    )

    async with semaphore:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # Adicionado 'verify=False' temporariamente caso seu ambiente tenha bloqueio de SSL (comum em redes corporativas/governamentais)
            response = await client.get(url, headers=headers, timeout=20.0)

            if response.status_code == 200:
                dados = response.json().get("dados", [])
                return dados
            
            print(f"\n[Aviso] Erro HTTP {response.status_code} na data {date_str}, pág {pagina}")
            return None
        except Exception as e:
            # Exibe o erro real caso a requisição esteja caindo por timeout ou rede
            print(f"\n[Erro de Conexão] {date_str} pág {pagina}: {str(e)}")
            return None


async def processar_data_completa(client, date, semaphore, pbar):
    """Baixa todas as páginas de uma única data sequencialmente."""
    date_str = date.strftime("%Y-%m-%d")
    proposicoes_data = []

    for pagina in range(1, 101):
        dados_pagina = await baixar_pagina_data(client, date_str, pagina, semaphore)

        # Se retornar uma lista vazia ou None, as páginas deste dia acabaram
        if not dados_pagina:
            break

        proposicoes_data.append(dados_pagina)
        
        # Atualiza a barra de progresso global a cada página baixada com sucesso
        pbar.update(1)

        # Pausa leve para respeitar a API
        await asyncio.sleep(0.05)

    return proposicoes_data


async def main():
    # Semáforos mais conservadores para evitar que o servidor rejeite a conexão de início
    semaphore = asyncio.Semaphore(10)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=15)

    caminho_salvar = (
        Path(__file__).parent / "Dados" / "Bronze" / "brz_proposicoes.json"
    )
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando requisições assíncronas para {len(dates)} datas...")

    # Criamos uma barra de progresso manual baseada em páginas estimadas
    with tqdm_asyncio(desc="Páginas processadas", unit="pág") as pbar:
        # Desabilitamos a verificação SSL rígida se o httpx travar por certificados locais do ambiente
        async with httpx.AsyncClient(limits=limits, verify=False) as client:
            
            # Passamos o objeto da barra de progresso (pbar) para dentro das funções
            tasks = [processar_data_completa(client, dt, semaphore, pbar) for dt in dates]

            resultados = await asyncio.gather(*tasks)

            proposicao_final = []
            for lote_data in resultados:
                if lote_data:
                    proposicao_final.extend(lote_data)

    # Salvando os dados
    with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
        json.dump(proposicao_final, arquivo, indent=4, ensure_ascii=False)

    print(f"\nSucesso! Arquivo JSON salvo em: {caminho_salvar}")


if __name__ == "__main__":
    asyncio.run(main())

###############################################################################
# 2) BAIXANDO DADOS DE AUTORIA DE CADA PROPOSIÇÃO

path = Path(r".\Dados\Bronze\brz_proposicoes.json")

try:
    with open(path, "r", encoding="utf-8") as f:
        dados_json = json.load(f)
except FileNotFoundError:
    print(f"Arquivo não encontrado: {path}")
    sys.exit()

lista_achatada = [item for sublista in dados_json for item in sublista]

try:
    df = pd.DataFrame(lista_achatada)
    id_proposicao_lista = df["id"].tolist()
except KeyError:
    print("Coluna 'id' não encontrada no JSON.")
    sys.exit()
except Exception:
    print("Sem novas proposições ou erro ao criar DataFrame")
    sys.exit()


async def buscar_autores(client, pid, semaphore):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{pid}/autores"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 3 tentativas por ID antes de desistir
    tentativas = 3
    tempo_espera = 2 

    async with semaphore:
        for tentativa in range(tentativas):
            try:
                response = await client.get(url, headers=headers, timeout=15.0)

                # Se sofrer rate limit (429) ou erro de servidor (5xx), espera e tenta de novo
                if response.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(tempo_espera * (tentativa + 1))
                    continue

                if response.status_code == 200:
                    dados_api = response.json().get("dados", [])
                    # Retorna mesmo vazio para você saber que a requisição teve sucesso
                    return {"proposicao": pid, "autoria": dados_api, "sucesso": True}
                
                # Outros status de erro (ex: 404) que não valem a pena tentar de novo
                return {"proposicao": pid, "autoria": [], "sucesso": False, "erro": response.status_code}

            except (httpx.RequestError, httpx.TimeoutException) as e:
                if tentativa == tentativas - 1:
                    # Registra que o ID falhou após todas as tentativas
                    return {"proposicao": pid, "autoria": [], "sucesso": False, "erro": str(e)}
                await asyncio.sleep(tempo_espera * (tentativa + 1))
                
        return {"proposicao": pid, "autoria": [], "sucesso": False, "erro": "Max retries reached"}


# Função auxiliar para dividir a lista em lotes (chunks)
def dividir_em_lotes(lista, tamanho_lote):
    for i in range(0, len(lista), tamanho_lote):
        yield lista[i : i + tamanho_lote]


async def main():
    # Configurações de alta performance
    semaphore = asyncio.Semaphore(20)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=30)

    tamanho_lote = 500
    lotes = list(dividir_em_lotes(id_proposicao_lista, tamanho_lote))

    caminho_salvar = (
        Path(__file__).parent / "Dados" / "Bronze" / "brz_proposicoes_autoria.json"
    )
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    # Se o arquivo já existe, carrega os dados anteriores para não sobrescrever
    dados_acumulados = []
    if caminho_salvar.exists():
        try:
            with open(caminho_salvar, "r", encoding="utf-8") as f:
                dados_acumulados = json.load(f)
            print(f"Arquivo existente encontrado. {len(dados_acumulados)} registros carregados.")
        except Exception:
            print("Arquivo existente corrompido, iniciando um novo.")

    print(f"Total de IDs: {len(id_proposicao_lista)} | Divididos em {len(lotes)} lotes de {tamanho_lote}.")

    async with httpx.AsyncClient(limits=limits) as client:
        for idx, lote in enumerate(lotes, start=1):
            print(f"\n--- Processando Lote {idx}/{len(lotes)} ({len(lote)} IDs) ---")

            tasks = [buscar_autores(client, pid, semaphore) for pid in lote]

            # Roda o lote atual em paralelo
            resultados = await tqdm_asyncio.gather(
                *tasks, desc=f"Lote {idx} baixando"
            )

            # Filtra os nulos do lote atual
            dados_lote = [r for r in resultados if r is not None]

            # Adiciona ao acumulador e salva no arquivo imediatamente
            dados_acumulados.extend(dados_lote)

            with open(caminho_salvar, "w", encoding="utf-8") as f:
                json.dump(dados_acumulados, f, indent=4, ensure_ascii=False)

            print(f"Lote {idx} salvo com sucesso! Total acumulado: {len(dados_acumulados)} registros.")

    print(f"\nProcesso concluído! Todos os lotes foram salvos em: {caminho_salvar}")


if __name__ == "__main__":
    asyncio.run(main())