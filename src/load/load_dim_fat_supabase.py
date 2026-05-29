import os
import re
from pathlib import Path
import hashlib

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL não encontrada no arquivo .env")

engine = create_engine(DATABASE_URL)


def camel_to_snake(nome_coluna: str) -> str:
    """
    Converte nomes de colunas de camelCase/PascalCase para snake_case.
    Ex:
    siglaPartido -> sigla_partido
    dataHoraRegistro -> data_hora_registro
    urlFoto -> url_foto
    """
    nome_coluna = nome_coluna.strip()
    nome_coluna = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", nome_coluna)
    nome_coluna = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", nome_coluna)
    nome_coluna = nome_coluna.replace(" ", "_").replace("-", "_")
    return nome_coluna.lower()


def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = [camel_to_snake(coluna) for coluna in df.columns]

    renomear = {
        "siglauf": "sigla_uf",
        "siglapartido": "sigla_partido",
        "urlfoto": "url_foto",
        "idlegislatura": "id_legislatura",
        "codtipo": "cod_tipo",
        "siglatipo": "sigla_tipo",
        "dataapresentacao": "data_apresentacao",
        "datahoraregistro": "data_hora_registro",
        "siglaorgao": "sigla_orgao",
        "proposicaoobjeto": "proposicao_objeto",
        "tipovoto": "tipo_voto",
        "idvotacao": "votacao_id",
        "iddeputado": "deputado_id",
        "nomedeputado": "nome_deputado",
        "tipodespesa": "tipo_despesa",
        "coddocumento": "cod_documento",
        "codtipodocumento": "cod_tipo_documento",
        "datadocumento": "data_documento",
        "numdocumento": "num_documento",
        "nomefornecedor": "nome_fornecedor",
        "valorliquido": "valor_liquido",
    }

    df = df.rename(columns=renomear)

    return df


def ajustar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    colunas_data = [
        "data",
        "data_apresentacao",
        "data_hora_registro",
        "data_documento",
    ]

    for coluna in colunas_data:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

            if coluna in ["data", "data_documento"]:
                df[coluna] = df[coluna].dt.date

    colunas_numericas = [
        "id",
        "numero",
        "ano",
        "mes",
        "cod_tipo",
        "cod_tipo_documento",
        "id_legislatura",
        "deputado_id",
        "proposicao_id",
        "ordem_assinatura",
        "proponente",
    ]

    for coluna in colunas_numericas:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    if "valor_liquido" in df.columns:
        df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce")

    if "cod_documento" in df.columns:
        df["cod_documento"] = df["cod_documento"].astype(str)

    if "num_documento" in df.columns:
        df["num_documento"] = df["num_documento"].astype(str)

    if "aprovacao" in df.columns:
        df["aprovacao"] = df["aprovacao"].map({
            1: True,
            1.0: True,
            "1": True,
            "1.0": True,
            0: False,
            0.0: False,
            "0": False,
            "0.0": False,
            True: True,
            False: False,
            "true": True,
            "false": False,
            "True": True,
            "False": False,
        })

    return df

def gerar_id_votacao(row) -> str:
    """
    Gera um ID artificial para votações quando o campo id vem nulo.
    Usa campos da própria linha para criar um identificador estável.
    """
    texto_base = (
        f"{row.get('data', '')}|"
        f"{row.get('data_hora_registro', '')}|"
        f"{row.get('sigla_orgao', '')}|"
        f"{row.get('descricao', '')}"
    )

    return hashlib.md5(texto_base.encode("utf-8")).hexdigest()


