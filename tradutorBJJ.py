#!/usr/bin/env python3
"""
===============================================================================
Tradutor de Legendas de Jiu-Jitsu Brasileiro (BJJ) - Inglês -> pt_BR
===============================================================================
Autor: Antigravity (Google DeepMind pair programmer)
Modelo padrão: gemma4:e4b via Ollama (suporte nativo a Docker open-webui e HTTP)
Alinhamento: Quebra de linha sintática e balanceada para padrão de leitura humana (42-48 caracteres, máx 2 linhas)
===============================================================================
"""

import os
import sys
import re
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# =============================================================================
# CORES ANSI PARA O TERMINAL
# =============================================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 75}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 75}{Colors.RESET}\n")

def print_success(msg: str):
    print(f"{Colors.GREEN}[✓] {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.CYAN}[i] {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}[!] {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}[✗] {msg}{Colors.RESET}")

# =============================================================================
# PROMPT ESPECIALIZADO DE BJJ (TERMINOLOGIA TÉCNICA)
# =============================================================================
BJJ_SYSTEM_PROMPT = """Você é um tradutor profissional e faixa-preta especialista em Jiu-Jitsu Brasileiro (BJJ).
Sua missão é traduzir legendas de instrucionais de Jiu-Jitsu do inglês para o Português do Brasil (pt-BR).

REGRAS ESSENCIAIS:
1. CONTINUIDADE DAS FRASES:
   As legendas vêm de fala contínua dividida em blocos de tempo. Muitas vezes uma frase começa em uma legenda e termina na próxima. Mantenha a pontuação e o fluxo natural em português, sem truncar sentenças.

2. TERMINOLOGIA TÉCNICA AUTÊNTICA DO JIU-JITSU:
   - Closed Guard -> Guarda Fechada
   - Open Guard -> Guarda Aberta
   - Half Guard -> Meia-Guarda
   - Butterfly Guard -> Guarda Borboleta
   - Spider Guard -> Guarda Aranha
   - De La Riva -> De La Riva
   - Posture / Posture Break -> Postura / Quebra de Postura
   - Break down posture -> Quebrar a postura
   - Sweep -> Raspagem (NUNCA traduza como "varrer" ou "varrida")
   - Pass / Guard Passing -> Passagem / Passagem de Guarda (NUNCA "passar através")
   - Submission -> Finalização (NUNCA "submissão")
   - Tap / Tap out -> Bater / Desistir (NUNCA "torneira")
   - Underhook -> Esgrima (ou underhook)
   - Overhook -> Overhook (ou laçada)
   - Cross face -> Cross face (ou esgrima de cabeça)
   - Mount / Full Mount -> Montada
   - Back take / Back control -> Pegada de costas / Controle de costas
   - Side control -> 100 quilos / Controle lateral
   - North-South -> Norte-Sul
   - Armbar / Armlock -> Armlock (ou chave de braço)
   - Triangle -> Triângulo
   - Kimura / Americana / Omoplata -> Kimura / Americana / Omoplata
   - Guillotine -> Guilhotina
   - Leg locks -> Leg locks (ou chaves de perna)
   - Heel hook -> Chave de calcanhar (ou heel hook)
   - Kneebar -> Chave de joelho
   - Ankle lock / Straight foot lock -> Botinha (ou chave de tornozelo)
   - No-Gi -> No-Gi (ou sem quimono)
   - Gi -> De quimono
   - Grips -> Pegadas
   - Mat -> Tatame
   - Drilling -> Treino de repetição / Drilling
   - Sparring / Rolling -> Rola / Treino livre
   - Scrimmage wrestling / Wrestling up -> Disputas de wrestling / Levantar da guarda
   - Bottom position -> Posição por baixo
   - Top position -> Posição por cima
   - Nomes próprios e marcas (ex: "New Wave", "John Danaher", "Gordon Ryan", "BJJ Fanatics") NUNCA devem ser traduzidos.

3. CONCISÃO E ECONOMIA DE ESPAÇO (LEGIBILIDADE HUMANA):
   - Como as legendas precisam ser lidas rapidamente na tela (alvo de 40 a 48 caracteres por linha, máx 2 linhas), seja DIRETO e NATURAL.
   - O português tende a ser mais longo; corte pronomes redundantes e prolixidade (ex: prefira "apresento" em vez de "eu quero apresentar a vocês").

4. ESTILO DE RESPOSTA:
   - Tom instrutivo e fluente, como um professor brasileiro no tatame.
   - NÃO adicione saudações, explicações extras, comentários ou notas de rodapé.
   - Retorne ESTRITAMENTE um objeto JSON válido no formato:
     {"translations": [{"id": <numero>, "text": "<texto_traduzido>"}, ...]}
"""

