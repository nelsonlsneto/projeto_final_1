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

ARQUIVO_SILVER = BASE_DIR / "Dados" / "Silver" / "slv_votacoes_votos.parquet"


def criar_tabela() -> None:
    sql = """
        CREATE TABLE IF NOT EXISTS votacoes_votos (
            id BIGSERIAL PRIMARY KEY,
            votacao_id TEXT,
            tipo_voto TEXT,
            data_registro_voto TIMESTAMP,
            deputado_id BIGINT,
            deputado_uri TEXT,
            deputado_nome TEXT,
            deputado_sigla_partido TEXT,
            deputado_uri_partido TEXT,
            deputado_sigla_uf TEXT,
            deputado_id_legislatura INTEGER,
            deputado_url_foto TEXT,
            deputado_email TEXT,
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
        row.get("data_registro_voto"),
    ]

    texto = "|".join([str(campo) for campo in campos])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def carregar_arquivo() -> pd.DataFrame:
    if not ARQUIVO_SILVER.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_SILVER}")

    df = pd.read_parquet(ARQUIVO_SILVER)

    df = df.rename(
        columns={
            "votacao": "votacao_id",
            "tipoVoto": "tipo_voto",
            "dataRegistroVoto": "data_registro_voto",
            "deputado_.id": "deputado_id",
            "deputado_.uri": "deputado_uri",
            "deputado_.nome": "deputado_nome",
            "deputado_.siglaPartido": "deputado_sigla_partido",
            "deputado_.uriPartido": "deputado_uri_partido",
            "deputado_.siglaUf": "deputado_sigla_uf",
            "deputado_.idLegislatura": "deputado_id_legislatura",
            "deputado_.urlFoto": "deputado_url_foto",
            "deputado_.email": "deputado_email",
        }
    )

    colunas = [
        "votacao_id",
        "tipo_voto",
        "data_registro_voto",
        "deputado_id",
        "deputado_uri",
        "deputado_nome",
        "deputado_sigla_partido",
        "deputado_uri_partido",
        "deputado_sigla_uf",
        "deputado_id_legislatura",
        "deputado_url_foto",
        "deputado_email",
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None

    df = df[colunas]

    df["data_registro_voto"] = pd.to_datetime(df["data_registro_voto"], errors="coerce")
    df["deputado_id"] = pd.to_numeric(df["deputado_id"], errors="coerce").astype("Int64")
    df["deputado_id_legislatura"] = pd.to_numeric(df["deputado_id_legislatura"], errors="coerce").astype("Int64")

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
        INSERT INTO votacoes_votos (
            votacao_id,
            tipo_voto,
            data_registro_voto,
            deputado_id,
            deputado_uri,
            deputado_nome,
            deputado_sigla_partido,
            deputado_uri_partido,
            deputado_sigla_uf,
            deputado_id_legislatura,
            deputado_url_foto,
            deputado_email,
            hash_registro
        )
        SELECT
            votacao_id,
            tipo_voto,
            data_registro_voto,
            deputado_id,
            deputado_uri,
            deputado_nome,
            deputado_sigla_partido,
            deputado_uri_partido,
            deputado_sigla_uf,
            deputado_id_legislatura,
            deputado_url_foto,
            deputado_email,
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