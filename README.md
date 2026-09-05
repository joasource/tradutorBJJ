# Tradutor de Legendas de Jiu-Jitsu (BJJ) - Inglês para pt_BR

Script especializado em tradução de vídeos instrucionais de Jiu-Jitsu Brasileiro (BJJ) do inglês para o Português do Brasil (pt-BR), utilizando o modelo local **`gemma4:e4b`** via Ollama com alinhamento ergonômico de legendas para leitura humana.

---

## 🥋 Características Principais

1. **Terminologia Autêntica de BJJ:**
   - O prompt foi desenhado para vocabulário técnico de tatame:
     * *Closed Guard* → Guarda Fechada
     * *Open Guard* → Guarda Aberta
     * *Sweep* → Raspagem (evita "varrer")
     * *Submission* → Finalização (evita "submissão")
     * *Posture break* → Quebra de postura
     * *Underhook* → Esgrima / Underhook
     * *Scrimmage wrestling / wrestling up* → Disputas de wrestling / levantar da guarda
     * *Leg locks / Heel hook* → Leg locks / Chave de calcanhar
     * *Pass* → Passagem de guarda
     * Preserva marcas e nomes próprios intactos (*New Wave*, *John Danaher*, *Gordon Ryan*).

2. **Alinhamento e Legibilidade Humana (Padrão Netflix / EBU):**
   - **42 a 48 caracteres por linha** (padrão ergonômico recomendado).
   - **Máximo de 2 linhas por bloco**.
   - **Frases curtas:** se couber em 1 linha, mantém em 1 linha (evita quebrar sem necessidade).
   - **Quebra sintática e gramatical:**
     * Quebra preferencialmente após pontuações (vírgulas, pontos, dois-pontos).
     * Quebra antes de conjunções e orações subordinadas (*e*, *mas*, *porque*, *que*, *para*).
     * **Proteção de termos compostos:** nunca corta termos técnicos ao meio (ex: *"guarda fechada"*, *"Jiu-Jitsu"*, *"chave de braço"*, *"No-Gi"*).
     * **Prevenção de palavras órfãs:** nunca deixa uma palavra isolada de 3 letras na linha de baixo.
     * Balanceamento em pirâmide invertida (linha superior ligeiramente maior ou igual à inferior).

3. **Conexão Híbrida Inteligente (Ollama / Docker Open-WebUI):**
   - Tenta conexão HTTP direta em `http://localhost:11434`.
   - Se a porta 11434 não estiver exposta diretamente no host (como ocorre quando o Ollama roda empacotado dentro do container `open-webui`), o script **detecta automaticamente e roteia os comandos via `docker exec -i open-webui curl`** sem necessidade de configurações extras.

4. **Tradução em Lotes (Batches) com Continuidade:**
   - Agrupa as legendas em blocos de 10 unidades por padrão.
   - Fornece contexto conversacional completo ao modelo, garantindo que frases faladas ao longo de duas legendas continuem de forma 100% natural.

5. **Sistema de Checkpoint e Resume (Recuperação Automática):**
   - Salva o progresso no disco após cada lote (`.nome_arquivo.checkpoint.json`).
   - Se o processo for interrompido com `Ctrl+C` ou queda de energia, ao executar novamente ele **continua exatamente da legenda onde parou**, sem gastar tempo nem recursos repetindo o que já foi traduzido.

---

## 🚀 Como Executar

### 1. Modo Interativo (Mais Fácil)
Basta executar o atalho `./traduzir.sh` ou o script Python no terminal:

```bash
./traduzir.sh
# ou
python tradutorBJJ.py
```

O script exibirá um menu interativo onde você poderá:
- Escolher a pasta ou arquivo SRT (o padrão já é `/home/joaquim/john`).
- Escolher se deseja traduzir um arquivo específico ou todos os arquivos da pasta de uma vez.
- Confirmar o modelo Ollama (`gemma4:e4b`).
- Ajustar o limite de caracteres por linha (padrão: 45) e tamanho do lote (padrão: 10).

---

### 2. Modo Linha de Comando (CLI com Parâmetros)

Você pode passar todos os argumentos diretamente pela linha de comando:

#### Traduzir um arquivo específico:
```bash
./traduzir.sh -i "New Wave Closed Guard 1.srt"
```
*(O resultado será salvo automaticamente como `New Wave Closed Guard 1.pt_BR.srt`)*

#### Traduzir todos os arquivos SRT de uma pasta:
```bash
./traduzir.sh -i /home/joaquim/john
```

#### Especificar um arquivo de saída customizado:
```bash
./traduzir.sh -i "New Wave Closed Guard 1.srt" -o "legendas_prontas/aula1_pt.srt"
```

#### Fazer um teste rápido (Dry-Run) nas primeiras 10 legendas:
```bash
./traduzir.sh -i "New Wave Closed Guard 1.srt" --dry-run 10
```

#### Ajustar caracteres por linha e tamanho do lote:
```bash
./traduzir.sh -i "New Wave Closed Guard 1.srt" --max-chars 42 --batch-size 12
```

---

## ⚙️ Opções Disponíveis na Linha de Comando

| Parâmetro | Descrição | Padrão |
| :--- | :--- | :--- |
| `-i`, `--input` | Caminho do arquivo SRT ou da pasta com os SRTs | `/home/joaquim/john` |
| `-o`, `--output` | Caminho do arquivo ou pasta de saída | `[nome_original].pt_BR.srt` |
| `-m`, `--model` | Nome do modelo registrado no Ollama | `gemma4:e4b` |
| `-u`, `--ollama-url` | URL da API do Ollama | `http://localhost:11434` |
| `-c`, `--container` | Nome do container Docker com o Ollama | `open-webui` |
| `--max-chars` | Limite de caracteres por linha para alinhamento | `45` (faixa 42 a 48) |
| `--batch-size` | Quantidade de legendas enviadas por lote ao LLM | `10` |
| `--dry-run N` | Traduz apenas as primeiras `N` legendas para teste | Desativado |
| `-f`, `--overwrite` | Sobrescreve arquivos já traduzidos em vez de pulá-los | Desativado |
| `--no-resume` | Ignora checkpoints anteriores e recomeça do zero | Desativado |
| `--no-reformat` | Não formata/alinha as quebras de linha | Desativado |
| `--interactive` | Força a exibição do menu interativo no terminal | Desativado |

---

## 💡 Dicas de Uso

- **Pausar e Continuar:** Se precisar pausar a tradução a qualquer momento, aperte `Ctrl+C`. Ao rodar o mesmo comando novamente, o script detecta o checkpoint e retoma instantaneamente.
- **Player de Vídeo:** Ao colocar o arquivo traduzido com o mesmo nome do vídeo (ex: `New Wave Closed Guard 1.pt_BR.srt` ou `New Wave Closed Guard 1.srt`), players como VLC, MPV ou reprodutor do sistema carregarão a legenda automaticamente.