# =============================================================================
# FORMATADOR DE LEGENDAS (PESQUISA DE LEGIBILIDADE HUMANA E PADRÃO NETFLIX/EBU)
# =============================================================================
class SubtitleFormatter:
    """
    Formata o texto da legenda respeitando princípios ergonômicos de leitura:
    - Limite de caracteres por linha (normalmente 42 a 48 caracteres).
    - Máximo de 2 linhas por bloco (padrão de TV/streaming internacional).
    - Se couber em 1 linha, mantém em 1 linha (evita quebrar frases curtas).
    - Quebra sintática/gramatical inteligente:
      * Quebra preferencialmente após pontuações (., ;, :, ?, !, -).
      * Quebra preferencialmente antes de conjunções (e, mas, ou, porque, que).
      * Quebra antes de preposições (para, com, em, de).
      * NUNCA quebra termos compostos de BJJ (ex: "guarda fechada", "No-Gi", "Jiu-Jitsu").
      * NUNCA deixa 'palavras órfãs' (uma única palavra isolada na segunda linha).
      * Balanceamento visual tipo pirâmide invertida (linha superior ligeiramente maior ou igual).
    """

    def __init__(self, max_chars: int = 45, max_lines: int = 2):
        self.max_chars = max_chars
        self.max_lines = max_lines

        # Expressões técnicas e nomes para não quebrar no meio
        self.compound_regexes = [
            re.compile(r'\bjiu[-\s]jitsu\b', re.IGNORECASE),
            re.compile(r'\bguarda\s+fechada\b', re.IGNORECASE),
            re.compile(r'\bguarda\s+aberta\b', re.IGNORECASE),
            re.compile(r'\bmeia[-\s]guarda\b', re.IGNORECASE),
            re.compile(r'\bno[-\s]gi\b', re.IGNORECASE),
            re.compile(r'\bchaves?\s+de\s+braço\b', re.IGNORECASE),
            re.compile(r'\bchaves?\s+de\s+perna\b', re.IGNORECASE),
            re.compile(r'\bchaves?\s+de\s+calcanhar\b', re.IGNORECASE),
            re.compile(r'\bchaves?\s+de\s+joelho\b', re.IGNORECASE),
            re.compile(r'\bnew\s+wave\b', re.IGNORECASE),
            re.compile(r'\bjohn\s+danaher\b', re.IGNORECASE),
            re.compile(r'\bgordon\s+ryan\b', re.IGNORECASE),
            re.compile(r'\bleg\s+locks?\b', re.IGNORECASE),
            re.compile(r'\bquebra\s+de\s+postura\b', re.IGNORECASE),
            re.compile(r'\bpassagem\s+de\s+guarda\b', re.IGNORECASE),
            re.compile(r'\bposição\s+por\s+baixo\b', re.IGNORECASE),
            re.compile(r'\bposição\s+por\s+cima\b', re.IGNORECASE),
            re.compile(r'\b100\s+quilos\b', re.IGNORECASE),
        ]

        # Finais de linha indesejados (artigos e preposições penduradas)
        self.bad_endings = {
            'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
            'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
            'por', 'pelo', 'pela', 'pelos', 'pelas', 'com', 'sem',
            'seu', 'sua', 'seus', 'suas', 'meu', 'minha', 'teu', 'tua'
        }

        # Conjunções e termos que abrem orações (ótimos para iniciar linha 2)
        self.good_starts = {
            'e', 'mas', 'ou', 'porque', 'pois', 'que', 'se', 'quando',
            'como', 'para', 'onde', 'já', 'embora', 'então', 'assim'
        }

    def _protect_compounds(self, text: str) -> str:
        """Substitui espaços em termos compostos por espaço não-separável temporário."""
        protected = text
        for pattern in self.compound_regexes:
            def repl(m):
                return m.group(0).replace(' ', '\u00a0')
            protected = pattern.sub(repl, protected)
        return protected

    def _unprotect(self, text: str) -> str:
        """Restaura espaços normais."""
        return text.replace('\u00a0', ' ')

    def format_text(self, text: str) -> str:
        clean_text = ' '.join(text.strip().split())
        if not clean_text:
            return ""

        # REGRA 1: Se já cabe em 1 linha, mantém em 1 linha
        if len(clean_text) <= self.max_chars:
            return clean_text

        # Protege termos compostos
        protected_text = self._protect_compounds(clean_text)
        words = protected_text.split(' ')
        if len(words) <= 1:
            return self._unprotect(clean_text)

        best_score = float('-inf')
        best_split = len(words) // 2

        for i in range(1, len(words)):
            line1_raw = ' '.join(words[:i])
            line2_raw = ' '.join(words[i:])

            len1 = len(self._unprotect(line1_raw))
            len2 = len(self._unprotect(line2_raw))

            score = 0.0

            # 1. Penalidade severa por exceder o limite de caracteres
            if len1 > self.max_chars:
                score -= (len1 - self.max_chars) * 25.0
            if len2 > self.max_chars:
                score -= (len2 - self.max_chars) * 25.0

            # 2. Balanceamento de tamanho (pirâmide invertida: linha 1 >= linha 2)
            diff = abs(len1 - len2)
            if len1 >= len2:
                score -= diff * 0.4
            else:
                score -= diff * 1.0

            # 3. Bônus por pontuação ao final da linha 1
            last_word = words[i - 1]
            if last_word.endswith(('.', '!', '?')):
                score += 45.0
            elif last_word.endswith((';', ':')):
                score += 35.0
            elif last_word.endswith(','):
                score += 28.0
            elif last_word.endswith(('-', '—')):
                score += 20.0

            # 4. Penalidade por artigo/preposição solta no fim da linha 1
            clean_last = re.sub(r'[^\w]', '', self._unprotect(last_word).lower())
            if clean_last in self.bad_endings:
                score -= 35.0

            # 5. Bônus por conjunção iniciando a linha 2
            first_word_l2 = re.sub(r'[^\w]', '', self._unprotect(words[i]).lower())
            if first_word_l2 in self.good_starts:
                score += 18.0

            # 6. Prevenção de palavras órfãs (linha com apenas 1 palavra ou < 8 chars)
            if len(line1_raw.split()) == 1 or len1 < 8:
                score -= 40.0
            if len(line2_raw.split()) == 1 or len2 < 8:
                score -= 40.0

            if score > best_score:
                best_score = score
                best_split = i

        l1 = self._unprotect(' '.join(words[:best_split]))
        l2 = self._unprotect(' '.join(words[best_split:]))

        # Se exceder limite e permitir mais linhas
        if self.max_lines > 2 and (len(l1) > self.max_chars * 1.3 or len(l2) > self.max_chars * 1.3):
            sub_formatter = SubtitleFormatter(self.max_chars, self.max_lines - 1)
            return f"{l1}\n{sub_formatter.format_text(l2)}"

        return f"{l1}\n{l2}"


