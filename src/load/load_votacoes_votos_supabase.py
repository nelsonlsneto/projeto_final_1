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

ARQUIVO_GOLD = BASE_DIR / "Dados" / "Gold" / "gld_votacoes_votos.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS fat_votacoes_votos (
            id BIGSERIAL PRIMARY KEY,
            votacao_id TEXT,
            tipo_voto TEXT,
            deputado_id BIGINT,
            hash_registro TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """

    with engine.begin() as connection:
        connection.execute(text(sql))


def gerar_hash(row) -> str:
    campos = [
        row.get("votacao_id"),
        row.get("deputado_id"),
        row.get("tipo_voto"),
    ]

    texto = "|".join([str(campo) for campo in campos])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_GOLD.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_GOLD}")

    df = pd.read_parquet(ARQUIVO_GOLD)

    colunas = [
        "id_votacao",
        "tipo_voto",
        "deputado_id",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df = df.rename(columns={"id_votacao": "votacao_id"})

    df["deputado_id"] = pd.to_numeric(df["deputado_id"], errors="coerce").astype("Int64")

    df["hash_registro"] = df.apply(gerar_hash, axis=1)

    df = df.drop_duplicates(subset=["hash_registro"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhum voto para carregar.")
        return

    tabela_temp = "tmp_votacoes_votos"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(
        tabela_temp,
        engine,
        if_exists="replace",
        index=False,
    )

    sql = """
        INSERT INTO fat_votacoes_votos (
            votacao_id,
            tipo_voto,
            deputado_id,
            hash_registro
        )
        SELECT
            votacao_id,
            tipo_voto,
            deputado_id,
            hash_registro
        FROM tmp_votacoes_votos
        ON CONFLICT (hash_registro)
        DO NOTHING;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} votos processados no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()