# Camada de IA — Resumos Executivos de Proposições

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o script `GLD_IA_Proposicoes.py` que lê as proposições do Parquet Gold, gera um resumo executivo de 3 linhas via OpenAI `gpt-4o-mini` para cada ementa, e grava o resultado na coluna `resumo_ia` da tabela `fat_proposicoes` no Supabase.

**Architecture:** Script sequencial seguindo o padrão dos scripts Gold existentes. Lê o Parquet, consulta o banco para filtrar apenas proposições pendentes (idempotente), itera linha a linha chamando a API da OpenAI e faz UPDATE no Supabase. Variável `MODO_TESTE` limita a 10 linhas para controle de custo antes do lote completo.

**Tech Stack:** Python 3.12, `openai>=1.0.0`, `psycopg2-binary>=2.9.0`, `pandas`, `python-dotenv`, PostgreSQL (Supabase).

---

### Task 1: Adicionar dependências ao projeto

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt` (regenerar com uv)

- [ ] **Step 1: Abrir `pyproject.toml` e adicionar as duas novas dependências**

O arquivo atual tem:
```toml
dependencies = [
    "pandas>=3.0.3",
    "pyarrow>=24.0.0",
    "python-dotenv>=1.2.2",
    "requests>=2.34.2",
]
```

Alterar para:
```toml
dependencies = [
    "openai>=1.0.0",
    "pandas>=3.0.3",
    "psycopg2-binary>=2.9.0",
    "pyarrow>=24.0.0",
    "python-dotenv>=1.2.2",
    "requests>=2.34.2",
]
```

- [ ] **Step 2: Instalar e regenerar o requirements.txt**

```powershell
uv sync
uv export --no-hashes --no-emit-project -o requirements.txt
```

Resultado esperado: nenhum erro. Os pacotes `openai` e `psycopg2-binary` aparecem instalados.

- [ ] **Step 3: Verificar instalação**

```powershell
uv run python -c "import openai; import psycopg2; print('OK')"
```

Resultado esperado: `OK`

- [ ] **Step 4: Commit**

```powershell
git add pyproject.toml requirements.txt uv.lock
git commit -m "deps: adiciona openai e psycopg2-binary para camada de IA"
```

---

### Task 2: Verificar e configurar o `.env`

**Files:**
- Modify: `.env` (arquivo local, nunca commitado)

- [ ] **Step 1: Copiar o `.env.example` para `.env` se ainda não existir**

```powershell
copy .env.example .env
```

Se já existir, pule este passo.

- [ ] **Step 2: Abrir o `.env` e preencher as duas variáveis**

```
OPENAI_API_KEY=sk-proj-SUACHAVEAQUI
DATABASE_URL=postgresql://usuario:senha@host:5432/postgres
```

> A `DATABASE_URL` é a connection string do Supabase.
> Pegue em: Supabase → Project Settings → Database → Connection string → URI (Session pooler, porta 5432).
> A `OPENAI_API_KEY` é gerada em: platform.openai.com → API Keys → Create new secret key.

- [ ] **Step 3: Confirmar que o `.env` NÃO está versionado**

```powershell
git status
```

O arquivo `.env` **não deve aparecer** na lista de arquivos modificados/novos. Se aparecer, algo está errado no `.gitignore` — pare e investigue antes de continuar.

---

### Task 3: Criar o script `GLD_IA_Proposicoes.py`

**Files:**
- Create: `GLD_IA_Proposicoes.py`

- [ ] **Step 1: Criar o arquivo com o conteúdo completo**

Criar `GLD_IA_Proposicoes.py` na raiz do projeto com o seguinte conteúdo:

```python
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
```

- [ ] **Step 2: Rodar em modo teste (10 proposições)**

```powershell
uv run GLD_IA_Proposicoes.py
```

Resultado esperado (exemplo):
```
Total de proposições no Parquet: 147
Já processadas: 0
Pendentes: 147
[MODO TESTE] Processando apenas 10 proposições.
[1/10] id=12345 ✓
[2/10] id=12346 ✓
...
[10/10] id=12354 ✓
==================================================
Processadas: 10 proposições
Tempo total: 0m 12s
Custo estimado: ~$0.0000 (referência: gpt-4o-mini $0.15/1M tokens entrada)
==================================================
```

- [ ] **Step 3: Verificar no Supabase que os 10 resumos foram gravados**

Abra o Supabase → Table Editor → `fat_proposicoes`.  
Filtre por `resumo_ia IS NOT NULL`.  
Deve aparecer 10 linhas com o texto do resumo preenchido.

Ou rode o SQL direto no Supabase SQL Editor:
```sql
SELECT id, ementa, resumo_ia
FROM fat_proposicoes
WHERE resumo_ia IS NOT NULL
LIMIT 10;
```

- [ ] **Step 4: Commit**

```powershell
git add GLD_IA_Proposicoes.py
git commit -m "feat: adiciona script de resumo executivo via OpenAI (Etapa 4)"
```

---

### Task 4: Processar o lote completo

- [ ] **Step 1: Mudar `MODO_TESTE` para `False` no script**

Na linha do arquivo `GLD_IA_Proposicoes.py`:
```python
MODO_TESTE = False   # ← era True
```

- [ ] **Step 2: Rodar o script completo**

```powershell
uv run GLD_IA_Proposicoes.py
```

O script vai pular automaticamente as 10 já processadas e processar o restante.  
Resultado esperado: todas as proposições com `resumo_ia IS NOT NULL` no Supabase.

- [ ] **Step 3: Verificar no Supabase**

```sql
SELECT COUNT(*) FROM fat_proposicoes WHERE resumo_ia IS NOT NULL;
-- deve retornar o total de proposições
```

- [ ] **Step 4: Commit**

```powershell
git add GLD_IA_Proposicoes.py
git commit -m "config: habilita processamento completo (MODO_TESTE=False)"
```

---

### Task 5: Atualizar o README com o prompt e instruções de execução

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Localizar a seção "Camada de IA" no README**

A seção atual tem:
```markdown
**Prompt utilizado:**
\```
_(a documentar quando a Etapa 4 for implementada)_
\```
```

Substituir por:
```markdown
**Prompt utilizado:**
\```
Sistema: Você é um analista de inteligência legislativa da consultoria Bússola Pública.
Resuma a proposição abaixo em exatamente 3 linhas,
em linguagem clara para um executivo corporativo.
Seja objetivo. Não use jargão jurídico.

Usuário: Proposição: {ementa}
\```
```

- [ ] **Step 2: Localizar a seção "Como Rodar" no README e adicionar o script da Etapa 4**

Adicionar após os scripts Gold:
```markdown
# --- IA: resumo executivo das proposições (Etapa 4) ---
uv run GLD_IA_Proposicoes.py   # requer OPENAI_API_KEY no .env
```

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs: documenta prompt e execução da camada de IA (Etapa 4)"
```

---

### Task 6: Push para o GitHub

- [ ] **Step 1: Verificar histórico de commits**

```powershell
git log --oneline -5
```

Deve mostrar os 4 commits criados nas tasks anteriores.

- [ ] **Step 2: Push para o repositório remoto**

```powershell
git push origin main
```

> Se o branch principal do grupo for diferente de `main` (ex: `master` ou `develop`), substitua o nome. Se precisar fazer via Pull Request, crie um branch antes: `git checkout -b feat/etapa-4-ia` e abra o PR no GitHub.

- [ ] **Step 3: Confirmar no GitHub**

Abra o repositório no GitHub e confirme que `GLD_IA_Proposicoes.py` aparece na raiz com a mensagem de commit correta.
