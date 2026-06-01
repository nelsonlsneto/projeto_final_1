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

ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_proposicoes.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS proposicoes (
            id BIGINT PRIMARY KEY,
            sigla_tipo TEXT,
            cod_tipo INTEGER,
            numero INTEGER,
            ano INTEGER,
            ementa TEXT,
            data_apresentacao DATE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """
    with engine.begin() as connection:
        connection.execute(text(sql))


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    df = df.rename(columns={
        "siglaTipo": "sigla_tipo",
        "codTipo": "cod_tipo",
        "dataApresentacao": "data_apresentacao",
    })

    colunas = [
        "id",
        "sigla_tipo",
        "cod_tipo",
        "numero",
        "ano",
        "ementa",
        "data_apresentacao",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df["cod_tipo"] = pd.to_numeric(df["cod_tipo"], errors="coerce").astype("Int64")
    df["numero"] = pd.to_numeric(df["numero"], errors="coerce").astype("Int64")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["data_apresentacao"] = pd.to_datetime(df["data_apresentacao"], errors="coerce").dt.date

    df = df.dropna(subset=["id"])
    df = df.drop_duplicates(subset=["id"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhuma proposição para carregar.")
        return

    tabela_temp = "tmp_proposicoes"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(tabela_temp, engine, if_exists="replace", index=False)

    sql = """
        INSERT INTO proposicoes (
            id, sigla_tipo, cod_tipo, numero, ano, ementa, data_apresentacao
        )
        SELECT
            id, sigla_tipo, cod_tipo, numero, ano, ementa, data_apresentacao
        FROM tmp_proposicoes
        ON CONFLICT (id)
        DO UPDATE SET
            sigla_tipo       = EXCLUDED.sigla_tipo,
            cod_tipo         = EXCLUDED.cod_tipo,
            numero           = EXCLUDED.numero,
            ano              = EXCLUDED.ano,
            ementa           = EXCLUDED.ementa,
            data_apresentacao = EXCLUDED.data_apresentacao;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} proposições carregadas/atualizadas no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()