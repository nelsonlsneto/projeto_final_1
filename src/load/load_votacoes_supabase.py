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

ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_votacoes.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS votacoes (
            id TEXT PRIMARY KEY,
            data DATE,
            data_hora_registro TIMESTAMP,
            sigla_orgao TEXT,
            proposicao_objeto TEXT,
            descricao TEXT,
            aprovacao TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """

    with engine.begin() as connection:
        connection.execute(text(sql))


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    df = df.rename(
        columns={
            "dataHoraRegistro": "data_hora_registro",
            "siglaOrgao": "sigla_orgao",
            "proposicaoObjeto": "proposicao_objeto",
        }
    )

    colunas = [
        "id",
        "data",
        "data_hora_registro",
        "sigla_orgao",
        "proposicao_objeto",
        "descricao",
        "aprovacao",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["id"] = df["id"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    df["data_hora_registro"] = pd.to_datetime(df["data_hora_registro"], errors="coerce")
    df["aprovacao"] = df["aprovacao"].astype(str)

    df = df.dropna(subset=["id"])
    df = df.drop_duplicates(subset=["id"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhuma votação para carregar.")
        return

    tabela_temp = "tmp_votacoes"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(
        tabela_temp,
        engine,
        if_exists="replace",
        index=False,
    )

    sql = """
        INSERT INTO votacoes (
            id,
            data,
            data_hora_registro,
            sigla_orgao,
            proposicao_objeto,
            descricao,
            aprovacao
        )
        SELECT
            id,
            data,
            data_hora_registro,
            sigla_orgao,
            proposicao_objeto,
            descricao,
            aprovacao
        FROM tmp_votacoes
        ON CONFLICT (id)
        DO UPDATE SET
            data = EXCLUDED.data,
            data_hora_registro = EXCLUDED.data_hora_registro,
            sigla_orgao = EXCLUDED.sigla_orgao,
            proposicao_objeto = EXCLUDED.proposicao_objeto,
            descricao = EXCLUDED.descricao,
            aprovacao = EXCLUDED.aprovacao;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} votações carregadas/atualizadas no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()