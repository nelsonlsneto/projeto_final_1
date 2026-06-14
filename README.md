# Radar Legislativo - Inteligência Legislativa Automatizada

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

**A solução - Radar Legislativo:** um pipeline automatizado que captura tudo o que
importa, resume com IA e entrega pronto para virar produto.

---

## Arquitetura do Pipeline

O projeto segue a **Arquitetura Medalhão** (Bronze -> Silver -> Gold), padrão de mercado
em engenharia de dados:

![Diagrama do pipeline do Radar Legislativo](docs/img/pipeline.png)

| Camada | Formato | Responsabilidade |
|--------|---------|------------------|
| **Bronze** | JSON | Dado bruto da API, salvo intacto (não chama a API de novo se o transform quebrar) |
| **Silver** | Parquet | Seleção de colunas, normalização de estruturas aninhadas, tipagem. Guarda as tabelas dimensão. |
| **Gold** | Parquet | Joins entre tabelas, validações de qualidade. Guarda as tabelas fato. |
| **PostgreSQL** | Supabase | Banco final, consultável e pronto para produto |
| **IA** | PostgreSQL | Resumo executivo de proposições (coluna `resumo_ia`) via LLM, gravado no banco |
| **n8n** | Workflow | Automação: email semanal com as proposições mais relevantes |

> A extração puxa, por padrão, os dados de **1 dia** (o orquestrador roda diariamente).
> Cargas históricas (ex.: 30 dias) são feitas manualmente ajustando a data inicial.

