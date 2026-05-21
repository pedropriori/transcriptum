# Transcriptum — Design Spec
> Criado em 2026-05-21 | Status: aprovado

## Visão Geral

Ferramenta CLI para transcrição em batch de áudios WhatsApp (.OGG) usando AssemblyAI. Gera outputs individuais por áudio e um arquivo consolidado, em múltiplos formatos. Arquitetada para ser importável como módulo no sistema Aurax no futuro.

---

## Arquitetura

### Estrutura de Arquivos

```
transcriptum/
├── config.yaml           ← configurações (pasta, idioma, formatos, extras)
├── transcribe.py         ← entry point CLI (Typer)
├── .env                  ← ASSEMBLYAI_API_KEY (gitignored)
├── src/
│   ├── config.py         ← carrega e valida config.yaml + .env (Pydantic)
│   ├── transcriber.py    ← lógica de batch via AssemblyAI SDK
│   ├── models.py         ← TranscriptionResult, AudioFile
│   └── exporters/
│       ├── base.py       ← classe abstrata Exporter
│       ├── txt.py
│       ├── markdown.py
│       ├── json.py
│       ├── docx.py
│       └── pdf.py
├── outputs/              ← saída padrão (gitignored)
├── lincohn-vo/           ← áudios de entrada
└── requirements.txt
```

### Princípio de Isolamento

Cada exporter recebe `List[TranscriptionResult]` e escreve arquivos. Nenhum exporter conhece os outros. Adicionar um novo formato = criar um arquivo em `exporters/`, sem tocar em nada existente.

---

## Interface CLI

### Comandos

```bash
# Roda com as configurações do config.yaml
python transcribe.py run

# Sobrescreve formatos pontualmente
python transcribe.py run --formats md,json,docx

# Pasta de input diferente do config
python transcribe.py run --input ./outro-batch

# Ativa extras na execução (flags mapeiam 1:1 com extras do config.yaml)
python transcribe.py run --timestamps --speakers --confidence

# Lista idiomas suportados pelo AssemblyAI (lista hardcoded dos docs oficiais)
python transcribe.py languages

# Exibe config atual resolvido
python transcribe.py config show
```

### Feedback Visual (Rich)

```
Transcriptum v1.0
─────────────────────────────────────────────────
Pasta:    ./lincohn-vo  (50 arquivos .ogg)
Idioma:   pt
Formatos: md, txt
─────────────────────────────────────────────────
Enviando para AssemblyAI...  ████████████ 100%

Transcrevendo...
  ✓ WhatsApp Audio 11.14.53.ogg       [0:28]
  ✓ WhatsApp Audio 11.14.53 (1).ogg   [0:45]
  ⠸ WhatsApp Audio 11.14.54.ogg       processando...

─────────────────────────────────────────────────
Exportando outputs...
  ✓ 50 arquivos individuais (.md, .txt)
  ✓ 2 consolidados (FULL.md, FULL.txt)

Concluído em 1m 42s  •  50/50 ok  •  outputs/lincohn-vo/2026-05-21_143201/
```

---

## Configuração

### config.yaml

```yaml
input_dir: "./lincohn-vo"
output_dir: "./outputs"
language: "pt"          # "pt", "en", "es", "fr", "auto", etc.
formats: ["md", "txt"]  # md, txt, json, docx, pdf

extras:
  timestamps: false
  speaker_diarization: false
  confidence_scores: false
```

### .env

```
ASSEMBLYAI_API_KEY=your_key_here
```

A API key nunca entra no `config.yaml` nem no git. Flags CLI sobrescrevem `config.yaml` pontualmente.

---

## Fluxo de Execução

1. Carregar `config.yaml` + `.env` via Pydantic — validação com erros claros
2. Coletar todos os `.ogg` da `input_dir`, ordenados por nome (ordem cronológica natural do WhatsApp)
3. Enviar batch para AssemblyAI via `transcriber.transcribe_group()`
4. Exibir progresso em tempo real com Rich
5. Mapear resultados de volta para os nomes de arquivo originais
6. Para cada formato selecionado, invocar o exporter correspondente
7. Escrever arquivos individuais + consolidado
8. Exibir tabela de resumo final

