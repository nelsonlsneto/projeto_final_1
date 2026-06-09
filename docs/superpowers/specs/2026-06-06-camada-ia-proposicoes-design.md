# Design — Camada de IA: Resumos Executivos de Proposições

**Data:** 2026-06-06  
**Responsável:** Raphael Gonçalves de Melo Valente  
**Etapa do projeto:** 4 de 5

---

## Problema

A tabela `fat_proposicoes` no Supabase possui a coluna `ementa`, que contém o texto
jurídico denso de cada proposição. Esse texto não é legível para um executivo corporativo
sem formação jurídica. A coluna `resumo_ia` existe na modelagem mas está vazia — é ela
que alimenta o email semanal do n8n (Etapa 5). Sem o `resumo_ia`, não há produto final.

---

## Objetivo

Criar o script `GLD_IA_Proposicoes.py` que:
1. Lê as proposições do arquivo `Dados/Gold/gld_proposicoes.parquet`
2. Consulta o Supabase para descobrir quais já têm `resumo_ia` (evita reprocessar)
3. Envia a `ementa` de cada proposição pendente para `gpt-4o-mini` via API da OpenAI
4. Recebe um resumo de 3 linhas em linguagem executiva
5. Faz `UPDATE` na tabela `fat_proposicoes` do Supabase com o resumo recebido

---

## Arquitetura

```
Dados/Gold/gld_proposicoes.parquet
            ↓
    Lê DataFrame (pandas)
            ↓
    Consulta Supabase: quais ids já têm resumo_ia?
            ↓
    Filtra apenas pendentes
            ↓
    [MODO_TESTE=True] → limita a 10 linhas
            ↓
    Loop por linha:
        ementa → OpenAI gpt-4o-mini → resumo_ia
        UPDATE fat_proposicoes SET resumo_ia = '...' WHERE id = ...
            ↓
    Relatório final: total processado, tempo, custo estimado
```

---

## Arquivo a criar

**`GLD_IA_Proposicoes.py`** — na raiz do projeto, junto com os demais scripts Gold.

Segue o padrão de nomenclatura do projeto: `[ORIGEM]_[DESTINO]_[ENTIDADE].py`.

---

## Seções do script

### 1. Imports e configuração
```python
import os, time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import psycopg2
```
- `load_dotenv()` carrega `OPENAI_API_KEY` e `DATABASE_URL` do `.env`
- Cliente OpenAI instanciado uma vez (não a cada chamada)
- Conexão PostgreSQL aberta uma vez e fechada no `finally`

### 2. Variável de controle de custo
```python
MODO_TESTE = True   # mude para False para processar tudo
LIMITE_TESTE = 10
```
Quando `True`, processa apenas as primeiras 10 proposições e imprime o custo estimado.
O desenvolvedor valida o custo antes de rodar o lote completo.

### 3. Leitura e filtragem
- Lê `gld_proposicoes.parquet`
- Consulta `SELECT id FROM fat_proposicoes WHERE resumo_ia IS NOT NULL` no Supabase
- Remove do DataFrame os ids já processados → **idempotente**: pode rodar várias vezes sem duplicar trabalho

### 4. Função `resumir_ementa(ementa: str) -> str`
Única responsabilidade: chamar a API e retornar o resumo.
```
model = "gpt-4o-mini"
max_tokens = 200
temperature = 0.3   # respostas mais determinísticas para texto técnico
```

**Prompt:**
```
Você é um analista de inteligência legislativa da consultoria Bússola Pública.
Resuma a proposição abaixo em exatamente 3 linhas,
em linguagem clara para um executivo corporativo.
Seja objetivo. Não use jargão jurídico.

Proposição: {ementa}
```

### 5. Loop principal
```
para cada linha do DataFrame pendente:
    chama resumir_ementa(ementa)
    executa UPDATE no Supabase
    imprime: [atual/total] id=XXXXX ✓
    aguarda 0.5s (respeita rate limit da API)
```

### 6. Relatório final
```
Processadas: 42 proposições
Tempo total: 1m 23s
Custo estimado: ~$0.03 (gpt-4o-mini: ~$0.15/1M tokens de entrada)
```

---

## Dependências novas

Adicionar ao `pyproject.toml`:
```
openai>=1.0.0
psycopg2-binary>=2.9.0
```

Executar `uv sync` (ou `pip install openai psycopg2-binary`) após adicionar.

---

## Variáveis de ambiente necessárias

Já existem no `.env.example`. O desenvolvedor precisa preencher o `.env` local:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://usuario:senha@host:5432/postgres
```

---

## Controle de custo (estimativa)

| Cenário | Proposições | Tokens estimados | Custo |
|---------|-------------|------------------|-------|
| Teste   | 10          | ~2.000           | < $0.01 |
| 30 dias | ~150        | ~30.000          | ~$0.01 |
| Histórico completo | ~1.000 | ~200.000 | ~$0.03 |

`gpt-4o-mini` custa ~$0.15 por 1M tokens de entrada. O custo é baixíssimo.

---

## O que NÃO está no escopo deste script

- Criar ou recriar a tabela `fat_proposicoes` (já existe, feito por outro membro)
- Classificação por embeddings (Caminho A do projeto — optamos pelo Caminho B)
- Integração com n8n (Etapa 5, separada)

---

## Como rodar

```powershell
# Com uv:
uv run GLD_IA_Proposicoes.py

# Com pip:
python GLD_IA_Proposicoes.py
```

Ordem no pipeline completo (README):
```
... (scripts anteriores) ...
uv run GLD_IA_Proposicoes.py   # ← Etapa 4, roda por último
```

---

## Critério de sucesso

- [ ] Script roda sem erros em `MODO_TESTE = True` com 10 proposições
- [ ] Coluna `resumo_ia` preenchida no Supabase (verificável pelo Table Editor)
- [ ] Custo estimado impresso no terminal
- [ ] Script roda em `MODO_TESTE = False` sem duplicar registros já processados
- [ ] `openai` e `psycopg2-binary` adicionados ao `pyproject.toml`
- [ ] Prompt documentado no README
- [ ] Commit com mensagem descritiva no GitHub
