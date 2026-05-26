import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no arquivo .env")

engine = create_engine(DATABASE_URL)


def buscar_ids_deputados() -> list[int]:
    """
    Busca os IDs dos deputados já carregados no Supabase.
    """
    query = "SELECT id FROM deputados ORDER BY id;"

    df = pd.read_sql(query, engine)

    ids = df["id"].dropna().astype(int).tolist()

    if not ids:
        raise ValueError("Nenhum deputado encontrado na tabela deputados. Rode load_deputados_supabase.py primeiro.")

    return ids


def buscar_despesas_deputado(id_deputado: int, ano: int = 2025) -> pd.DataFrame:
    """
    Busca despesas de um deputado específico na API da Câmara.
    """
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id_deputado}/despesas"

    todas_despesas = []
    pagina = 1

    while True:
        params = {
            "ano": ano,
            "pagina": pagina,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "ano",
        }

        try:
            response = requests.get(url, params=params, timeout=60)
        except requests.RequestException as erro:
            print(f"Erro de conexão para deputado {id_deputado}, página {pagina}: {erro}")
            break

        if response.status_code != 200:
            print(f"Erro API deputado {id_deputado}, página {pagina}: {response.status_code}")
            break

        dados = response.json().get("dados", [])

        if not dados:
            break

        todas_despesas.extend(dados)

        print(f"Deputado {id_deputado} | Página {pagina} | Registros {len(dados)}")

        pagina += 1
        time.sleep(0.2)

    if not todas_despesas:
        return pd.DataFrame()

    df = pd.DataFrame(todas_despesas)
    df["deputado_id"] = id_deputado

    return df


def tratar_despesas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza nomes de colunas e tipos de dados para gravar no Supabase.
    """
    if df.empty:
        return df

    df = df.rename(
        columns={
            "tipoDespesa": "tipo_despesa",
            "codDocumento": "cod_documento",
            "tipoDocumento": "tipo_documento",
            "codTipoDocumento": "cod_tipo_documento",
            "dataDocumento": "data_documento",
            "numDocumento": "num_documento",
            "valorDocumento": "valor_documento",
            "urlDocumento": "url_documento",
            "nomeFornecedor": "nome_fornecedor",
            "cnpjCpfFornecedor": "cnpj_cpf_fornecedor",
            "valorLiquido": "valor_liquido",
            "valorGlosa": "valor_glosa",
            "numRessarcimento": "num_ressarcimento",
            "codLote": "cod_lote",
        }
    )

    colunas = [
        "deputado_id",
        "ano",
        "mes",
        "tipo_despesa",
        "cod_documento",
        "tipo_documento",
        "cod_tipo_documento",
        "data_documento",
        "num_documento",
        "url_documento",
        "nome_fornecedor",
        "cnpj_cpf_fornecedor",
        "valor_documento",
        "valor_glosa",
        "valor_liquido",
        "num_ressarcimento",
        "cod_lote",
        "parcela",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    colunas_inteiras = [
    "deputado_id",
    "ano",
    "mes",
    "cod_tipo_documento",
    "parcela",
]

    for coluna in colunas_inteiras:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").astype("Int64")
    
    df["cod_documento"] = df["cod_documento"].astype(str)
    df["cod_lote"] = df["cod_lote"].astype(str)

    colunas_valores = [
        "valor_documento",
        "valor_glosa",
        "valor_liquido",
    ]

    for coluna in colunas_valores:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df["data_documento"] = pd.to_datetime(df["data_documento"], errors="coerce").dt.date

    df = df.drop_duplicates(
        subset=[
            "deputado_id",
            "ano",
            "mes",
            "cod_documento",
            "num_documento",
            "valor_liquido",
        ]
    )

    return df


def carregar_despesas(df: pd.DataFrame) -> None:
    """
    Carrega despesas no Supabase.
    """
    if df.empty:
        print("Nenhuma despesa para carregar.")
        return

    df.to_sql(
        "despesas",
        engine,
        if_exists="append",
        index=False,
    )

    print(f"{len(df)} despesas inseridas no Supabase.")


def main():
    ano = 2025

    ids_deputados = buscar_ids_deputados()

    print(f"Total de deputados encontrados no banco: {len(ids_deputados)}")

    lista_dfs = []

    for id_deputado in ids_deputados:
        df_despesas = buscar_despesas_deputado(id_deputado, ano=ano)

        if not df_despesas.empty:
            lista_dfs.append(df_despesas)

    if not lista_dfs:
        print("Nenhuma despesa encontrada.")
        return

    df_final = pd.concat(lista_dfs, ignore_index=True)

    df_final = tratar_despesas(df_final)

    carregar_despesas(df_final)


if __name__ == "__main__":
    main()