def filtrar_colunas_por_tabela(df: pd.DataFrame, tabela_destino: str) -> pd.DataFrame:
    """
    Mantém apenas as colunas esperadas em cada tabela.
    Isso evita erro quando o parquet tem colunas extras.
    """

    colunas_por_tabela = {
        "dim_deputados": [
            "id",
            "nome",
            "sigla_partido",
            "sigla_uf",
            "url_foto",
        ],
        "dim_proposicoes": [
            "id",
            "uri",
            "sigla_tipo",
            "cod_tipo",
            "numero",
            "ano",
            "ementa",
            "data_apresentacao",
        ],
        "dim_proposicoes_autoria": [
            "proposicao_id",
            "nome",
            "tipo",
            "cod_tipo",
            "ordem_assinatura",
            "proponente",
        ],
        "dim_votacoes": [
            "id",
            "data",
            "data_hora_registro",
            "sigla_orgao",
            "proposicao_objeto",
            "descricao",
            "aprovacao",
        ],
        "dim_votacoes_detalhes": [
            "votacao_id",
            "descricao",
            "sigla_orgao",
            "data_hora_registro",
            "proposicao_objeto",
        ],
        "dim_votacoes_votos": [
            "votacao_id",
            "deputado_id",
            "nome_deputado",
            "sigla_partido",
            "sigla_uf",
            "tipo_voto",
        ],
        "fat_deputados_despesas": [
            "deputado",
            "tipo_despesa",
            "cod_documento",
            "cod_tipo_documento",
            "data_documento",
            "num_documento",
            "nome_fornecedor",
            "valor_liquido",
        ],
        "fat_proposicoes": [
            "id",
            "codigo_tipo_sigla",
            "ementa",
            "data_apresentacao",
            "nome",
            "codigo_tipo",
        ],
        "fat_votacoes": [
            "id_votacao",
            "data",
            "data_hora_registro",
            "sigla_orgao",
            "descricao",
            "aprovacao",
        ],
        "fat_votacoes_votos": [
            "id_votacao",
            "deputado_id",
            "nome_deputado",
            "sigla_partido",
            "sigla_uf",
            "tipo_voto",
        ],
    }

    colunas_esperadas = colunas_por_tabela.get(tabela_destino)

    if not colunas_esperadas:
        return df

    for coluna in colunas_esperadas:
        if coluna not in df.columns:
            df[coluna] = None

    return df[colunas_esperadas]


def carregar_parquet_para_supabase(caminho_arquivo: Path, tabela_destino: str):
    if not caminho_arquivo.exists():
        print(f"Arquivo não encontrado: {caminho_arquivo}")
        return

    df = pd.read_parquet(caminho_arquivo)

    print(f"\nCarregando {caminho_arquivo.name}")
    print(f"Tabela destino: {tabela_destino}")
    print(f"Registros: {len(df)}")
    print(f"Colunas originais: {df.columns.tolist()}")

    df = padronizar_colunas(df)

    print(f"Colunas padronizadas: {df.columns.tolist()}")

    df = ajustar_tipos(df)
    df = filtrar_colunas_por_tabela(df, tabela_destino)

    if tabela_destino == "fat_proposicoes":
        if "id" in df.columns:
            df = df.rename(columns={"id": "id_proposicao"})

    # Se a tabela for dim_votacoes e o id estiver vazio, gera um id artificial
    if tabela_destino == "dim_votacoes":
        if "id" not in df.columns:
            df["id"] = None

        df["id"] = df["id"].apply(
            lambda valor: None if pd.isna(valor) or valor == "" else valor
        )

        linhas_sem_id = df["id"].isna()

        df.loc[linhas_sem_id, "id"] = df[linhas_sem_id].apply(
            gerar_id_votacao,
            axis=1
        )

    df = df.drop_duplicates()

    print(f"Colunas finais enviadas: {df.columns.tolist()}")
    print(f"Registros finais: {len(df)}")

    # Limpa a tabela antes de carregar novamente
    with engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {tabela_destino} RESTART IDENTITY CASCADE;")
        )

    # Carrega os dados no Supabase
    df.to_sql(
        tabela_destino,
        engine,
        if_exists="append",
        index=False,
        method="multi",
    )

    print(f"{len(df)} registros inseridos em {tabela_destino}.")


def main():
    arquivos = [
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_deputados.parquet",
            "tabela": "dim_deputados",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_proposicoes.parquet",
            "tabela": "dim_proposicoes",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_proposicoes_autoria.parquet",
            "tabela": "dim_proposicoes_autoria",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_votacoes.parquet",
            "tabela": "dim_votacoes",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_votacoes_detalhes.parquet",
            "tabela": "dim_votacoes_detalhes",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Silver" / "slv_votacoes_votos.parquet",
            "tabela": "dim_votacoes_votos",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Gold" / "gld_deputados_despesas.parquet",
            "tabela": "fat_deputados_despesas",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Gold" / "gld_proposicoes.parquet",
            "tabela": "fat_proposicoes",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Gold" / "gld_votacoes.parquet",
            "tabela": "fat_votacoes",
        },
        {
            "arquivo": BASE_DIR / "Dados" / "Gold" / "gld_votacoes_votos.parquet",
            "tabela": "fat_votacoes_votos",
        },
    ]

    for item in arquivos:
        carregar_parquet_para_supabase(
            caminho_arquivo=item["arquivo"],
            tabela_destino=item["tabela"],
        )


if __name__ == "__main__":
    main()