> Fonte editável do diagrama: [`docs/img/pipeline.excalidraw`](docs/img/pipeline.excalidraw) (abra em [excalidraw.com](https://excalidraw.com)).

---

## Modelo de Dados

Modelagem dimensional simples (estrela), carregada no PostgreSQL:

**Tabelas Fato (camada Gold)**
- `fat_proposicoes` - `id`, `sigla_tipo`, `cod_tipo`, `numero`, `ano`, `ementa`, `data_apresentacao`, **`resumo_ia`** (coluna preenchida pela camada de IA)
- `fat_votacoes` - `id_votacao`, `data`, `descricao`, `aprovacao`, `id_proposicao`, `ementa`, `proposicao_objeto`
- `fat_votacoes_votos` - `id`, `votacao_id`, `deputado_id`, `tipo_voto`
- `fat_deputados_despesas` - `id`, `deputado`, `tipo_despesa`, `data_documento`, `nome_fornecedor`, `valor_liquido`

**Tabelas Dimensão (camada Silver)**
- `dim_deputados` - `id`, `nome`, `sigla_partido`, `sigla_uf`, `id_legislatura`, `url_foto`, `email` (520 registros)
- `dim_proposicoes_autoria` - `id`, `proposicao_id`, `nome`, `tipo`, `cod_tipo`, `proponente`
- `dim_votacoes_detalhes` - `id`, `votacao_id`, `votacao_data`, `votacao_descricao`, `votacao_sigla_orgao`, `votacao_aprovacao`, `proposicao_id`
- `dim_partidos` - `id`, `sigla`, `nome`, `uri` (21 registros)

> Todas as tabelas possuem `created_at` (e algumas `hash_registro`) como metadados de controle e particionamento.
>
> A `fat_proposicoes` é carregada a partir da camada Silver (já no formato final de fato); as demais tabelas fato vêm da Gold.

**Relacionamentos**
- `fat_votacoes_votos.deputado_id` -> `dim_deputados.id`
- `fat_deputados_despesas.deputado` -> `dim_deputados.id`
- `fat_votacoes.id_proposicao` -> `fat_proposicoes.id`
- `dim_proposicoes_autoria.proposicao_id` -> `fat_proposicoes.id`

---

## Camada de IA

Para cada proposição, a **ementa** (texto jurídico denso) é enviada a um LLM
(`gpt-4o-mini` da OpenAI) que devolve um **resumo executivo de 3 linhas** em linguagem
clara - exatamente o que um cliente corporativo precisa ler em 10 segundos.

O resumo é salvo na coluna `resumo_ia` da tabela `fat_proposicoes` e alimenta
diretamente o email semanal do n8n (a IA agrega valor real ao produto, não é decoração).

> **Caminho escolhido: B - Resumo executivo** (em vez do Caminho A, classificação por
> embeddings). Optamos pelo resumo porque ele aparece **direto no produto final** (o e-mail
> semanal), em linguagem clara para o cliente - valor imediato e fácil de demonstrar.

**Prompt utilizado:**
```
Sistema: Você é um analista de inteligência legislativa da consultoria Bússola Pública.
Resuma a proposição abaixo em exatamente 3 linhas,
em linguagem clara para um executivo corporativo.
Seja objetivo. Não use jargão jurídico.

Usuário: Proposição: {ementa}
```

> **Controle de custo:** conforme recomendado no escopo, a camada de IA foi aplicada a
> uma amostra de cerca de 10 proposições (em vez do volume total), o suficiente para
> demonstrar o valor no produto final (o e-mail semanal) mantendo o custo baixo. Rodar a
> IA em todo o histórico fica como próximo passo.

### Exemplos reais (ementa → resumo)

**Exemplo 1 - parecer de relator**
> **Ementa:** "Parecer do Relator, Dep. Kim Kataguiri, pela compatibilidade e adequação
> financeira e orçamentária; e, no mérito, pela aprovação."
>
> **Resumo IA:** "O Relator avaliou a proposta e concluiu que está em conformidade com as
> normas financeiras e orçamentárias. Recomenda a aprovação da matéria. A decisão indica
> que a proposta é viável e pode avançar no processo legislativo."

**Exemplo 2 - requerimento de adiamento**
> **Ementa:** "Requerimento de Adiamento da Discussão de Matéria Urgente - PL 1822/2024."
>
> **Resumo IA:** "A proposta solicita o adiamento da discussão do Projeto de Lei 1822/2024,
> considerado urgente. O objetivo é ganhar mais tempo para análise e debate. A medida pode
> impactar o cronograma legislativo."

---

## Automação (n8n)

Workflow agendado que, semanalmente:
1. Consulta o PostgreSQL pelas proposições mais relevantes da semana (com `resumo_ia`);
2. Monta um email em HTML com cada proposição e o resumo gerado por IA;
3. Envia automaticamente para o cliente.

Fluxo: **Agendador semanal → Consulta no Supabase → Monta o e-mail (HTML) → Envia e-mail**.

> Workflow exportado: [`n8n/workflow_email_semanal.json`](n8n/workflow_email_semanal.json)
> (importe no n8n e reconecte as credenciais de Postgres e SMTP).

**Exemplo de e-mail recebido (execução real):**

![Email semanal gerado pelo n8n](docs/img/n8n_email.png)

---

## Decisões Técnicas

As principais escolhas de engenharia do projeto e o raciocínio por trás de cada uma.

### Arquitetura e armazenamento

- **Arquitetura Medalhão (Bronze → Silver → Gold).** Separa o pipeline em camadas com
  responsabilidades claras: dado bruto, dado limpo e dado modelado. Facilita encontrar e
  corrigir problemas, e é um padrão consolidado no mercado de engenharia de dados.
- **Salvar o JSON bruto na camada Bronze antes de qualquer transformação.** Se a etapa de
  transformação quebrar, não é preciso chamar a API de novo - basta reprocessar o arquivo
  já salvo. Isso poupa tempo e respeita os limites da API pública.
- **Parquet nas camadas Silver e Gold.** Formato colunar, tipado e compactado: ocupa menos
  espaço e é muito mais rápido de ler do que CSV/JSON para o volume que manipulamos.
- **PostgreSQL gerenciado no Supabase.** Plano gratuito generoso, painel web para visualizar
  as tabelas e rodar SQL, e link fácil de compartilhar na avaliação - sem precisar instalar
  banco na máquina. (O `pgvector` já vem habilitado, deixando aberta a porta para evoluções
  com embeddings no futuro.)

### Modelagem

- **Modelo dimensional simples (estrela), com tabelas fato e dimensão.** Deixa as consultas
  analíticas naturais (ex.: "quanto cada partido gastou") e é fácil de entender. As tabelas
  fato (`fat_*`) ficam na camada Gold; as dimensão (`dim_*`), na Silver.

### Ingestão

- **Extração incremental de 1 dia, com orquestração diária.** A API retorna, por padrão, uma
  janela recente; em vez de baixar anos de histórico de uma vez (lento e arriscado), o
  pipeline puxa o movimento do dia e roda todo dia. Cargas históricas maiores são feitas
  manualmente ajustando a data inicial, quando necessário.
- **Requisições assíncronas na extração de proposições.** A extração de proposições e autoria
  usa `httpx` com chamadas assíncronas, o que acelera bastante o download de grandes volumes
  (por exemplo, no backfill histórico de 30 dias).

### Camada de IA

- **Resumo executivo (em vez de classificação por embeddings).** O resumo gerado pela IA
  aparece **direto no produto final** (o e-mail semanal), em linguagem clara para um
  executivo. Ou seja, a IA agrega valor visível e imediato, não fica como enfeite técnico.
- **Modelo `gpt-4o-mini`.** Qualidade mais que suficiente para resumir ementas, a um custo
  de centavos. Para controlar o custo, a IA foi rodada em uma amostra de cerca de 10
  proposições, suficiente para demonstrar a camada. Processar o volume total fica como
  próximo passo.


### Automação

- **Workflow de e-mail semanal no n8n.** Entrega o "produto" da consultoria de forma
  tangível e demonstrável, conectando-se diretamente ao PostgreSQL para montar o relatório.

### Boas práticas

- **Segredos fora do versionamento.** Chaves de API e credenciais ficam só no `.env`
  (ignorado pelo `.gitignore`); o repositório traz apenas um `.env.example` como modelo.
- **Acesso ao banco para avaliação via usuário somente-leitura.** Um papel dedicado que só
  faz `SELECT`, evitando qualquer risco de alteração acidental dos dados.
- **Gerenciamento de dependências com `uv`** (`pyproject.toml` + `uv.lock`), garantindo um
  ambiente reproduzível.
- **Versionamento com branches e Pull Requests**, mantendo o histórico organizado e revisável.

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
# ou, com pip tradicional:
pip install -r requirements.txt

# 3. Configurar credenciais (copie o exemplo e preencha)
copy .env.example .env
#    Edite o .env com sua connection string do Supabase e sua chave OpenAI

# 4. Rodar o pipeline (na ordem)

# --- Bronze: extração da API (salva JSON bruto) ---
uv run API_BRZ_Deputados.py          # deputados + despesas
uv run API_BRZ_Partidos.py
uv run API_BRZ_Proposicoes.py        # proposições + autoria
uv run API_BRZ_Votacoes.py           # votações + detalhes + votos

# --- Silver: limpeza e normalização (salva Parquet) ---
uv run BRZ_SLV_Deputados.py
uv run BRZ_SLV_Deputados_Despesas.py
uv run BRZ_SLV_Partidos.py
uv run BRZ_SLV_Proposicoes.py
uv run BRZ_SLV_Proposicoes_Autoria.py
uv run BRZ_SLV_Votacoes.py
uv run BRZ_SLV_Votacoes_Detalhes.py
uv run BRZ_SLV_Votacoes_Votos.py

# --- Gold: modelagem e validações (salva Parquet) ---
uv run SLV_GLD_Deputados_Despesas.py
uv run SLV_GLD_Proposicoes.py
uv run SLV_GLD_Votacoes.py
uv run SLV_GLD_Votacoes_Votos.py

# --- Carga no PostgreSQL / Supabase (Etapa 3) ---
uv run src/load/teste_conexao_supabase.py        # (opcional) testa a conexão
uv run src/load/load_dim_deputados_supabase.py
uv run src/load/load_dim_partidos_supabase.py
uv run src/load/load_proposicoes_autoria_supabase.py
uv run src/load/load_fat_proposicoes_supabase.py
uv run src/load/load_despesas_supabase.py
uv run src/load/load_votacoes_supabase.py
uv run src/load/load_votacoes_detalhes_supabase.py
uv run src/load/load_votacoes_votos_supabase.py

# --- IA: resumo executivo das proposições (Etapa 4) ---
uv run GLD_IA_Proposicoes.py   # requer OPENAI_API_KEY no .env
```

> **Nunca** commite o arquivo `.env`. Ele já está no `.gitignore`.

---

## Estrutura do Repositório

```
projeto_final_1/
├── API_BRZ_*.py        # Extração da API -> Bronze (JSON)
├── BRZ_SLV_*.py        # Limpeza Bronze -> Silver (Parquet)
├── SLV_GLD_*.py        # Modelagem Silver -> Gold (Parquet)
├── GLD_IA_Proposicoes.py  # Camada de IA: resumo executivo (Etapa 4)
├── src/load/*.py       # Carga das tabelas no PostgreSQL (Etapa 3)
├── n8n/                # Workflow de automação n8n (email semanal)
├── docs/img/           # Diagrama do pipeline e prints
├── Notas API.txt       # Anotações sobre os endpoints da API
├── pyproject.toml      # Dependências (uv)
├── requirements.txt    # Dependências (pip)
├── .gitignore
└── README.md
```

---

## Resultados e Demonstração

### Tabelas populadas no PostgreSQL (Supabase)

A base reúne dados reais da Câmara dos Deputados, já tratados e modelados.

**Dimensão de deputados** - os deputados carregados da base (520 registros, inclui suplentes):

![Tabela dim_deputados](docs/img/dim_deputados.png)

**Autoria das proposições** - quem propôs cada matéria:

![Tabela dim_proposicoes_autoria](docs/img/dim_proposicoes_autoria.png)

**Despesas (cota parlamentar)** - milhares de gastos declarados:

![Tabela fat_deputados_despesas](docs/img/fat_deputados_despesas.png)

**Votações** - as votações ocorridas no período:

![Tabela fat_votacoes](docs/img/fat_votacoes.png)

### Análises de exemplo (consultas SQL)

O banco não é só um depósito de linhas - é **consultável e gera insight**. Alguns exemplos:

**Maiores bancadas da Câmara** - o PL lidera com 99 deputados:

![Top 10 partidos por número de deputados](docs/img/top10_partidos_por_deputados.png)

**Deputados que mais gastaram a cota parlamentar** (com nome, partido e UF):

![Top 10 deputados por total de gastos](docs/img/top10_deputados_gastos.png)

**Tipos de despesa que mais consomem recursos** - divulgação e combustíveis no topo:

![Top 10 tipos de despesa por valor líquido](docs/img/top10_tipo_despesas_valor_liquido.png)

---

## Banco de Dados (acesso para avaliação)

O banco está hospedado no **Supabase** (PostgreSQL gerenciado, região São Paulo) e pode
ser consultado por qualquer cliente SQL usando o usuário **somente-leitura** abaixo
(criado especificamente para avaliação - só faz `SELECT`, não consegue alterar dados):

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

## Autores e Contribuidores
- Alex Macedo Teles Silva - [@AlexMacedo45](https://github.com/AlexMacedo45)
- Gabriel Ferreira Davila - [@Ferreira0826](https://github.com/Ferreira0826)
- Natasha Sugiyama - [@nasugiyama](https://github.com/nasugiyama)
- Nelson L. S. Neto - [@nelsonlsneto](https://github.com/nelsonlsneto)
- Raphael Gonçalves de Melo Valente - [@rgmelovalente](https://github.com/rgmelovalente)

---

_Projeto desenvolvido como Projeto Integrador da Fase 1 da pós-graduação em Engenharia de Dados e IA._
