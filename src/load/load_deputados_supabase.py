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


def buscar_deputados() -> pd.DataFrame:
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"

    todos_deputados = []
    pagina = 1

    while True:
        params = {
            "itens": 100,
            "pagina": pagina,
            "ordem": "ASC",
            "ordenarPor": "nome",
        }

        response = requests.get(url, params=params, timeout=60)

        print(f"Página {pagina} | Status: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Erro ao buscar deputados: {response.status_code}")

        dados = response.json().get("dados", [])

        if not dados:
            break

        todos_deputados.extend(dados)

        print(f"Registros encontrados na página {pagina}: {len(dados)}")

        pagina += 1
        time.sleep(0.2)

    df = pd.DataFrame(todos_deputados)

    print("Total retornado pela API:", len(df))

    df = df.rename(
        columns={
            "siglaPartido": "sigla_partido",
            "uriPartido": "uri_partido",
            "siglaUf": "sigla_uf",
            "idLegislatura": "id_legislatura",
            "urlFoto": "url_foto",
        }
    )

    colunas = [
        "id",
        "uri",
        "nome",
        "sigla_partido",
        "uri_partido",
        "sigla_uf",
        "id_legislatura",
        "url_foto",
        "email",
    ]

    df = df[colunas]

    df = df.drop_duplicates(subset=["id"])

    return df


def carregar_deputados(df: pd.DataFrame) -> None:
    tabela_temp = "tmp_deputados"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    df.to_sql(
        tabela_temp,
        engine,
        if_exists="replace",
        index=False,
    )

    sql = """
        INSERT INTO deputados (
            id,
            uri,
            nome,
            sigla_partido,
            uri_partido,
            sigla_uf,
            id_legislatura,
            url_foto,
            email
        )
        SELECT
            id,
            uri,
            nome,
            sigla_partido,
            uri_partido,
            sigla_uf,
            id_legislatura,
            url_foto,
            email
        FROM tmp_deputados
        ON CONFLICT (id)
        DO UPDATE SET
            uri = EXCLUDED.uri,
            nome = EXCLUDED.nome,
            sigla_partido = EXCLUDED.sigla_partido,
            uri_partido = EXCLUDED.uri_partido,
            sigla_uf = EXCLUDED.sigla_uf,
            id_legislatura = EXCLUDED.id_legislatura,
            url_foto = EXCLUDED.url_foto,
            email = EXCLUDED.email;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))
        connection.execute(text(f"DROP TABLE IF EXISTS {tabela_temp};"))

    print(f"{len(df)} deputados carregados/atualizados no Supabase.")


def main():
    df = buscar_deputados()
    carregar_deputados(df)


if __name__ == "__main__":
    main()