---

## Estrutura de Outputs

### Organização de Pastas

```
outputs/
└── lincohn-vo/
    └── 2026-05-21_143201/
        ├── individual/
        │   ├── 01_WhatsApp-Audio-11.14.53.md
        │   ├── 01_WhatsApp-Audio-11.14.53.txt
        │   ├── 02_WhatsApp-Audio-11.14.53-1.md
        │   └── ...
        ├── FULL.md
        ├── FULL.txt
        └── transcriptions.json   ← sempre gerado
```

Cada run gera uma pasta com timestamp — runs anteriores nunca são sobrescritos.

### Arquivo Individual

```markdown
# WhatsApp Audio 2026-05-21 at 11.14.53
> Duração: 0:28 | Idioma: pt | Confiança: 96%

Texto transcrito aqui...
```

### Arquivo Consolidado (FULL.md)

```markdown
# Transcrição — lincohn-vo
> Gerado em 2026-05-21 14:32 · 50 áudios · Idioma: pt

---

## Índice

| # | Arquivo | Duração | Confiança |
|---|---------|---------|-----------|
| 01 | WhatsApp Audio 11.14.53 | 0:28 | 96% |
| 02 | WhatsApp Audio 11.14.53 (1) | 0:45 | 94% |

---

## 01 · WhatsApp Audio 2026-05-21 at 11.14.53

> Duração: 0:28

Texto transcrito...

---

## 02 · WhatsApp Audio 2026-05-21 at 11.14.53 (1)
...
```

### transcriptions.json (formato pivô)

```json
[
  {
    "id": "01",
    "filename": "WhatsApp Audio 2026-05-21 at 11.14.53.ogg",
    "duration_seconds": 28,
    "language": "pt",
    "confidence": 0.96,
    "text": "...",
    "words": [],
    "utterances": [],
    "status": "completed"
  }
]
```

`words` e `utterances` são populados apenas quando os extras correspondentes estão ativos. Este JSON é a interface de saída para o Aurax.

---

## Tratamento de Erros

| Cenário | Comportamento |
|---|---|
| API key ausente | Erro claro antes de qualquer chamada, exit 1 |
| Pasta de input vazia | Mensagem descritiva, exit limpo |
| Arquivo individual falha | Logado com motivo, batch continua |
| Falha parcial | `status: "failed"` no `transcriptions.json` |
| Timeout da API | Retry automático via SDK (configurável) |
| Formato inválido no config | Erro de validação Pydantic com sugestão |

---

## Dependências

| Pacote | Uso |
|---|---|
| `assemblyai` | SDK oficial — upload, batch, polling |
| `typer[all]` | CLI + Rich incluído |
| `pydantic` | Validação do config.yaml |
| `python-dotenv` | Carrega .env |
| `pyyaml` | Lê config.yaml |
| `python-docx` | Export .docx |
| `fpdf2` | Export .pdf (sem deps C) |

---

## Caminho para o Aurax

- `transcriber.py` vira lib importável — zero mudança na lógica de negócio
- `transcribe.py` vira adaptador CLI sobre a lib
- Agentes do Aurax consomem `transcriptions.json` diretamente
- Extensões futuras (VSL, anúncios, processamento IA) adicionam novos exporters ou pipelines pós-transcrição sem alterar o núcleo

---

## Decisões de Design

| Decisão | Escolha | Motivo |
|---|---|---|
| Interface | Typer CLI + config.yaml | UX profissional, mínima complexidade |
| Batch | `transcribe_group()` | SDK gerencia concorrência e polling |
| Idioma padrão | `pt` configurável | Maioria dos casos de uso, flexível |
| Extras | Off por padrão | Outputs limpos, opt-in consciente |
| Formato pivô | JSON sempre gerado | Interface estável para Aurax e outros consumidores |
| Runs isolados | Pasta com timestamp | Nunca sobrescreve, histórico preservado |
