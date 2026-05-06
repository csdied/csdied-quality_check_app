"""
Detectores de qualidade para respostas de pesquisa de camisinhas/lubrificantes.
Cada detector retorna flags por respondente.
"""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

import pandas as pd


# Marcas que NÃO são camisinha nem lubrificante íntimo - sinal forte de fraude
BLACKLIST_BRANDS = {
    # óleos automotivos
    "bardahl", "castrol", "castroll", "mobil", "mobil 1", "shell",
    "ipiranga", "lubrax", "valvoline", "quaker", "quaker state",
    "pennzoil", "penzoil", "ypf", "pemex", "total", "elf", "agip",
    "repsol", "gulf", "liqui moly", "liqui", "motul", "akron",
    "wd-40", "wd40", "wd 40", "3 en 1", "3en1", "3 in 1",
}

# Marcas SEED conhecidas internacionalmente (camisinha + lubrificante íntimo).
# Garantem whitelist mesmo se aparecerem pouco na base — evita falsos positivos
# tipo Astroglide, Sliquid, Pjur, Vagisil que são marcas reais mas raras.
KNOWN_VALID_BRANDS = {
    # camisinhas
    "sico", "prudence", "trojan", "durex", "playboy", "play boy", "skyn",
    "m force", "mforce", "m-force", "alfa", "balam", "vive", "trust",
    "gladiator", "do it lovely", "simi", "simi condon", "simi condón",
    "lifestyles", "one", "lelo", "condones m",
    # lubrificantes íntimos
    "k-y", "ky", "k y", "ky jelly", "k-y jelly", "benzal", "lua",
    "lov lub", "sensy lub", "lube tube", "naturals", "lubifem",
    "astroglide", "sliquid", "uberlube", "pjur", "vagisil", "isdin",
    "aloe cadabra", "pasante", "wet", "id glide", "good clean love",
    "sutil", "lov", "ego", "meibi", "cumlaude",
}

# Lugares e instituições mencionados como "marca" - suspeita média
NON_BRAND_PLACES = {
    "imss", "issste", "del seguro", "del imms", "centro de salud",
    "farmacia similar", "farmacia similares", "farmacias similares",
    "doctor simi", "dr simi", "doctorsimi", "del simi",
    "bienestar", "bienestar social", "del bienestar",
    "bodega aurrera", "aurrera", "soriana", "walmart", "chedraui",
    "del ahorro", "farmacia del ahorro",
}

# Respostas legítimas de "não conheço/não lembro" - não são fraude
NON_ANSWERS = {
    "no se", "no sé", "nose", "no recuerdo", "no", "ninguna", "ninguno",
    "na", "n/a", "nada", "no aplica", "ns", "nr", "ns/nr",
    "0", "-", ".", "x",
}

# Substâncias caseiras usadas como lubrificante - resposta legítima
HOMEMADE_LUBES = {
    "vaselina", "aceite", "aceite de bebe", "aceite de bebé",
    "aceites de bebé", "aceite de coco", "coco", "aceite de oliva",
    "aceite de almendra", "saliva", "agua", "crema", "piña y coco",
    "coco bliss",
}


def normalize(text):
    """Normaliza texto: minúsculo, sem acento, sem pontuação extra."""
    if pd.isna(text):
        return ""
    s = str(text).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_gibberish(text):
    """
    Detecta texto sem sentido. Heurísticas:
    - Repetição alta da mesma letra (gggg, kkkk)
    - Sequência de consoantes sem vogal (bbv, fbfnf, dmmrmrm)
    - Strings curtas com baixa proporção de vogais
    - Caracteres random tipo bdkd, cdddd, hsjaaj
    """
    s = normalize(text)
    if not s or len(s) < 3:
        return False  # muito curto, trata por outra regra

    if s in NON_ANSWERS or s in HOMEMADE_LUBES:
        return False

    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False

    # Repetição da mesma letra (4+ iguais em sequência)
    if re.search(r"(.)\1{3,}", s):
        return True

    # Proporção de vogais muito baixa em texto puramente alfabético
    vowels = sum(1 for c in letters if c in "aeiouáéíóú")
    vowel_ratio = vowels / len(letters)
    if len(letters) >= 4 and vowel_ratio < 0.15:
        return True

    # Sequências de 5+ consoantes diferentes (ex: bbsv, dnfn, exmwn)
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", s):
        return True

    # Padrão de teclado random: muitas trocas sem formar palavra.
    # Apenas se for >= 4 letras, não atinge whitelist e tem padrão repetitivo
    if len(letters) >= 4 and vowel_ratio < 0.20:
        unique = len(set(letters))
        # bbsb (3 únicos, 4 letras), gggg, fbfnf - repetição alta
        if unique <= 3:
            return True

    return False