# =============================================================================
# CLIENTE OLLAMA (CONEXÃO HÍBRIDA: HTTP DIRETO + FALLBACK DOCKER OPEN-WEBUI)
# =============================================================================
class OllamaClient:
    """
    Gerencia comunicação com o Ollama:
    1. Tenta conexão HTTP direta (ex: http://localhost:11434).
    2. Se falhar (porta 11434 não exposta no host), usa fallback automático
       via `docker exec -i open-webui curl -s http://localhost:11434/...`.
    """

    def __init__(self, base_url: str = "http://localhost:11434", docker_container: str = "open-webui"):
        self.base_url = base_url.rstrip('/')
        self.docker_container = docker_container
        self.mode = self._detect_mode()

    def _detect_mode(self) -> str:
        # 1. Testar HTTP direto
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return "http"
        except Exception:
            pass

        # 2. Testar Docker container
        try:
            res = subprocess.run(
                ["docker", "exec", self.docker_container, "curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=4
            )
            if res.returncode == 0 and "models" in res.stdout:
                return "docker"
        except Exception:
            pass

        return "unknown"

    def list_models(self) -> List[str]:
        try:
            if self.mode == "http":
                import urllib.request
                req = urllib.request.Request(f"{self.base_url}/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return [m['name'] for m in data.get('models', [])]
            elif self.mode == "docker":
                res = subprocess.run(
                    ["docker", "exec", self.docker_container, "curl", "-s", "http://localhost:11434/api/tags"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    return [m['name'] for m in data.get('models', [])]
        except Exception:
            pass
        return []

    def chat_json(self, model: str, system_prompt: str, user_prompt: str, timeout: int = 120) -> Optional[Dict[str, Any]]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        json_payload = json.dumps(payload, ensure_ascii=False)

        if self.mode == "unknown":
            self.mode = self._detect_mode()

        if self.mode == "http":
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{self.base_url}/api/chat",
                    data=json_payload.encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    raw_content = res_data.get('message', {}).get('content', '')
                    return json.loads(raw_content)
            except Exception as e:
                print_warning(f"Falha na conexão HTTP direta ({e}). Tentando fallback via Docker...")
                self.mode = "docker"

        if self.mode == "docker":
            try:
                p = subprocess.run(
                    ["docker", "exec", "-i", self.docker_container, "curl", "-s", "http://localhost:11434/api/chat", "-d", "@-"],
                    input=json_payload,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                if p.returncode == 0:
                    res_data = json.loads(p.stdout)
                    raw_content = res_data.get('message', {}).get('content', '')
                    return json.loads(raw_content)
                else:
                    print_error(f"Erro no docker exec curl: {p.stderr}")
            except Exception as e:
                print_error(f"Exceção ao chamar Ollama via Docker: {e}")

        return None


# =============================================================================
# ESTRUTURA E PARSER DE ARQUIVOS SRT
# =============================================================================
class SubtitleCue:
    def __init__(self, index: int, timestamp: str, text: str):
        self.index = index
        self.timestamp = timestamp
        self.text = text

    def to_srt(self) -> str:
        return f"{self.index}\n{self.timestamp}\n{self.text}\n"

def parse_srt(file_path: Path) -> List[SubtitleCue]:
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    blocks = re.split(r'\n\s*\n', content.strip())
    cues: List[SubtitleCue] = []

    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) >= 3:
            try:
                idx_match = re.match(r'^\d+', lines[0])
                idx = int(idx_match.group(0)) if idx_match else len(cues) + 1
                timestamp = lines[1]
                text = ' '.join(lines[2:])
                cues.append(SubtitleCue(idx, timestamp, text))
            except Exception:
                continue
        elif len(lines) == 2 and '-->' in lines[1]:
            idx = int(re.match(r'^\d+', lines[0]).group(0))
            cues.append(SubtitleCue(idx, lines[1], ""))

    return cues

def write_srt(file_path: Path, cues: List[SubtitleCue]):
    with open(file_path, 'w', encoding='utf-8') as f:
        for cue in cues:
            f.write(cue.to_srt() + "\n")


# =============================================================================
# MOTOR DE TRADUÇÃO EM LOTES (COM CHECKPOINT E RESUME)
# =============================================================================
class SubtitleTranslator:
    def __init__(
        self,
        client: OllamaClient,
        model: str = "gemma4:e4b",
        batch_size: int = 10,
        max_chars: int = 45,
        max_lines: int = 2,
        reformat: bool = True
    ):
        self.client = client
        self.model = model
        self.batch_size = batch_size
        self.formatter = SubtitleFormatter(max_chars=max_chars, max_lines=max_lines) if reformat else None

    def _get_checkpoint_path(self, input_file: Path) -> Path:
        return input_file.parent / f".{input_file.name}.pt_BR.checkpoint.json"

    def _load_checkpoint(self, checkpoint_path: Path) -> Dict[int, str]:
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()}
            except Exception as e:
                print_warning(f"Não foi possível carregar checkpoint: {e}")
        return {}

    def _save_checkpoint(self, checkpoint_path: Path, translated_dict: Dict[int, str]):
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(translated_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print_warning(f"Falha ao salvar checkpoint: {e}")

    def translate_file(
        self,
        input_file: Path,
        output_file: Path,
        resume: bool = True,
        dry_run_limit: Optional[int] = None
    ) -> bool:
        cues = parse_srt(input_file)
        if not cues:
            print_error(f"Nenhuma legenda válida encontrada em {input_file}")
            return False

        if dry_run_limit and dry_run_limit > 0:
            cues = cues[:dry_run_limit]
            print_info(f"Modo Dry-Run: limitando tradução às primeiras {len(cues)} legendas.")

        checkpoint_path = self._get_checkpoint_path(input_file)
        translated_map: Dict[int, str] = {}

        if resume:
            translated_map = self._load_checkpoint(checkpoint_path)
            if translated_map:
                print_info(f"Checkpoint recuperado: {len(translated_map)} legendas já traduzidas previamente.")

        total_cues = len(cues)
        cues_to_translate = [c for c in cues if c.index not in translated_map]
        
        print_info(f"Arquivo: {input_file.name}")
        print_info(f"Total de legendas: {total_cues} | A traduzir: {len(cues_to_translate)}")
        print_info(f"Modelo: {self.model} | Modo Ollama: {self.client.mode}")
        if self.formatter:
            print_info(f"Alinhamento: máx {self.formatter.max_chars} chars/linha, máx {self.formatter.max_lines} linhas.")

        batches = [cues_to_translate[i:i + self.batch_size] for i in range(0, len(cues_to_translate), self.batch_size)]
        
        start_time = time.time()
        try:
            for b_idx, batch in enumerate(batches, 1):
                batch_ids = [c.index for c in batch]
                items_payload = [{"id": c.index, "text": c.text} for c in batch]

                user_prompt = (
                    f"Traduza cada uma das legendas a seguir mantendo rigorosamente os IDs originais:\n"
                    f"{json.dumps(items_payload, ensure_ascii=False, indent=2)}"
                )

                success = False
                for attempt in range(1, 4):
                    try:
                        result = self.client.chat_json(
                            model=self.model,
                            system_prompt=BJJ_SYSTEM_PROMPT,
                            user_prompt=user_prompt,
                            timeout=120
                        )
                        if result and "translations" in result:
                            translations = result["translations"]
                            t_map = {t["id"]: t["text"] for t in translations if "id" in t and "text" in t}
                            
                            missing = set(batch_ids) - set(t_map.keys())
                            if not missing:
                                for cid, ctext in t_map.items():
                                    translated_map[cid] = ctext
                                success = True
                                break
                            else:
                                for cid, ctext in t_map.items():
                                    translated_map[cid] = ctext
                                items_payload = [item for item in items_payload if item["id"] in missing]
                                user_prompt = f"Traduza os itens faltantes mantendo os IDs:\n{json.dumps(items_payload, ensure_ascii=False, indent=2)}"
                    except Exception as e:
                        print_warning(f"Tentativa {attempt} falhou para o lote {b_idx}: {e}")
                        time.sleep(2)

                if not success:
                    print_error(f"Falha ao traduzir lote {b_idx} (IDs {batch_ids}). Mantendo texto original para evitar perda.")
                    for c in batch:
                        if c.index not in translated_map:
                            translated_map[c.index] = c.text

                self._save_checkpoint(checkpoint_path, translated_map)

                done_count = len(translated_map)
                pct = (done_count / total_cues) * 100
                elapsed = time.time() - start_time
                rate = done_count / elapsed if elapsed > 0 else 0.1
                eta_seconds = (total_cues - done_count) / rate if rate > 0 else 0
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds))

                sample_txt = translated_map.get(batch[0].index, "")
                sample_preview = (sample_txt[:50] + '...') if len(sample_txt) > 50 else sample_txt

                print(
                    f"\r{Colors.CYAN}[Lote {b_idx}/{len(batches)}]{Colors.RESET} "
                    f"{Colors.GREEN}{done_count}/{total_cues} ({pct:.1f}%){Colors.RESET} "
                    f"{Colors.YELLOW}ETA: {eta_str}{Colors.RESET} | "
                    f"{Colors.DIM}ID {batch[0].index}: \"{sample_preview}\"{Colors.RESET}",
                    end="",
                    flush=True
                )
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}[!] Tradução pausada pelo usuário (Ctrl+C).{Colors.RESET}")
            print(f"{Colors.GREEN}[✓] O progresso ({len(translated_map)}/{total_cues} legendas) está salvo no checkpoint!{Colors.RESET}")
            print(f"{Colors.CYAN}[i] Execute o script novamente para continuar de onde parou.{Colors.RESET}")
            return False

        print("\n")
        print_success("Tradução do modelo concluída! Formatando e alinhando linhas das legendas...")

        final_cues: List[SubtitleCue] = []
        for cue in cues:
            pt_text = translated_map.get(cue.index, cue.text)
            if self.formatter:
                formatted_text = self.formatter.format_text(pt_text)
            else:
                formatted_text = pt_text
            final_cues.append(SubtitleCue(cue.index, cue.timestamp, formatted_text))

        write_srt(output_file, final_cues)
        print_success(f"Legenda final salva com sucesso em: {Colors.BOLD}{output_file}{Colors.RESET}")

        if checkpoint_path.exists() and not dry_run_limit:
            try:
                checkpoint_path.unlink()
            except Exception:
                pass

        return True


# =============================================================================
# INTERFACE INTERATIVA E CLI
# =============================================================================
def interactive_menu(default_dir: str = "/home/joaquim/john") -> Dict[str, Any]:
    print_header("TRADUTOR DE VÍDEOS DE JIU-JITSU (BJJ) - INGLÊS PARA PT_BR")
    print(f"{Colors.BOLD}Configuração Interativa de Tradução:{Colors.RESET}\n")

    user_input = input(f"{Colors.CYAN}Caminho do arquivo SRT ou diretório [{default_dir}]: {Colors.RESET}").strip()
    if not user_input:
        user_input = default_dir

    input_path = Path(user_input).expanduser().resolve()
    while not input_path.exists():
        print_error(f"O caminho '{input_path}' não existe!")
        user_input = input(f"{Colors.CYAN}Digite um caminho válido: {Colors.RESET}").strip()
        input_path = Path(user_input).expanduser().resolve()

    selected_files: List[Path] = []
    if input_path.is_file():
        if input_path.suffix.lower() != '.srt':
            print_warning(f"O arquivo {input_path.name} não possui extensão .srt, mas será processado como SRT.")
        selected_files = [input_path]
    else:
        srt_files = sorted(list(input_path.glob("*.srt")))
        source_srts = [f for f in srt_files if not f.name.endswith(".pt_BR.srt")]

        if not source_srts:
            print_error(f"Nenhum arquivo .srt encontrado em {input_path}!")
            sys.exit(1)

        print(f"\n{Colors.BOLD}Arquivos SRT encontrados em {input_path}:{Colors.RESET}")
        print(f"  {Colors.GREEN}[0] Traduzir TODOS os arquivos ({len(source_srts)} arquivos){Colors.RESET}")
        for i, srt in enumerate(source_srts, 1):
            print(f"  [{i}] {srt.name}")

        choice = input(f"\n{Colors.CYAN}Selecione o número do arquivo a traduzir [0]: {Colors.RESET}").strip()
        if not choice or choice == "0":
            selected_files = source_srts
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(source_srts):
                    selected_files = [source_srts[idx]]
                else:
                    print_warning("Opção inválida, processando todos os arquivos.")
                    selected_files = source_srts
            except ValueError:
                selected_files = source_srts

    client = OllamaClient()
    available_models = client.list_models()
    default_model = "gemma4:e4b"
    if available_models and default_model not in available_models:
        default_model = available_models[0]

    print(f"\n{Colors.BOLD}Modelos detectados no Ollama:{Colors.RESET} {', '.join(available_models) if available_models else '(nenhum detectado automaticamente)'}")
    print(f"Modo de conexão detectado: {Colors.GREEN}{client.mode.upper()}{Colors.RESET}")
    
    model_input = input(f"{Colors.CYAN}Modelo Ollama a utilizar [{default_model}]: {Colors.RESET}").strip()
    model = model_input if model_input else default_model

    print(f"\n{Colors.BOLD}Alinhamento e Legibilidade Humana:{Colors.RESET}")
    print("Recomendado: 42 a 48 caracteres por linha (padrão Netflix / Broadcast)")
    chars_input = input(f"{Colors.CYAN}Limite máximo de caracteres por linha [45]: {Colors.RESET}").strip()
    try:
        max_chars = int(chars_input) if chars_input else 45
    except ValueError:
        max_chars = 45

    batch_input = input(f"{Colors.CYAN}Quantidade de legendas por requisição ao Ollama [10]: {Colors.RESET}").strip()
    try:
        batch_size = int(batch_input) if batch_input else 10
    except ValueError:
        batch_size = 10

    print(f"\n{Colors.BOLD}{Colors.GREEN}Resumo da Operação:{Colors.RESET}")
    print(f"  • Arquivos selecionados: {len(selected_files)}")
    for f in selected_files:
        print(f"    - {f.name}")
    print(f"  • Modelo Ollama: {model}")
    print(f"  • Modo de conexão: {client.mode}")
    print(f"  • Caracteres por linha: {max_chars} (máx 2 linhas)")
    print(f"  • Tamanho do lote: {batch_size}")

    confirm = input(f"\n{Colors.BOLD}{Colors.CYAN}Pressione Enter para iniciar a tradução (ou 'q' para cancelar): {Colors.RESET}").strip()
    if confirm.lower() == 'q':
        print("Operação cancelada.")
        sys.exit(0)

    return {
        "files": selected_files,
        "client": client,
        "model": model,
        "max_chars": max_chars,
        "batch_size": batch_size,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Tradutor de Legendas SRT de Jiu-Jitsu (BJJ) do Inglês para pt_BR com Ollama e alinhamento ergonômico."
    )
    parser.add_argument(
        "-i", "--input",
        help="Caminho do arquivo SRT ou pasta contendo arquivos SRT (padrão: /home/joaquim/john)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Caminho do arquivo de saída ou diretório de saída (padrão: [nome].pt_BR.srt)"
    )
    parser.add_argument(
        "-m", "--model",
        default="gemma4:e4b",
        help="Nome do modelo no Ollama (padrão: gemma4:e4b)"
    )
    parser.add_argument(
        "-u", "--ollama-url",
        default="http://localhost:11434",
        help="URL da API do Ollama (padrão: http://localhost:11434)"
    )
    parser.add_argument(
        "-c", "--container",
        default="open-webui",
        help="Nome do container Docker que roda o Ollama caso a porta não esteja exposta no host (padrão: open-webui)"
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=45,
        help="Limite de caracteres por linha para legibilidade perfeita (padrão: 45, faixa recomendada 42-48)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Número de legendas agrupadas por chamada ao modelo LLM (padrão: 10)"
    )
    parser.add_argument(
        "--no-reformat",
        action="store_true",
        help="Desativa a quebra sintática inteligente de linhas"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Não retoma de checkpoint anterior; recomeça do zero"
    )
    parser.add_argument(
        "--dry-run",
        type=int,
        metavar="N",
        help="Testa a tradução traduzindo apenas as primeiras N legendas"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Força a execução em modo interativo com menu no terminal"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1 or args.interactive:
        config = interactive_menu(default_dir="/home/joaquim/john")
        files = config["files"]
        client = config["client"]
        model = config["model"]
        max_chars = config["max_chars"]
        batch_size = config["batch_size"]
        reformat = True
        resume = True
        dry_run = None
    else:
        input_target = args.input or "/home/joaquim/john"
        input_path = Path(input_target).expanduser().resolve()

        if not input_path.exists():
            print_error(f"Caminho não encontrado: {input_path}")
            sys.exit(1)

        if input_path.is_file():
            files = [input_path]
        else:
            files = sorted([f for f in input_path.glob("*.srt") if not f.name.endswith(".pt_BR.srt")])
            if not files:
                print_error(f"Nenhum arquivo .srt encontrado em {input_path}")
                sys.exit(1)

        client = OllamaClient(base_url=args.ollama_url, docker_container=args.container)
        model = args.model
        max_chars = args.max_chars
        batch_size = args.batch_size
        reformat = not args.no_reformat
        resume = not args.no_resume
        dry_run = args.dry_run

    if client.mode == "unknown":
        print_error("Não foi possível conectar ao Ollama nem via HTTP (http://localhost:11434) nem via Docker container 'open-webui'.")
        print_info("Certifique-se de que o container 'open-webui' está rodando (docker ps) ou que o serviço Ollama está ativo.")
        sys.exit(1)

    translator = SubtitleTranslator(
        client=client,
        model=model,
        batch_size=batch_size,
        max_chars=max_chars,
        max_lines=2,
        reformat=reformat
    )

    print_header(f"INICIANDO TRADUÇÃO DE {len(files)} ARQUIVO(S)")

    for idx, srt_file in enumerate(files, 1):
        print(f"\n{Colors.BOLD}{Colors.YELLOW}[{idx}/{len(files)}] Processando: {srt_file.name}{Colors.RESET}")
        
        if args.output and len(files) == 1 and not Path(args.output).is_dir():
            output_file = Path(args.output).expanduser().resolve()
        elif args.output and Path(args.output).is_dir():
            output_file = Path(args.output).expanduser().resolve() / f"{srt_file.stem}.pt_BR.srt"
        else:
            output_file = srt_file.parent / f"{srt_file.stem}.pt_BR.srt"

        success = translator.translate_file(
            input_file=srt_file,
            output_file=output_file,
            resume=resume,
            dry_run_limit=dry_run
        )
        if not success:
            print_error(f"Erro ao traduzir {srt_file.name}")

    print_header("TODAS AS OPERAÇÕES CONCLUÍDAS COM SUCESSO!")

if __name__ == "__main__":
    main()
