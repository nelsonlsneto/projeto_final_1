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
    current_date = current_date + relativedelta(months=1)

############################################################################
# 1) BAIXANDO DADOS DE VOTAÇÕES

# Configurações de Concorrência
MAX_PAGINAS = 100  # Limite de segurança. O script para antes se as páginas acabarem.
CONCORRENCIA_MAXIMA = 5  # Quantidade de requisições simultâneas


async def baixar_pagina(client, pagina, semaphore, pbar):
    """Baixa uma página específica utilizando o intervalo dataInicio e dataFim."""
    # Adicionado o parâmetro &dataFim na URL da API
    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes?dataInicio={data_ini}&dataFim={data_ontem}&itens=100&pagina={pagina}&ordem=DESC&ordenarPor=dataHoraRegistro"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with semaphore:
        try:
            response = await client.get(url, headers=headers, timeout=20.0)
            pbar.update(1)

            if response.status_code == 200:
                dados = response.json().get("dados", [])
                return {"pagina": pagina, "dados": dados}

            print(f"\n[Aviso] Erro HTTP {response.status_code} na página {pagina}")
            return {"pagina": pagina, "dados": []}
        except Exception as e:
            print(f"\n[Erro de Conexão] Página {pagina}: {str(e)}")
            return {"pagina": pagina, "dados": []}


async def main():
    semaphore = asyncio.Semaphore(CONCORRENCIA_MAXIMA)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=CONCORRENCIA_MAXIMA)

    caminho_salvar = Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes.json"
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando busca paralela de votações entre {data_ini} e {data_ontem}...")

    # Dispara a busca em paralelo de todas as páginas potenciais do intervalo
    with tqdm_asyncio(total=MAX_PAGINAS, desc="Páginas Baixadas", unit="pág") as pbar:
        async with httpx.AsyncClient(limits=limits, verify=False) as client:
            tasks = [
                baixar_pagina(client, pag, semaphore, pbar)
                for pag in range(1, MAX_PAGINAS + 1)
            ]
            resultados = await asyncio.gather(*tasks)

    # Reordena para garantir a ordem correta das páginas (1, 2, 3...)
    resultados.sort(key=lambda x: x["pagina"])

    # Consolidação dos dados
    proposicao_final = []
    ids_coletados = set()

    for lote in resultados:
        dados_pagina = lote["dados"]

        # Se a página retornou vazia, significa que os dados do intervalo acabaram ali
        if not dados_pagina:
            break

        # Remove duplicados que possam surgir por oscilação de paginação dinâmica
        for item in dados_pagina:
            if item["id"] not in ids_coletados:
                ids_coletados.add(item["id"])
                proposicao_final.append(item)

    # Salvando os dados no arquivo JSON
    with open(caminho_salvar, "w", encoding="utf-8") as arquivo:
        json.dump(proposicao_final, arquivo, indent=4, ensure_ascii=False)

    print(f"\nSucesso! Arquivo JSON salvo com {len(proposicao_final)} registros únicos do período.")


if __name__ == "__main__":
    asyncio.run(main())

###############################################################################
# 2) BAIXANDO DADOS DE CADA ID DE VOTAÇÃO

path = Path(r".\Dados\Bronze\brz_votacoes.json")

try:
    with open(path, "r", encoding="utf-8") as f:
        dados_json = json.load(f)
except FileNotFoundError:
    print(f"Arquivo não encontrado: {path}")
    sys.exit()

# Extrai os IDs direto para a lista final
try:
    id_proposicao_lista = [item["id"] for item in dados_json]
except KeyError:
    print("O atributo 'id' não existe em algum dos registros do JSON.")
    sys.exit()
except TypeError:
    print("O formato do JSON não é uma lista válida de registros.")
    sys.exit()


async def buscar_autores(client, pid, semaphore):
    url = f'https://dadosabertos.camara.leg.br/api/v2/votacoes/{pid}'
    
    async with semaphore:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = await client.get(url, headers=headers, timeout=15.0)
            if response.status_code == 200:
                return response.json()['dados']
            return None
        except Exception:
            return None


# Função auxiliar para dividir a lista em lotes (chunks)
def dividir_em_lotes(lista, tamanho_lote):
    for i in range(0, len(lista), tamanho_lote):
        yield lista[i : i + tamanho_lote]


async def main():
    # Configurações de alta performance
    semaphore = asyncio.Semaphore(40)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

    tamanho_lote = 500
    lotes = list(dividir_em_lotes(id_proposicao_lista, tamanho_lote))

    caminho_salvar = (
        Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes_detalhes.json"
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

###############################################################################
# 3) BAIXANDO DADOS DE CADA VOTO

async def buscar_autores(client, pid, semaphore):
    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{pid}/votos"

    async with semaphore:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = await client.get(url, headers=headers, timeout=15.0)

            if response.status_code == 200:
                dados_api = response.json().get("dados", [])

                # Só cria a estrutura se houver dados de votos reais
                if dados_api:
                    return {"votacao": pid, "votos": dados_api}

            return None
        except Exception:
            return None


# Função auxiliar para dividir a lista em lotes (chunks)
def dividir_em_lotes(lista, tamanho_lote):
    for i in range(0, len(lista), tamanho_lote):
        yield lista[i : i + tamanho_lote]


async def main():
    # Garantir que a lista global existe antes de rodar
    global id_proposicao_lista
    if "id_proposicao_lista" not in globals() or not id_proposicao_lista:
        print("Erro: A lista 'id_proposicao_lista' não foi definida ou está vazia.")
        return

    # Configurações de alta performance
    semaphore = asyncio.Semaphore(40)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

    tamanho_lote = 500
    lotes = list(dividir_em_lotes(id_proposicao_lista, tamanho_lote))

    caminho_salvar = (
        Path(__file__).parent / "Dados" / "Bronze" / "brz_votacoes_votos.json"
    )
    caminho_salvar.parent.mkdir(parents=True, exist_ok=True)

    # Se o arquivo já existe, carrega os dados anteriores para não sobrescrever
    dados_acumulados = []
    if caminho_salvar.exists():
        try:
            with open(caminho_salvar, "r", encoding="utf-8") as f:
                dados_acumulados = json.load(f)
            print(
                f"Arquivo existente encontrado. {len(dados_acumulados)} registros carregados."
            )
        except Exception:
            print("Arquivo existente corrompido, iniciando um novo.")

    print(
        f"Total de IDs: {len(id_proposicao_lista)} | Divididos em {len(lotes)} lotes de {tamanho_lote}."
    )

    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        for idx, lote in enumerate(lotes, start=1):
            print(
                f"\n--- Processando Lote {idx}/{len(lotes)} ({len(lote)} IDs) ---"
            )

            tasks = [buscar_autores(client, pid, semaphore) for pid in lote]

            # Roda o lote atual em paralelo
            resultados = await tqdm_asyncio.gather(
                *tasks, desc=f"Lote {idx} baixando"
            )

            # Filtra os nulos do lote atual (erros ou votações sem votos)
            dados_lote = [r for r in resultados if r is not None]

            # Adiciona ao acumulador e salva no arquivo imediatamente
            dados_acumulados.extend(dados_lote)

            with open(caminho_salvar, "w", encoding="utf-8") as f:
                json.dump(dados_acumulados, f, indent=4, ensure_ascii=False)

            print(
                f"Lote {idx} salvo com sucesso! Total acumulado: {len(dados_acumulados)} registros."
            )

    print(
        f"\nProcesso concluído! Todos os lotes foram salvos em: {caminho_salvar}"
    )


if __name__ == "__main__":
    asyncio.run(main())