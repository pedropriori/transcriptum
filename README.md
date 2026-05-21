# Transcriptum

Ferramenta CLI para transcrição em batch de áudios WhatsApp (.OGG) via [AssemblyAI](https://www.assemblyai.com/). Gera outputs individuais e consolidados em múltiplos formatos, com menu interativo e barra de progresso em tempo real.

---

## Funcionalidades

- **Menu TUI interativo** — navegação com setas, seleção de formatos, idioma e extras sem precisar decorar flags
- **Barra de progresso em tempo real** — cada arquivo aparece ao ser concluído, com duração e confiança
- **5 formatos de saída** — Markdown, TXT, JSON, DOCX e PDF gerados simultaneamente
- **Runs isolados** — cada execução cria uma pasta com timestamp, nunca sobrescreve resultados anteriores
- **`transcriptions.json` sempre gerado** — arquivo pivô com todos os dados estruturados para uso programático
- **12 idiomas + auto-detecção** — português, inglês, espanhol, francês, alemão e mais
- **Extras opcionais** — timestamps por palavra, diarização por speaker, confiança por palavra

---

## Exemplo de uso

```
╭──────────────────── Transcriptum ─────────────────────╮
│  Pasta     ./input/audio-fies  (50 arquivos .ogg)     │
│  Idioma    pt  — Português                             │
│  Formatos  md, txt                                     │
│  Extras    nenhum                                      │
│  API Key   ● configurada                               │
╰────────────────────────────────────────────────────────╯

  Selecione uma opção  [↑↓ para navegar · Enter para selecionar]
  ─── Configurações ──────────────────────────────────────
  » 📁  Pasta de entrada    ./input/audio-fies
    🌍  Idioma              pt — Português
    📄  Formatos            md, txt
    ⚙   Extras              nenhum
  ───────────────────────────────────────────────────────
    ▶   Iniciar transcrição  (50 arquivos)
    ✕   Sair
```

```
Transcrevendo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  12/50  0:00:38
  ✓ 01 WhatsApp Audio 2026-05-21 at 11.14.53.ogg    0:28 · 96%
  ✓ 02 WhatsApp Audio 2026-05-21 at 11.14.53 (1).ogg  0:45 · 94%
  ✓ 03 WhatsApp Audio 2026-05-21 at 11.14.54.ogg    1:02 · 97%
  ...
```

---

## Requisitos

- Python 3.11+
- Conta no [AssemblyAI](https://www.assemblyai.com/) (plano gratuito disponível)

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/transcriptum.git
cd transcriptum

# 2. (Recomendado) Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Configuração

### 1. API Key

Copie o arquivo de exemplo e adicione sua chave do AssemblyAI:

```bash
cp .env.example .env
```

Edite `.env`:

```
ASSEMBLYAI_API_KEY=sua_chave_aqui
```

Obtenha sua chave gratuita em [assemblyai.com](https://www.assemblyai.com/app).

### 2. config.yaml

O arquivo `config.yaml` define os padrões de cada execução:

```yaml
input_dir: "./input/audio-fies"   # pasta com os arquivos .ogg
output_dir: "./outputs"           # onde os resultados são salvos
language: "pt"                    # idioma padrão (pt, en, es, fr, de, auto...)
formats:
  - md                            # formatos gerados por padrão
  - txt

extras:
  timestamps: false               # timestamps por palavra
  speaker_diarization: false      # quem falou cada trecho
  confidence_scores: false        # confiança por palavra
```

Todos os valores podem ser sobrescritos via menu interativo ou flags CLI.

---

## Uso

### Modo interativo (recomendado)

```bash
python transcribe.py run
```

Abre o menu TUI onde você navega com setas e personaliza pasta, idioma, formatos e extras antes de iniciar.

### Flags diretas (modo não-interativo)

```bash
# Usar config.yaml sem nenhuma pergunta
python transcribe.py run --yes

# Sobrescrever formatos
python transcribe.py run --formats md,json,docx --yes

# Pasta de entrada diferente
python transcribe.py run --input ./outro-batch --yes

# Ativar extras
python transcribe.py run --timestamps --speakers --confidence --yes
```

### Outros comandos

```bash
# Listar idiomas suportados
python transcribe.py languages

# Ver configuração atual resolvida
python transcribe.py config show

# Ajuda geral
python transcribe.py --help
python transcribe.py run --help
```

---

## Estrutura de outputs

Cada execução cria uma pasta com timestamp dentro de `outputs/`. Runs anteriores nunca são sobrescritos.

```
outputs/
└── audio-fies/
    └── 2026-05-21_143201/
        ├── individual/
        │   ├── 01_WhatsApp-Audio-2026-05-21-at-11.14.53.md
        │   ├── 01_WhatsApp-Audio-2026-05-21-at-11.14.53.txt
        │   ├── 02_WhatsApp-Audio-2026-05-21-at-11.14.53-1.md
        │   └── ...
        ├── FULL.md
        ├── FULL.txt
        └── transcriptions.json   ← sempre gerado
```

### Arquivo individual (Markdown)

```markdown
# WhatsApp Audio 2026-05-21 at 11.14.53.ogg
> Duração: 0:28 | Idioma: pt | Confiança: 96%

Texto transcrito aqui...
```

### FULL.md (consolidado)

Contém índice com tabela de todos os áudios, seguido de cada transcrição com separadores.

### transcriptions.json

Formato estruturado com todos os dados. Ideal para integração com outros sistemas:

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

`words` e `utterances` são populados apenas quando os extras correspondentes estão ativos.

---

## Formatos suportados

| Formato | Arquivo | Descrição |
|---------|---------|-----------|
| `md`    | `.md`   | Markdown com cabeçalhos, blockquotes e tabela de índice |
| `txt`   | `.txt`  | Texto plano com separadores e índice |
| `json`  | `.json` | JSON estruturado (dados completos) |
| `docx`  | `.docx` | Word com estilos de título e itálico |
| `pdf`   | `.pdf`  | PDF via fpdf2, pronto para impressão |

---

## Idiomas suportados

| Código | Idioma    |
|--------|-----------|
| `pt`   | Português |
| `en`   | English   |
| `es`   | Español   |
| `fr`   | Français  |
| `de`   | Deutsch   |
| `it`   | Italiano  |
| `nl`   | Nederlands|
| `hi`   | Hindi     |
| `ja`   | 日本語    |
| `ko`   | 한국어    |
| `zh`   | 中文      |
| `auto` | Auto-detect |

---

## Extras

Ativados via menu interativo ou flags:

| Extra | Flag | Descrição |
|-------|------|-----------|
| Timestamps | `--timestamps` | Start/end em ms de cada palavra em `words[]` |
| Diarização | `--speakers`   | Identifica quem falou cada trecho em `utterances[]` |
| Confiança  | `--confidence` | Score de confiança por palavra em `words[]` |

---

## Tratamento de erros

| Situação | Comportamento |
|----------|---------------|
| API key ausente | Erro antes de qualquer chamada, exit 1 |
| Pasta de entrada vazia | Mensagem descritiva, exit limpo |
| Arquivo individual falha | `status: "failed"` no JSON, batch continua |
| Formato inválido no config | Erro de validação com sugestão |

---

## Desenvolvimento

### Rodar testes

```bash
python -m pytest -v
```

50 testes unitários cobrindo modelos, config, todos os exporters e transcriber (com mock do SDK AssemblyAI).

### Estrutura do projeto

```
transcriptum/
├── transcribe.py           # Entry point CLI (Typer + menu TUI)
├── config.yaml             # Configuração padrão
├── .env.example            # Template da API key
├── requirements.txt
├── src/
│   ├── models.py           # AudioFile, TranscriptionResult, etc.
│   ├── config.py           # AppConfig (Pydantic), load_config()
│   ├── transcriber.py      # collect_audio_files(), transcribe_batch()
│   └── exporters/
│       ├── base.py         # Classe abstrata Exporter
│       ├── txt.py
│       ├── markdown.py
│       ├── json.py
│       ├── docx.py
│       └── pdf.py
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_transcriber.py
    └── exporters/
        ├── test_txt.py
        ├── test_markdown.py
        ├── test_json.py
        ├── test_docx.py
        └── test_pdf.py
```

### Adicionar um novo formato

1. Crie `src/exporters/meu_formato.py` com uma classe que estende `Exporter`
2. Implemente `extension`, `render_individual()` e `render_full()`
3. Registre em `src/exporters/__init__.py`

Nenhum outro arquivo precisa ser alterado.

---

## Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| `assemblyai` | ≥0.28.0 | SDK oficial — upload, batch, polling |
| `typer[all]` | ≥0.12.0 | CLI + Rich incluído |
| `questionary` | ≥2.0.0 | Menu TUI interativo |
| `pydantic` | ≥2.7.0 | Validação do config.yaml |
| `python-dotenv` | ≥1.0.0 | Carrega .env |
| `pyyaml` | ≥6.0.1 | Lê config.yaml |
| `python-docx` | ≥1.1.0 | Export .docx |
| `fpdf2` | ≥2.7.9 | Export .pdf |

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.
