# Radar Legislativo — Inteligência Legislativa Automatizada

> Pipeline de Engenharia de Dados que captura, organiza e enriquece com IA os dados
> abertos da **Câmara dos Deputados**, transformando um oceano de informação pública
> em sinal acionável para clientes corporativos.

Produto de inteligência legislativa da consultoria fictícia **Bússola Pública**,
desenvolvido como **Projeto Integrador** da pós-graduação em Engenharia de Dados e IA.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Pandas](https://img.shields.io/badge/Pandas-3.0-150458)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E)
![OpenAI](https://img.shields.io/badge/IA-OpenAI-412991)
![n8n](https://img.shields.io/badge/Automacao-n8n-EA4B71)

---

## O Problema

Toda semana, **513 deputados** decidem pautas que afetam diretamente empresas e
cidadãos: tributação, regulação de IA, saneamento, reforma trabalhista. Cada voto,
proposição e despesa é **dado público**, atualizado diariamente por uma
[API aberta e gratuita](https://dadosabertos.camara.leg.br/swagger/api.html).

A consultoria fictícia **Bússola Pública** vende inteligência legislativa, mas hoje
depende de analistas lendo o site da Câmara manualmente. Não escala, não tem histórico
organizado e a classificação por tema é inconsistente.

**A solução — Radar Legislativo:** um pipeline automatizado que captura tudo o que
importa, resume com IA e entrega pronto para virar produto.

---

## Arquitetura do Pipeline

O projeto segue a **Arquitetura Medalhão** (Bronze -> Silver -> Gold), padrão de mercado
em engenharia de dados:

```mermaid
flowchart LR
    A[API Camara dos Deputados] -->|requests + paginacao| B[Bronze - JSON bruto]
    B -->|limpeza / json_normalize| C[Silver - Parquet tipado]
    C -->|merges / validacoes| D[Gold - Parquet modelado]
    D -->|OpenAI gpt-4o-mini| E[Enriquecimento IA - coluna resumo_ia]
    E -->|SQLAlchemy| F[(PostgreSQL - Supabase)]
    F -->|query semanal| G[n8n - Email automatico]
```

| Camada | Formato | Responsabilidade |
|--------|---------|------------------|
| **Bronze** | JSON | Dado bruto da API, salvo intacto (não chama a API de novo se o transform quebrar) |
| **Silver** | Parquet | Seleção de colunas, normalização de estruturas aninhadas, tipagem. Guarda as tabelas dimensão. |
| **Gold** | Parquet | Joins entre tabelas, validações de qualidade. Guarda as tabelas fato. |
| **IA** | Parquet | Resumo executivo de cada proposição via LLM |
| **PostgreSQL** | Supabase | Banco final, consultável e pronto para produto |
| **n8n** | Workflow | Automação: email semanal com as proposições mais relevantes |

> A extração puxa, por padrão, os dados de **1 dia** (o orquestrador roda diariamente).
> Cargas históricas (ex.: 30 dias) são feitas manualmente ajustando a data inicial.

> Diagrama detalhado no Excalidraw: _(link a inserir)_

---

## Modelo de Dados

Modelagem dimensional simples (estrela), carregada no PostgreSQL:

**Tabelas Fato (camada Gold)**
- `fat_proposicoes` — `id`, `codigo_tipo_sigla`, `ementa`, `data_apresentacao`, `autor_nome`, **`resumo_ia`** (coluna a ser criada pela camada de IA)
- `fat_votacoes` — `id_votacao`, `data`, `descricao`, `aprovacao`, `id_proposicao`
- `fat_votacoes_votos` — `id_votacao`, `deputado_id`, `tipo_voto`
- `fat_deputados_despesas` — `deputado`, `tipo_despesa`, `data_documento`, `nome_fornecedor`, `valor_liquido`

**Tabelas Dimensão (camada Silver)**
- `dim_deputados` — `id`, `uri`, `nome`, `sigla_partido`, `uri_partido`, `sigla_uf`, `id_legislatura` (513 registros)
- `dim_proposicoes_autoria` — autoria de cada proposição (`proposicao`, `nome`, `codigo_tipo`)
- `dim_votacoes_detalhes` — detalhamento das votações
- `dim_partidos` — `sigla`, `nome` _(a adicionar)_

**Relacionamentos**
- `fat_votacoes_votos.deputado_id` -> `dim_deputados.id`
- `fat_deputados_despesas.deputado` -> `dim_deputados.id`
- `fat_votacoes.id_proposicao` -> `fat_proposicoes.id`
- `dim_proposicoes_autoria.proposicao` -> `fat_proposicoes.id`

---

## Camada de IA

Para cada proposição, a **ementa** (texto jurídico denso) é enviada a um LLM
(`gpt-4o-mini` da OpenAI) que devolve um **resumo executivo de 3 linhas** em linguagem
clara — exatamente o que um cliente corporativo precisa ler em 10 segundos.

O resumo é salvo na coluna `resumo_ia` da tabela `fat_proposicoes` e alimenta
diretamente o email semanal do n8n (a IA agrega valor real ao produto, não é decoração).

**Prompt utilizado:**
```
_(a documentar quando a Etapa 4 for implementada)_
```

> **Controle de custo:** testado primeiro com 10 proposições para medir o custo antes
> de rodar o lote completo.

---

## Automação (n8n)

Workflow agendado que, semanalmente:
1. Consulta o PostgreSQL pelas proposições mais relevantes da semana;
2. Monta um email com título, autor e o `resumo_ia`;
3. Envia automaticamente para o cliente.

> Workflow exportado: `n8n/workflow_email_semanal.json` _(a inserir)_
> Print de execução bem-sucedida: _(a inserir)_

---

## Como Rodar

### Pré-requisitos
- Python 3.12
- [uv](https://docs.astral.sh/uv/) (gerenciador de dependências)
- Conta no [Supabase](https://supabase.com) (PostgreSQL gratuito)
- Chave de API da [OpenAI](https://platform.openai.com)

### Passos
```powershell
# 1. Clonar o repositório
git clone https://github.com/nelsonlsneto/projeto_final_1.git
cd projeto_final_1

# 2. Instalar dependências
uv sync

# 3. Configurar credenciais (copie o exemplo e preencha)
copy .env.example .env
#    Edite o .env com sua connection string do Supabase e sua chave OpenAI

# 4. Rodar o pipeline (na ordem)
uv run API_BRZ_Deputados.py        # Extração -> Bronze
uv run API_BRZ_Proposicoes.py
uv run API_BRZ_Votacoes.py
uv run BRZ_SLV_Deputados.py        # Limpeza -> Silver
# ... (demais scripts BRZ_SLV_)
uv run SLV_GLD_Proposicoes.py      # Modelagem -> Gold
# ... (demais scripts SLV_GLD_)
```

> **Nunca** commite o arquivo `.env`. Ele já está no `.gitignore`.

---

## Estrutura do Repositório

```
projeto_final_1/
├── API_BRZ_*.py        # Extração da API -> Bronze (JSON)
├── BRZ_SLV_*.py        # Limpeza Bronze -> Silver (Parquet)
├── SLV_GLD_*.py        # Modelagem Silver -> Gold (Parquet)
├── Notas API.txt       # Anotações sobre os endpoints da API
├── pyproject.toml      # Dependências (uv)
├── .gitignore
└── README.md
```
_(serão adicionados: camada de IA e workflow n8n)_

---

## Resultados e Demonstração

### Tabelas populadas no PostgreSQL (Supabase)

A base reúne dados reais da Câmara dos Deputados, já tratados e modelados.

**Dimensão de deputados** — os 513 deputados em exercício:

![Tabela dim_deputados](docs/img/dim_deputados.png)

**Autoria das proposições** — quem propôs cada matéria:

![Tabela dim_proposicoes_autoria](docs/img/dim_proposicoes_autoria.png)

**Despesas (cota parlamentar)** — milhares de gastos declarados:

![Tabela fat_deputados_despesas](docs/img/fat_deputados_despesas.png)

**Votações** — as votações ocorridas no período:

![Tabela fat_votacoes](docs/img/fat_votacoes.png)

### Análises de exemplo (consultas SQL)

O banco não é só um depósito de linhas — é **consultável e gera insight**. Alguns exemplos:

**Maiores bancadas da Câmara** — o PL lidera com 97 deputados:

![Top 10 partidos por número de deputados](docs/img/top10_partidos_por_deputados.png)

**Deputados que mais gastaram a cota parlamentar** (com nome, partido e UF):

![Top 10 deputados por total de gastos](docs/img/top10_deputados_gastos.png)

**Tipos de despesa que mais consomem recursos** — divulgação e combustíveis no topo:

![Top 10 tipos de despesa por valor líquido](docs/img/top10_tipo_despesas_valor_liquido.png)

---

## Banco de Dados (acesso para avaliação)

O banco está hospedado no **Supabase** (PostgreSQL gerenciado, região São Paulo) e pode
ser consultado por qualquer cliente SQL usando o usuário **somente-leitura** abaixo
(criado especificamente para avaliação — só faz `SELECT`, não consegue alterar dados):

```
postgresql://avaliador.dxtqisdoimywsdrbdkzh:Radar_Leitura_2026@aws-1-sa-east-1.pooler.supabase.com:5432/postgres
```

| Parâmetro | Valor |
|-----------|-------|
| Host | `aws-1-sa-east-1.pooler.supabase.com` |
| Porta | `5432` (Session pooler / IPv4) |
| Banco | `postgres` |
| Usuário | `avaliador` (somente-leitura) |
| Senha | `Radar_Leitura_2026` |

Exemplo de consulta:

```sql
-- Maiores bancadas da Câmara
select sigla_partido, count(*) as qtd_deputados
from dim_deputados
group by sigla_partido
order by qtd_deputados desc;
```

> As credenciais acima são intencionalmente **somente-leitura** e públicas para fins de
> avaliação. Tentativas de escrita são bloqueadas pelo banco (`permission denied`).

---

## Próximos Passos
- [x] Carga dos dados no PostgreSQL (Supabase)
- [ ] Dimensão `partidos`
- [ ] Camada de IA: resumo executivo das proposições
- [ ] Workflow n8n: email semanal automatizado
- [ ] Dashboard de indicadores (proposições por tema, partido mais ativo)

---

## Autores e Contribuidores
- Alex Macedo Teles Silva — [@AlexMacedo45](https://github.com/AlexMacedo45)
- Gabriel Ferreira Davila — [@Ferreira0826](https://github.com/Ferreira0826)
- Natasha Sugiyama — [@nasugiyama](https://github.com/nasugiyama)
- Nelson L. S. Neto — [@nelsonlsneto](https://github.com/nelsonlsneto)
- Raphael Gonçalves de Melo Valente — [@rgmelovalente](https://github.com/rgmelovalente)

---

_Projeto desenvolvido como Projeto Integrador da Fase 1 da pós-graduação em Engenharia de Dados e IA._
