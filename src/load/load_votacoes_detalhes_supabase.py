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

ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_votacoes_detalhes.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS dim_votacoes_detalhes (
            id BIGSERIAL PRIMARY KEY,
            votacao_id TEXT,
            votacao_data DATE,
            votacao_sigla_orgao TEXT,
            votacao_id_orgao INTEGER,
            votacao_id_evento INTEGER,
            votacao_descricao TEXT,
            votacao_aprovacao TEXT,
            votacao_desc_ultima_abertura_votacao TEXT,
            origem_lista TEXT,
            proposicao_id BIGINT,
            sigla_tipo TEXT,
            numero INTEGER,
            ano INTEGER,
            ementa TEXT,
            hash_registro TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """

    with engine.begin() as connection:
        connection.execute(text(sql))


def gerar_hash(row) -> str:
    campos = [
        row.get("votacao_id"),
        row.get("origem_lista"),
        row.get("proposicao_id"),
        row.get("sigla_tipo"),
        row.get("numero"),
        row.get("ano"),
        row.get("ementa"),
    ]

    texto = "|".join([str(campo) for campo in campos])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    df = df.rename(
        columns={
            "votacao_data": "votacao_data",
            "votacao_siglaOrgao": "votacao_sigla_orgao",
            "votacao_idOrgao": "votacao_id_orgao",
            "votacao_idEvento": "votacao_id_evento",
            "votacao_descricao": "votacao_descricao",
            "votacao_aprovacao": "votacao_aprovacao",
            "votacao_descUltimaAberturaVotacao": "votacao_desc_ultima_abertura_votacao",
            "id": "proposicao_id",
            "siglaTipo": "sigla_tipo",
        }
    )

    colunas = [
        "votacao_id",
        "votacao_data",
        "votacao_sigla_orgao",
        "votacao_id_orgao",
        "votacao_id_evento",
        "votacao_descricao",
        "votacao_aprovacao",
        "votacao_desc_ultima_abertura_votacao",
        "origem_lista",
        "proposicao_id",
        "sigla_tipo",
        "numero",
        "ano",
        "ementa",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["votacao_data"] = pd.to_datetime(df["votacao_data"], errors="coerce").dt.date
    df["votacao_id_orgao"] = pd.to_numeric(df["votacao_id_orgao"], errors="coerce").astype("Int64")
    df["votacao_id_evento"] = pd.to_numeric(df["votacao_id_evento"], errors="coerce").astype("Int64")
    df["proposicao_id"] = pd.to_numeric(df["proposicao_id"], errors="coerce").astype("Int64")
    df["numero"] = pd.to_numeric(df["numero"], errors="coerce").astype("Int64")
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["votacao_aprovacao"] = df["votacao_aprovacao"].astype(str)

    df["hash_registro"] = df.apply(gerar_hash, axis=1)

    df = df.drop_duplicates(subset=["hash_registro"])

    return df


def carregar_supabase(df: pd.DataFrame) -> None:
    if df.empty:
        print("Nenhum detalhe de votação para carregar.")
        return

    tabela_temp = "tmp_votacoes_detalhes"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(
        tabela_temp,
        engine,
        if_exists="replace",
        index=False,
    )

    sql = """
        INSERT INTO dim_votacoes_detalhes (
            votacao_id,
            votacao_data,
            votacao_sigla_orgao,
            votacao_id_orgao,
            votacao_id_evento,
            votacao_descricao,
            votacao_aprovacao,
            votacao_desc_ultima_abertura_votacao,
            origem_lista,
            proposicao_id,
            sigla_tipo,
            numero,
            ano,
            ementa,
            hash_registro
        )
        SELECT
            votacao_id,
            votacao_data,
            votacao_sigla_orgao,
            votacao_id_orgao,
            votacao_id_evento,
            votacao_descricao,
            votacao_aprovacao,
            votacao_desc_ultima_abertura_votacao,
            origem_lista,
            proposicao_id,
            sigla_tipo,
            numero,
            ano,
            ementa,
            hash_registro
        FROM tmp_votacoes_detalhes
        ON CONFLICT (hash_registro)
        DO NOTHING;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} detalhes de votações processados no Supabase.")


def main():
    criar_tabela()
    df = carregar_arquivo()
    carregar_supabase(df)


if __name__ == "__main__":
    main()