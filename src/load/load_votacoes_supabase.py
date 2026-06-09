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

# Lê do Gold — gerado pelo SLV_GLD_Votacoes.py
ARQUIVO_GOLD = BASE_DIR / "Dados" / "Gold" / "gld_votacoes.parquet"


def criar_tabela() -> None:
    # votacao_id e votacao_descricao removidas — duplicatas do merge
    sql = """
        CREATE TABLE IF NOT EXISTS fat_votacoes (
            id_votacao        TEXT,
            data              DATE,
            proposicao_objeto TEXT,
            descricao         TEXT,
            aprovacao         TEXT,
            votacao_id_orgao  INTEGER,
            origem_lista      TEXT,
            id_proposicao     BIGINT,
            ementa            TEXT,
            hash_registro     TEXT UNIQUE,
            created_at        TIMESTAMP DEFAULT NOW()
        );
    """
    with engine.begin() as connection:
        connection.execute(text(sql))


def gerar_hash(row) -> str:
    campos = [
        row.get("id_votacao"),
        row.get("origem_lista"),
        row.get("id_proposicao"),
    ]
    texto = "|".join([str(c) for c in campos])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_GOLD.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_GOLD}")

    df = pd.read_parquet(ARQUIVO_GOLD)

    # Renomeia a coluna com nome diferente do esperado
    df = df.rename(columns={"votacao_idOrgao": "votacao_id_orgao"})

    # Remove colunas duplicadas do merge:
    #   votacao_id       → idêntica a id_votacao
    #   votacao_descricao → idêntica a descricao
    colunas = [
        "id_votacao",
        "data",
        "proposicao_objeto",
        "descricao",
        "aprovacao",
        "votacao_id_orgao",
        "origem_lista",
        "id_proposicao",
        "ementa",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["data"]            = pd.to_datetime(df["data"], errors="coerce").dt.date
    df["aprovacao"]       = df["aprovacao"].astype(str)
    df["votacao_id_orgao"] = pd.to_numeric(df["votacao_id_orgao"], errors="coerce").astype("Int64")
    df["id_proposicao"]   = pd.to_numeric(df["id_proposicao"],    errors="coerce").astype("Int64")

    df["hash_registro"] = df.apply(gerar_hash, axis=1)
    df = df.drop_duplicates(subset=["hash_registro"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhuma votação para carregar.")
        return

    tabela_temp = "tmp_fat_votacoes"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(tabela_temp, engine, if_exists="replace", index=False)

    sql = """
        INSERT INTO fat_votacoes (
            id_votacao, data, proposicao_objeto, descricao, aprovacao,
            votacao_id_orgao, origem_lista, id_proposicao, ementa, hash_registro
        )
        SELECT
            id_votacao, data, proposicao_objeto, descricao, aprovacao,
            votacao_id_orgao, origem_lista, id_proposicao, ementa, hash_registro
        FROM tmp_fat_votacoes
        ON CONFLICT (hash_registro)
        DO NOTHING;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} registros de votações carregados no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()