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

# Lê do Silver — gerado pelo BRZ_SLV_Partidos.py
ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_partidos.parquet"


def criar_tabela() -> None:
    # 4 colunas que existem no Silver (id, sigla, nome, uri)
    sql = """
        CREATE TABLE IF NOT EXISTS dim_partidos (
            id         BIGINT PRIMARY KEY,
            sigla      TEXT,
            nome       TEXT,
            uri        TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """
    with engine.begin() as connection:
        connection.execute(text(sql))


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    colunas = ["id", "sigla", "nome", "uri"]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["id"])
    df = df.drop_duplicates(subset=["id"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhum partido para carregar.")
        return

    tabela_temp = "tmp_dim_partidos"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(tabela_temp, engine, if_exists="replace", index=False)

    sql = """
        INSERT INTO dim_partidos (id, sigla, nome, uri)
        SELECT                    id, sigla, nome, uri
        FROM tmp_dim_partidos
        ON CONFLICT (id)
        DO UPDATE SET
            sigla = EXCLUDED.sigla,
            nome  = EXCLUDED.nome,
            uri   = EXCLUDED.uri;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} partidos carregados/atualizados no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()