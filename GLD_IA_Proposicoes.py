import os
import time
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

MODO_TESTE = True   # True = processa só 10 linhas. Mude para False para rodar tudo.
LIMITE_TESTE = 10

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# LEITURA DO PARQUET
# ---------------------------------------------------------------------------

path_parquet = Path(__file__).parent / "Dados" / "Gold" / "gld_proposicoes.parquet"
df = pd.read_parquet(path_parquet)

print(f"Total de proposições no Parquet: {len(df)}")

# ---------------------------------------------------------------------------
# FILTRA APENAS PENDENTES (idempotente — não reprocessa o que já tem resumo)
# ---------------------------------------------------------------------------

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Garante que a coluna resumo_ia existe (idempotente; necessario em banco zerado)
cur.execute("ALTER TABLE fat_proposicoes ADD COLUMN IF NOT EXISTS resumo_ia TEXT;")
conn.commit()

cur.execute("SELECT id FROM fat_proposicoes WHERE resumo_ia IS NOT NULL;")
ids_prontos = {row[0] for row in cur.fetchall()}

df_pendentes = df[~df["id"].isin(ids_prontos)].copy()

print(f"Já processadas: {len(ids_prontos)}")
print(f"Pendentes: {len(df_pendentes)}")

if MODO_TESTE:
    df_pendentes = df_pendentes.head(LIMITE_TESTE)
    print(f"[MODO TESTE] Processando apenas {LIMITE_TESTE} proposições.")

# ---------------------------------------------------------------------------
# FUNÇÃO DE RESUMO
# ---------------------------------------------------------------------------

PROMPT_SISTEMA = (
    "Você é um analista de inteligência legislativa da consultoria Bússola Pública. "
    "Resuma a proposição abaixo em exatamente 3 linhas, "
    "em linguagem clara para um executivo corporativo. "
    "Seja objetivo. Não use jargão jurídico."
)


def resumir_ementa(ementa: str) -> str:
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": f"Proposição: {ementa}"},
        ],
        max_tokens=200,
        temperature=0.3,
    )
    return resposta.choices[0].message.content.strip()

# ---------------------------------------------------------------------------
# LOOP PRINCIPAL
# ---------------------------------------------------------------------------

total = len(df_pendentes)
inicio = time.time()

for i, (_, row) in enumerate(df_pendentes.iterrows(), start=1):
    prop_id = row["id"]
    ementa = row["ementa"]

    # pula ementas vazias/curtas (evita resumo-lixo do tipo "voce nao incluiu a proposicao")
    if ementa is None or len(str(ementa).strip()) < 10:
        print(f"[{i}/{total}] id={prop_id} - ementa vazia, pulando")
        continue

    try:
        resumo = resumir_ementa(str(ementa))
        cur.execute(
            "UPDATE fat_proposicoes SET resumo_ia = %s WHERE id = %s;",
            (resumo, prop_id),
        )
        conn.commit()
        print(f"[{i}/{total}] id={prop_id} ✓")
    except Exception as e:
        print(f"[{i}/{total}] id={prop_id} ERRO: {e}")
        conn.rollback()

    time.sleep(0.5)  # respeita rate limit da API

# ---------------------------------------------------------------------------
# RELATÓRIO FINAL
# ---------------------------------------------------------------------------

cur.close()
conn.close()

tempo = time.time() - inicio
minutos = int(tempo // 60)
segundos = int(tempo % 60)

print(f"\n{'='*50}")
print(f"Processadas: {total} proposições")
print(f"Tempo total: {minutos}m {segundos}s")
print(f"Custo estimado: ~${total * 0.0000003:.4f} (referência: gpt-4o-mini $0.15/1M tokens entrada)")
print(f"{'='*50}")
