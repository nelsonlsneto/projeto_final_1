import hashlib
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no arquivo .env")

engine = create_engine(DATABASE_URL)

# Lê do Gold — gerado pelo SLV_GLD_Deputados_Despesas.py
# 8 colunas: deputado, tipoDespesa, codDocumento, codTipoDocumento,
#            dataDocumento, numDocumento, nomeFornecedor, valorLiquido
ARQUIVO_GOLD = BASE_DIR / "Dados" / "Gold" / "gld_deputados_despesas.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS fat_deputados_despesas (
            id               BIGSERIAL PRIMARY KEY,
            deputado         BIGINT,
            tipo_despesa     TEXT,
            cod_documento    TEXT,
            cod_tipo_documento INTEGER,
            data_documento   DATE,
            num_documento    TEXT,
            nome_fornecedor  TEXT,
            valor_liquido    NUMERIC,
            hash_registro    TEXT UNIQUE,
            created_at       TIMESTAMP DEFAULT NOW()
        );
    """
    with engine.begin() as connection:
        connection.execute(text(sql))


def gerar_hash(row) -> str:
    campos = [
        row.get("deputado"),
        row.get("cod_documento"),
        row.get("num_documento"),
        row.get("valor_liquido"),
    ]
    texto = "|".join([str(c) for c in campos])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_GOLD.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_GOLD}")

    df = pd.read_parquet(ARQUIVO_GOLD)

    df = df.rename(columns={
        "tipoDespesa":     "tipo_despesa",
        "codDocumento":    "cod_documento",
        "codTipoDocumento": "cod_tipo_documento",
        "dataDocumento":   "data_documento",
        "numDocumento":    "num_documento",
        "nomeFornecedor":  "nome_fornecedor",
        "valorLiquido":    "valor_liquido",
    })

    colunas = [
        "deputado",
        "tipo_despesa",
        "cod_documento",
        "cod_tipo_documento",
        "data_documento",
        "num_documento",
        "nome_fornecedor",
        "valor_liquido",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["deputado"]          = pd.to_numeric(df["deputado"],          errors="coerce").astype("Int64")
    df["cod_tipo_documento"] = pd.to_numeric(df["cod_tipo_documento"], errors="coerce").astype("Int64")
    df["valor_liquido"]     = pd.to_numeric(df["valor_liquido"],     errors="coerce")
    df["data_documento"]    = pd.to_datetime(df["data_documento"],   errors="coerce").dt.date
    df["cod_documento"]     = df["cod_documento"].astype(str)
    df["num_documento"]     = df["num_documento"].astype(str)

    df["hash_registro"] = df.apply(gerar_hash, axis=1)
    df = df.drop_duplicates(subset=["hash_registro"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhuma despesa para carregar.")
        return

    tabela_temp = "tmp_fat_deputados_despesas"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(tabela_temp, engine, if_exists="replace", index=False)

    sql = """
        INSERT INTO fat_deputados_despesas (
            deputado, tipo_despesa, cod_documento, cod_tipo_documento,
            data_documento, num_documento, nome_fornecedor,
            valor_liquido, hash_registro
        )
        SELECT
            deputado, tipo_despesa, cod_documento, cod_tipo_documento,
            data_documento, num_documento, nome_fornecedor,
            valor_liquido, hash_registro
        FROM tmp_fat_deputados_despesas
        ON CONFLICT (hash_registro)
        DO NOTHING;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} despesas carregadas no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()