def is_only_symbols(text):
    """Resposta que é só pontuação ou símbolos: '*', ':(', '????', '.'"""
    s = str(text).strip() if not pd.isna(text) else ""
    if not s:
        return False
    return not any(c.isalnum() for c in s)


def fuzzy_similar(a, b, threshold=0.82):
    """Compara dois textos com tolerância a typo."""
    return SequenceMatcher(None, a, b).ratio() >= threshold


def build_brand_whitelist(all_brand_responses, min_count=3, min_pct=0.005):
    """
    Aprende as marcas válidas das próprias respostas:
    marcas que aparecem >= min_count vezes E >= min_pct do total
    são consideradas "plausíveis". Sempre inclui as marcas seed conhecidas.
    """
    normalized = [normalize(r) for r in all_brand_responses if not pd.isna(r)]
    normalized = [r for r in normalized if r and r not in NON_ANSWERS]
    counter = Counter(normalized)
    total = len(normalized)
    threshold = max(min_count, int(total * min_pct))
    learned = {b for b, n in counter.items() if n >= threshold}
    # Mescla com seed: marcas internacionalmente conhecidas sempre valem
    whitelist = learned | KNOWN_VALID_BRANDS
    return whitelist, counter, total, threshold


def classify_brand_response(text, whitelist):
    """
    Classifica uma resposta de marca.
    Retorna: (categoria, motivo)
    Categorias: ok, non_answer, homemade, blacklist_oil, place_not_brand,
                gibberish, only_symbols, suspicious_rare
    """
    if pd.isna(text) or str(text).strip() == "":
        return ("empty", "")

    raw = str(text).strip()
    s = normalize(raw)

    if is_only_symbols(raw):
        return ("only_symbols", f"Sólo símbolos: '{raw[:20]}'")

    if s in NON_ANSWERS:
        return ("non_answer", "")

    if s in HOMEMADE_LUBES:
        return ("homemade", "")

    # Antes de tudo: é uma marca conhecida (seed)? Trata como ok.
    for known in KNOWN_VALID_BRANDS:
        if s == known or fuzzy_similar(s, known, 0.85):
            return ("ok", "")
        if known in s and len(known) >= 3:
            return ("ok", "")

    # Lista negra: marca de óleo automotivo
    for bad in BLACKLIST_BRANDS:
        if s == bad:
            return ("blacklist_oil", f"Marca de aceite automotriz: '{raw}'")
        if re.search(rf"\b{re.escape(bad)}\b", s):
            return ("blacklist_oil", f"Marca de aceite automotriz: '{raw}'")
        if fuzzy_similar(s, bad, 0.90):
            return ("blacklist_oil", f"Marca de aceite automotriz: '{raw}'")

    # Lugares mencionados como marca
    for place in NON_BRAND_PLACES:
        if place in s:
            return ("place_not_brand", f"Lugar/institución, no es marca: '{raw}'")

    if is_gibberish(raw):
        return ("gibberish", f"Texto sin sentido: '{raw}'")

    if len(s) <= 2 and s not in {"ky", "m"}:
        return ("too_short", f"Respuesta muy corta: '{raw}'")

    # Match com whitelist
    if s in whitelist:
        return ("ok", "")
    for valid in whitelist:
        if fuzzy_similar(s, valid, 0.82):
            return ("ok", "")
        if valid in s and len(valid) >= 4:
            return ("ok", "")

    return ("suspicious_rare", f"Marca no reconocida: '{raw}'")


def detect_duplicate_text_across_questions(row, brand_cols):
    """Mesma resposta colada em 4+ campos abertos = copy-paste preguiçoso."""
    answers = [normalize(row[c]) for c in brand_cols]
    answers = [a for a in answers if a and a not in NON_ANSWERS]
    if len(answers) < 4:
        return False
    counts = Counter(answers)
    most_common, n = counts.most_common(1)[0]
    return n >= 4


# ---------- ANÁLISE PRINCIPAL ----------

