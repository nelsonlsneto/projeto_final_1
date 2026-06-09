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

ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS dim_proposicoes_autoria (
            id               BIGSERIAL PRIMARY KEY,
            proposicao_id    BIGINT,
            nome             TEXT,
            cod_tipo         INTEGER,
            tipo             TEXT,
            ordem_assinatura INTEGER,
            proponente       BOOLEAN,
            created_at       TIMESTAMP DEFAULT NOW()
        );
    """
    with engine.begin() as connection:
        connection.execute(text(sql))


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    df = df.rename(columns={
        "codTipo":         "cod_tipo",
        "ordemAssinatura": "ordem_assinatura",
    })

    colunas = [
        "proposicao_id",
        "nome",
        "cod_tipo",
        "tipo",
        "ordem_assinatura",
        "proponente",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["proposicao_id"]    = pd.to_numeric(df["proposicao_id"],    errors="coerce").astype("Int64")
    df["cod_tipo"]         = pd.to_numeric(df["cod_tipo"],         errors="coerce").astype("Int64")
    df["ordem_assinatura"] = pd.to_numeric(df["ordem_assinatura"], errors="coerce").astype("Int64")

    # Converte inteiro (0/1) para boolean — necessário para o PostgreSQL aceitar
    df["proponente"] = df["proponente"].astype(bool)

    df = df.drop_duplicates()

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhuma autoria de proposição para carregar.")
        return

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE dim_proposicoes_autoria RESTART IDENTITY;"))

    df.to_sql(
        "dim_proposicoes_autoria",
        engine,
        if_exists="append",
        index=False,
    )

    print(f"{len(df)} registros de autoria carregados no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()