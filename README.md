# Quality Check — Auditoria de respostas de pesquisa

Web app para identificar respostas suspeitas em pesquisas exportadas do
QuestionPro / SurveyMonkey / Typeform. Detecta IPs duplicados, tempos de
resposta muito curtos, marcas inválidas (óleo de motor mencionado como
camisinha 🙃), gibberish e copy-paste entre campos.

## O que o sistema faz

Para cada respondente, calcula um **score de suspeita** (0-100) somando flags:

| Flag | Peso | O que detecta |
|---|---|---|
| `flag_marca_oleo` | 30 | Marca de óleo automotivo (Bardahl, Castrol, Mobil...) |
| `flag_copy_paste` | 25 | Mesma resposta colada em 4+ campos |
| `flag_gibberish` | 25 | Texto sem sentido (`bbsv`, `dmmrmrm`, `gggg`) |
| `flag_so_simbolos` | 20 | Resposta só com pontuação (`*`, `???`, `:(`) |
| `flag_lugar_nao_marca` | 15 | Lugar mencionado como marca (IMSS, Bodega Aurrera) |
| `flag_muitas_marcas_raras` | 15 | 3+ marcas não reconhecidas |
| `flag_tempo_curto` | 15 | Tempo abaixo do limite (default 8 min) |
| `flag_ip_duplicado` | 10 | IP já apareceu em outra resposta |

**Classificação final:**
- 🔴 Alta suspeita: score ≥ 40
- 🟡 Revisar: score 20-39
- 🟢 OK com observações: score 1-19
- ✅ Limpo: score 0

## O que o sistema NÃO marca como erro

- Vaselina, óleo de bebê, óleo de coco/oliva — gente realmente usa como
  lubrificante (mesmo sendo má ideia clinicamente)
- "No sé", "no recuerdo", "ninguna" — respostas legítimas
- Typos óbvios de marcas conhecidas (`troyan` → Trojan, `produnce` →
  Prudence, `mforce` → M Force) via fuzzy match

## Instalação

```bash
cd quality_check_app
pip install flask pandas openpyxl
python app.py
```

Acesse <http://localhost:5000>.

## Como usar

1. Exporte o arquivo `.xlsx` da plataforma (QuestionPro: "Datos sin procesar")
2. Suba no app
3. Ajuste o tempo mínimo aceitável (default 8 min)
4. Clique em **Analizar**
5. Revise o dashboard e baixe o Excel com 3 abas:
   - **Resumen**: estatísticas gerais
   - **Revisar**: só respondentes com score ≥ 20 (prioridade)
   - **Datos completos**: tudo + colunas de flag + linhas coloridas

Os IDs marcados em vermelho são os que você deve eliminar primeiro na
plataforma.

## Estrutura

```
quality_check_app/
├── app.py              # Flask + endpoints
├── quality.py          # Lógica de detecção (testável isolado)
└── templates/
    └── index.html      # UI single-page
```

A lógica de detecção fica isolada em `quality.py` então é fácil ajustar
pesos, adicionar marcas à blacklist/whitelist ou criar testes.

## Configuração

As listas estão no topo de `quality.py`:

- `BLACKLIST_BRANDS`: marcas de óleo / produtos automotivos
- `KNOWN_VALID_BRANDS`: marcas seed de camisinha/lubrificante
- `NON_BRAND_PLACES`: lugares/instituições
- `NON_ANSWERS`: "não sei", "ninguna", etc.
- `HOMEMADE_LUBES`: vaselina, óleo de bebê — respostas legítimas

Adicione novas marcas conforme a base evoluir.

## Limites conhecidos

- Funciona com formato QuestionPro (colunas 63-74 são as marcas abertas).
  Se sua plataforma exportar diferente, ajuste `brand_col_indices` em
  `analyze()`.
- Tempo de processamento: ~5-15s para 1000 respostas.
- Limite de upload: 50 MB.