def analyze(df_raw, time_threshold_min=8, brand_col_indices=None):
    """
    Roda todos os detectores e retorna um DataFrame com flags por respondente.
    """
    # Pula linha de subheader (primeira linha do QuestionPro)
    if pd.isna(df_raw.iloc[0]['ID de respuesta']):
        df = df_raw.iloc[1:].reset_index(drop=True).copy()
    else:
        df = df_raw.copy()

    # Default: colunas de marca aberta no formato QuestionPro
    if brand_col_indices is None:
        brand_col_indices = [63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74]
    brand_col_indices = [i for i in brand_col_indices if i < len(df.columns)]
    brand_cols = [df.columns[i] for i in brand_col_indices]

    # Aprende whitelist das próprias respostas
    all_brand_responses = []
    for c in brand_cols:
        all_brand_responses.extend(df[c].tolist())
    whitelist, counter, total_mentions, threshold = build_brand_whitelist(
        all_brand_responses
    )

    results = []
    time_threshold_sec = time_threshold_min * 60

    # Pré-calcula IPs duplicados
    ip_counts = df['Dirección IP'].value_counts()
    duplicate_ips = set(ip_counts[ip_counts > 1].index)

    for idx, row in df.iterrows():
        flags = {
            'ID de respuesta': row.get('ID de respuesta', ''),
            'Dirección IP': row.get('Dirección IP', ''),
            'Tiempo (seg)': row.get('Tiempo necesario para completar (segundos)', None),
        }

        # Tempo em minutos
        t_sec = flags['Tiempo (seg)']
        try:
            t_min = float(t_sec) / 60 if pd.notna(t_sec) else None
        except (ValueError, TypeError):
            t_min = None
        flags['Tiempo (min)'] = round(t_min, 1) if t_min else None

        # Detector 1: IP duplicado
        flags['flag_ip_duplicado'] = flags['Dirección IP'] in duplicate_ips

        # Detector 2: tempo curto
        flags['flag_tempo_curto'] = bool(t_min and t_min < time_threshold_min)

        # Detector 3: análise das respostas abertas de marca
        bad_brands = []
        gibberish_count = 0
        oil_count = 0
        place_count = 0
        rare_count = 0
        symbol_count = 0
        short_count = 0
        valid_count = 0

        for c in brand_cols:
            cat, motivo = classify_brand_response(row[c], whitelist)
            if cat == "blacklist_oil":
                oil_count += 1
                bad_brands.append(motivo)
            elif cat == "gibberish":
                gibberish_count += 1
                bad_brands.append(motivo)
            elif cat == "place_not_brand":
                place_count += 1
                bad_brands.append(motivo)
            elif cat == "only_symbols":
                symbol_count += 1
                bad_brands.append(motivo)
            elif cat == "too_short":
                short_count += 1
            elif cat == "suspicious_rare":
                rare_count += 1
                bad_brands.append(motivo)
            elif cat == "ok":
                valid_count += 1

        flags['flag_marca_oleo'] = oil_count > 0
        flags['flag_gibberish'] = gibberish_count > 0
        flags['flag_lugar_nao_marca'] = place_count > 0
        flags['flag_so_simbolos'] = symbol_count > 0
        flags['flag_muitas_marcas_raras'] = rare_count >= 3  # 3+ marcas estranhas

        # Detector 4: copy-paste em vários campos
        flags['flag_copy_paste'] = detect_duplicate_text_across_questions(
            row, brand_cols
        )

        # Score ponderado
        score = 0
        score += 30 if flags['flag_marca_oleo'] else 0
        score += 25 if flags['flag_gibberish'] else 0
        score += 20 if flags['flag_so_simbolos'] else 0
        score += 25 if flags['flag_copy_paste'] else 0
        score += 15 if flags['flag_lugar_nao_marca'] else 0
        score += 15 if flags['flag_muitas_marcas_raras'] else 0
        score += 15 if flags['flag_tempo_curto'] else 0
        score += 10 if flags['flag_ip_duplicado'] else 0
        flags['score_suspeita'] = score

        # Classificação final
        if score >= 40:
            flags['classificacao'] = '🔴 Alta sospecha'
        elif score >= 20:
            flags['classificacao'] = '🟡 Revisar'
        elif score > 0:
            flags['classificacao'] = '🟢 OK con observaciones'
        else:
            flags['classificacao'] = '✅ Limpio'

        flags['motivos'] = ' | '.join(bad_brands[:5])  # limita pra não ficar gigante
        results.append(flags)

    return pd.DataFrame(results), {
        'whitelist': sorted(whitelist),
        'whitelist_threshold': threshold,
        'total_marcas_unicas': len(counter),
        'total_mencoes': total_mentions,
    }
