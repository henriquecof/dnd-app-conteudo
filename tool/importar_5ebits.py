#!/usr/bin/env python3
"""Gera pacotes do SRD 5.1 a partir do 5e-bits/5e-database.

Uso (a partir da raiz do repositório):  python3 tool/importar_5ebits.py .

Fonte: https://github.com/5e-bits/5e-database (código/dados MIT), com conteúdo do
System Reference Document 5.1 da Wizards of the Coast (CC-BY-4.0).

Pacotes gerados em pacotes/:
  srd-magias, srd-criaturas, srd-itens, srd-itens-magicos  (en)
  srd-talentos, srd-antecedentes, srd-condicoes            (pt-BR quando existir, senão en)

Só usa a biblioteca padrão.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://raw.githubusercontent.com/5e-bits/5e-database/main/src/2014/{lang}/5e-SRD-{nome}.json"

LICENCA = (
    "Contém material do System Reference Document 5.1 da Wizards of the Coast LLC "
    "(CC-BY-4.0, https://creativecommons.org/licenses/by/4.0/legalcode). "
    "Dados estruturados de 5e-bits/5e-database (MIT)."
)
FONTE = "System Reference Document 5.1 (Wizards of the Coast), via 5e-bits/5e-database"

# Ids do pacote embutido srd-5.1 que não seguem o index do 5e-bits.
ALIAS_ID = {
    "rations-1-day": "rations",
    "rope-hempen-50-feet": "rope_hempen",
    "crossbow-light": "light_crossbow",
    "crossbow-bolt": "bolt",
    "potion-of-healing-common": "potion_healing",
}


# ---------------------------------------------------------------- utilidades

def baixar(nome, lang):
    url = BASE.format(lang=lang, nome=nome)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def baixar_preferindo_pt(nome):
    dados = baixar(nome, "pt-BR")
    if dados:
        return dados, "pt-BR"
    return baixar(nome, "en"), "en"


def ident(index):
    if index in ALIAS_ID:
        return ALIAS_ID[index]
    i = re.sub(r"[^a-z0-9]+", "_", index.lower()).strip("_")
    return i


def num(x):
    """Formata número: inteiro sem casas, senão uma casa decimal."""
    x = round(x, 2)
    if x == int(x):
        return str(int(x))
    return ("%.2f" % x).rstrip("0").rstrip(".")


def pes_para_m(pes):
    return pes * 0.3  # 5 pés = 1,5 m


def _n(s):
    return float(s.replace(",", ""))


def metrificar(texto, sep="."):
    """Converte distâncias em pés no texto para metros (1,5 m a cada 5 pés)."""
    if not texto:
        return texto

    def fmt(pes):
        s = num(pes_para_m(pes))
        return s.replace(".", sep)

    # "80/320 ft." ou "80/320 feet"
    def faixa(m):
        a, b = m.group(1), m.group(2)
        return "%s/%s m%s" % (fmt(_n(a)), fmt(_n(b)), _ponto(m))

    texto = re.sub(r"(\d[\d,]*)/(\d[\d,]*)\s*(feet|foot|ft\.?)(?![a-z])", faixa, texto)

    # "20-foot radius" -> "6-meter radius"
    texto = re.sub(r"(\d[\d,]*(?:\.\d+)?)-(?:foot|feet)\b",
                   lambda m: "%s-meter" % fmt(_n(m.group(1))), texto)

    # "30 feet", "30 ft.", "1 foot"
    def simples(m):
        return "%s m%s" % (fmt(_n(m.group(1))), _ponto(m))

    texto = re.sub(r"(\d[\d,]*(?:\.\d+)?)\s*(feet|foot|ft\.?)(?![a-z])", simples, texto)

    # "N pés" em texto pt-BR (raro)
    texto = re.sub(r"(\d[\d,]*)\s*pés\b", lambda m: "%s m" % fmt(_n(m.group(1))), texto)
    return texto


def _ponto(m):
    """'ft.' abrevia; mantém o ponto só quando ele também encerra a frase."""
    if not m.group(0).endswith("."):
        return ""
    resto = m.string[m.end():].lstrip(" ")
    if resto == "" or resto[:1].isupper() or resto[:1] == "\n":
        return "."
    return ""


def juntar(desc, sep="\n\n"):
    if desc is None:
        return ""
    if isinstance(desc, str):
        return desc
    return sep.join(d for d in desc if d)


def pacote(pid, nome, descricao, idioma, categoria, publico, lista):
    lista = sorted(lista, key=lambda x: x["id"])
    ids = [x["id"] for x in lista]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit("ids duplicados em %s: %s" % (pid, sorted(dup)))
    for i in ids:
        if not re.match(r"^[a-z0-9_]+$", i):
            raise SystemExit("id inválido em %s: %s" % (pid, i))
    return {
        "formato": 1,
        "id": pid,
        "nome": nome,
        "versao": "1.0.0",
        "descricao": descricao,
        "licenca": LICENCA,
        "idioma": idioma,
        "categoria": categoria,
        "publico": publico,
        "fonte": FONTE,
        "depende_de": [],
        "complementa": ["srd-5.1"],
        categoria: lista,
    }


# ---------------------------------------------------------------- magias

ESCOLAS = {
    "abjuration": "abjuracao", "divination": "adivinhacao", "conjuration": "conjuracao",
    "enchantment": "encantamento", "evocation": "evocacao", "illusion": "ilusao",
    "necromancy": "necromancia", "transmutation": "transmutacao",
}


def conv_magia(s):
    texto = juntar(s.get("desc"))
    if s.get("higher_level"):
        texto += "\n\n**At Higher Levels.** " + juntar(s["higher_level"], " ")
    m = {
        "id": ident(s["index"]),
        "nome": s["name"],
        "nivel": s["level"],
        "escola": ESCOLAS[s["school"]["index"]],
        "tempo": s["casting_time"],
        "alcance": metrificar(s["range"]),
        "componentes": s.get("components", []),
        "material": metrificar(s.get("material")),
        "duracao": s["duration"],
        "concentracao": bool(s.get("concentration")),
        "ritual": bool(s.get("ritual")),
        "listas": sorted("lista:" + c["index"] for c in s.get("classes", [])),
        "texto": metrificar(texto),
    }
    return m


# ---------------------------------------------------------------- criaturas

TAMANHOS = {"Tiny": "miudo", "Small": "pequeno", "Medium": "medio", "Large": "grande",
            "Huge": "enorme", "Gargantuan": "imenso"}
ATR = [("strength", "for"), ("dexterity", "des"), ("constitution", "con"),
       ("intelligence", "int"), ("wisdom", "sab"), ("charisma", "car")]
ATR_ABREV = {"str": "for", "dex": "des", "con": "con", "int": "int", "wis": "sab", "cha": "car"}
PERICIAS = {
    "acrobatics": "acrobacia", "animal-handling": "adestrar_animais", "arcana": "arcanismo",
    "athletics": "atletismo", "performance": "atuacao", "deception": "enganacao",
    "stealth": "furtividade", "history": "historia", "intimidation": "intimidacao",
    "insight": "intuicao", "investigation": "investigacao", "medicine": "medicina",
    "nature": "natureza", "perception": "percepcao", "persuasion": "persuasao",
    "sleight-of-hand": "prestidigitacao", "religion": "religiao", "survival": "sobrevivencia",
}
DESLOC = {"walk": "andar", "fly": "voo", "swim": "natacao", "climb": "escalada", "burrow": "escavacao"}
ND = {0.125: "1/8", 0.25: "1/4", 0.5: "1/2"}


def pes_de(valor):
    m = re.match(r"\s*([\d,]+)\s*ft", str(valor))
    return _n(m.group(1)) if m else None


def ca_detalhe(entrada):
    t = entrada["type"]
    if t == "armor":
        return ", ".join(a["name"].lower() for a in entrada.get("armor", []))
    if t == "natural":
        return "natural armor"
    if t == "spell":
        return "with " + entrada["spell"]["name"].lower()
    if t == "condition":
        return "while " + entrada["condition"]["name"].lower()
    return ""


def sufixo_uso(nome, uso):
    if not uso or "(" in nome:
        return nome
    t = uso.get("type")
    if t == "recharge on roll":
        mn = uso.get("min_value", 6)
        r = "Recharge %d" % mn if mn >= 6 else "Recharge %d-6" % mn
        return "%s (%s)" % (nome, r)
    if t == "per day":
        return "%s (%d/Day)" % (nome, uso.get("times", 1))
    if t == "recharge after rest":
        rt = uso.get("rest_types", [])
        if rt == ["long"]:
            return "%s (Recharges after a Long Rest)" % nome
        return "%s (Recharges after a Short or Long Rest)" % nome
    return nome


def blocos(lista):
    return [{"nome": sufixo_uso(a["name"], a.get("usage")), "texto": metrificar(a.get("desc", ""))}
            for a in (lista or [])]


def conv_criatura(c):
    tipo = c["type"] + (" (%s)" % c["subtype"] if c.get("subtype") else "")
    desl = {v: 0 for v in DESLOC.values()}
    pairar = False
    for k, v in c.get("speed", {}).items():
        if k == "hover":
            pairar = bool(v)
            continue
        if k in DESLOC:
            p = pes_de(v)
            if p is not None:
                desl[DESLOC[k]] = float(num(pes_para_m(p))) if p % 10 else int(pes_para_m(p))
    if pairar:
        desl["pairar"] = True

    sentidos = []
    for k, v in c.get("senses", {}).items():
        if k == "passive_perception":
            continue
        rotulo = k.replace("_", " ")
        sentidos.append("%s %s" % (rotulo, metrificar(str(v)).rstrip(".")))
    sentidos.append("passive Perception %s" % c["senses"].get("passive_perception", 10))

    salv, peric = {}, {}
    for p in c.get("proficiencies", []):
        idx = p["proficiency"]["index"]
        if idx.startswith("saving-throw-"):
            salv[ATR_ABREV[idx[len("saving-throw-"):]]] = p["value"]
        elif idx.startswith("skill-"):
            peric[PERICIAS[idx[len("skill-"):]]] = p["value"]

    cas = c.get("armor_class", [])
    ca = cas[0]["value"] if cas else 10
    det = ca_detalhe(cas[0]) if cas else ""
    extras = ["%d %s" % (e["value"], ca_detalhe(e)) for e in cas[1:]]
    if extras:
        det = ", ".join(x for x in [det] + extras if x)

    cr = c.get("challenge_rating", 0)
    out = {
        "id": ident(c["index"]),
        "nome": c["name"],
        "tamanho": TAMANHOS[c["size"]],
        "tipo": tipo,
        "alinhamento": c.get("alignment", ""),
        "ca": ca,
        "ca_detalhe": det,
        "pv": c.get("hit_points"),
        "dados_vida": c.get("hit_points_roll") or c.get("hit_dice"),
        "deslocamento": desl,
        "atributos": {pt: c[en] for en, pt in ATR},
        "salvaguardas": salv,
        "pericias": peric,
        "resistencias": "; ".join(c.get("damage_resistances", [])),
        "imunidades": "; ".join(c.get("damage_immunities", [])),
        "vulnerabilidades": "; ".join(c.get("damage_vulnerabilities", [])),
        "imunidade_condicoes": ", ".join(x["name"].lower() for x in c.get("condition_immunities", [])),
        "sentidos": ", ".join(sentidos),
        "idiomas": metrificar(c.get("languages", "")),
        "nd": ND.get(cr, num(cr)),
        "xp": c.get("xp", 0),
        "bonus_proficiencia": c.get("proficiency_bonus"),
        "tracos": blocos(c.get("special_abilities")),
        "acoes": blocos(c.get("actions")),
        "reacoes": blocos(c.get("reactions")),
        "acoes_lendarias": blocos(c.get("legendary_actions")),
    }
    # campos vazios podem ser omitidos
    return {k: v for k, v in out.items() if v not in ("", [], {}, None)}


# ---------------------------------------------------------------- itens

MOEDA = {"cp": "pc", "sp": "pp", "ep": "pe", "gp": "po", "pp": "pl"}
MUNICAO = {"arrow": "flecha", "crossbow-bolt": "virote", "sling-bullet": "bala",
           "blowgun-needle": "agulha"}
USA_MUNICAO = {"longbow": "flecha", "shortbow": "flecha", "crossbow-light": "virote",
               "crossbow-heavy": "virote", "crossbow-hand": "virote", "sling": "bala",
               "blowgun": "agulha"}
# Capacidades da tabela "Container Capacity" do SRD 5.1.
RECIPIENTES = {
    "backpack": {"peso": 30},
    "barrel": {"peso": None},
    "basket": {"peso": 40},
    "chest": {"peso": 300},
    "pouch": {"peso": 6},
    "sack": {"peso": 30},
    "quiver": {"unidades": 20, "aceita": ["municao"]},
    "case-crossbow-bolt": {"unidades": 20, "aceita": ["municao"]},
    "case-map-or-scroll": {"unidades": 10},
}
CONSUMIVEIS = {"rations-1-day", "torch", "candle", "oil-flask", "acid-vial", "alchemists-fire-flask",
               "antitoxin-vial", "holy-water-flask", "poison-basic-vial", "chalk-1-piece",
               "paper-one-sheet", "parchment-one-sheet", "ink-1-ounce-bottle", "block-of-incense",
               "sealing-wax", "soap", "perfume-vial", "little-bag-of-sand"}
DURACAO_MIN = {"torch": 60, "candle": 60}
FOCO_CATS = {"arcane-foci", "druidic-foci", "holy-symbols"}


def custo(c, lote=None):
    if not c or not c.get("quantity"):
        return None
    out = {"valor": c["quantity"], "moeda": MOEDA[c["unit"]]}
    if lote and lote > 1:
        out["lote"] = lote
    return out


def tipo_item(e):
    cat = e["equipment_category"]["index"]
    gear = (e.get("gear_category") or {}).get("index")
    idx = e["index"]
    if cat == "weapon":
        return "arma"
    if cat == "armor":
        return "escudo" if e.get("armor_category") == "Shield" else "armadura"
    if cat == "tools":
        return "ferramenta"
    if gear == "ammunition":
        return "municao"
    if gear in FOCO_CATS or idx == "component-pouch":
        return "foco"
    if gear == "kits" or idx == "tinderbox":
        return "ferramenta"
    if idx in RECIPIENTES:
        return "recipiente"
    if idx in CONSUMIVEIS:
        return "consumivel"
    return "equipamento"


def texto_arma(e):
    partes = []
    d = e.get("damage")
    if d:
        partes.append("%s %s" % (d["damage_dice"], d["damage_type"]["name"].lower()))
    props = []
    for p in e.get("properties", []):
        nome = p["name"]
        if p["index"] in ("ammunition", "thrown"):
            r = e.get("range", {}) if p["index"] == "ammunition" else e.get("throw_range", {})
            if r.get("normal") and r.get("long"):
                nome += " (range %s/%s m)" % (num(pes_para_m(r["normal"])), num(pes_para_m(r["long"])))
        if p["index"] == "versatile" and e.get("two_handed_damage"):
            nome += " (%s)" % e["two_handed_damage"]["damage_dice"]
        props.append(nome)
    linha = "; ".join(x for x in [", ".join(partes), ", ".join(props)] if x)
    cab = "%s weapon" % e.get("category_range", "").lower() if e.get("category_range") else ""
    return ". ".join(x for x in [cab[:1].upper() + cab[1:] if cab else "", linha] if x) + "."


def texto_armadura(e):
    ac = e.get("armor_class", {})
    if e.get("armor_category") == "Shield":
        s = "+%d AC" % ac.get("base", 2)
    else:
        s = "AC %d" % ac.get("base", 10)
        if ac.get("dex_bonus"):
            s += " + Dex modifier" + (" (max %d)" % ac["max_bonus"] if ac.get("max_bonus") else "")
    partes = ["%s armor" % e["armor_category"] if e.get("armor_category") != "Shield" else "Shield", s]
    if e.get("str_minimum"):
        partes.append("Strength %d" % e["str_minimum"])
    if e.get("stealth_disadvantage"):
        partes.append("disadvantage on Stealth checks")
    return "; ".join(partes) + "."


def conv_item(e, nomes):
    idx = e["index"]
    tipo = tipo_item(e)
    qtd = e.get("quantity") or 1
    out = {"id": ident(idx), "nome": metrificar(e["name"]), "tipo": tipo}
    if tipo == "municao" and idx in MUNICAO:
        out["municao"] = MUNICAO[idx]
    if tipo == "arma" and idx in USA_MUNICAO:
        out["usa_municao"] = USA_MUNICAO[idx]
    if e.get("weight") is not None:
        out["peso"] = round(e["weight"] / qtd, 4) if qtd > 1 else e["weight"]
    c = custo(e.get("cost"), qtd)
    if c:
        out["custo"] = c
    if tipo == "recipiente":
        cap = {k: v for k, v in RECIPIENTES[idx].items() if v is not None}
        if cap:
            out["capacidade"] = cap
    if idx in DURACAO_MIN:
        out["duracao_min"] = DURACAO_MIN[idx]

    textos = []
    if tipo == "arma":
        textos.append(texto_arma(e))
    elif tipo in ("armadura", "escudo"):
        textos.append(texto_armadura(e))
    if e.get("tool_category"):
        textos.append(e["tool_category"] + ".")
    if e.get("vehicle_category"):
        textos.append(e["vehicle_category"] + ".")
    sp = e.get("speed")
    if sp:
        if sp.get("unit") == "ft/round":
            textos.append("Speed %s m." % num(pes_para_m(sp["quantity"])))
        else:
            textos.append("Speed %s %s." % (num(sp["quantity"]), sp.get("unit", "")))
    if isinstance(e.get("capacity"), str):
        textos.append("Carrying capacity %s" % e["capacity"])
    if e.get("contents"):
        itens = ["%s%s" % (nomes.get(x["item"]["index"], x["item"]["name"]),
                           " (%d)" % x["quantity"] if x["quantity"] > 1 else "")
                 for x in e["contents"]]
        textos.append("Includes: " + ", ".join(itens) + ".")
    if qtd > 1:
        textos.append("Sold in bundles of %d." % qtd)
    textos += [juntar(e.get("desc"))] + [juntar(e.get("special"))]
    t = metrificar("\n\n".join(x for x in textos if x))
    if t:
        out["texto"] = t
    return out


RARIDADE = {"Common": "comum", "Uncommon": "incomum", "Rare": "raro", "Very Rare": "muito_raro",
            "Legendary": "lendario", "Artifact": "artefato", "Varies": "variada"}


def conv_item_magico(e):
    desc = e.get("desc") or []
    out = {
        "id": ident(e["index"]),
        "nome": metrificar(e["name"]),
        "tipo": "magico",
        "raridade": RARIDADE[e["rarity"]["name"]],
    }
    if desc and "requires attunement" in desc[0].lower():
        out["sintonizacao"] = True
    out["texto"] = metrificar(juntar(desc))
    return out


# ---------------------------------------------------------------- talentos / antecedentes / condições

def conv_talento(f, idioma):
    pre = []
    for p in f.get("prerequisites", []):
        if "ability_score" in p:
            pre.append("%s %s" % (p["ability_score"]["name"], p.get("minimum_score", "")))
        elif "name" in p:
            pre.append(p["name"])
    sep = "\n" if any(d.startswith("- ") for d in f.get("desc", [])) else "\n\n"
    out = {"id": ident(f["index"]), "nome": f["name"], "pre_requisito": ", ".join(pre),
           "texto": metrificar(juntar(f.get("desc"), sep), "," if idioma == "pt-BR" else ".")}
    return out


def conv_antecedente(b, idioma):
    pericias, ferramentas = [], []
    for p in b.get("starting_proficiencies", []):
        idx = p["index"]
        if idx.startswith("skill-") and idx[6:] in PERICIAS:
            pericias.append(PERICIAS[idx[6:]])
        else:
            ferramentas.append(ident(idx))
    lo = b.get("language_options") or {}
    feat = b.get("feature") or {}
    sep = "," if idioma == "pt-BR" else "."
    return {
        "id": ident(b["index"]),
        "nome": b["name"],
        "pericias": pericias,
        "idiomas_escolha": lo.get("choose", 0),
        "ferramentas": ferramentas,
        "caracteristica": {"nome": feat.get("name", ""),
                           "texto": metrificar(juntar(feat.get("desc")), sep)},
    }


def conv_condicao(c, idioma):
    desc = c.get("desc") or []
    sep = "\n" if any(d.startswith("- ") or d.startswith("|") for d in desc) else "\n\n"
    return {"id": ident(c["index"]), "nome": c["name"],
            "texto": metrificar(juntar(desc, sep), "," if idioma == "pt-BR" else ".")}


# ---------------------------------------------------------------- principal

def main():
    raiz = sys.argv[1] if len(sys.argv) > 1 else "."
    destino = os.path.join(raiz, "pacotes")
    os.makedirs(destino, exist_ok=True)
    pub_jm = ["jogador", "mestre"]
    pacotes = []

    spells = baixar("Spells", "en")
    pacotes.append(pacote("srd-magias", "SRD 5.1 — Magias",
                          "Todas as magias do System Reference Document 5.1 (em inglês).",
                          "en", "magias", pub_jm, [conv_magia(s) for s in spells]))

    monsters = baixar("Monsters", "en")
    pacotes.append(pacote("srd-criaturas", "SRD 5.1 — Criaturas",
                          "Todas as criaturas do System Reference Document 5.1 (em inglês).",
                          "en", "criaturas", ["mestre"], [conv_criatura(c) for c in monsters]))

    equip = baixar("Equipment", "en")
    nomes = {e["index"]: e["name"] for e in equip}
    pacotes.append(pacote("srd-itens", "SRD 5.1 — Equipamento",
                          "Armas, armaduras, equipamento de aventura, ferramentas, montarias e "
                          "veículos do System Reference Document 5.1 (em inglês).",
                          "en", "itens", pub_jm, [conv_item(e, nomes) for e in equip]))

    magic = baixar("Magic-Items", "en")
    pacotes.append(pacote("srd-itens-magicos", "SRD 5.1 — Itens mágicos",
                          "Todos os itens mágicos do System Reference Document 5.1 (em inglês).",
                          "en", "itens_magicos", ["mestre"], [conv_item_magico(e) for e in magic]))

    for nome, pid, titulo, cat, conv, desc in [
        ("Feats", "srd-talentos", "SRD 5.1 — Talentos", "talentos", conv_talento,
         "Talentos do System Reference Document 5.1"),
        ("Backgrounds", "srd-antecedentes", "SRD 5.1 — Antecedentes", "antecedentes", conv_antecedente,
         "Antecedentes do System Reference Document 5.1"),
        ("Conditions", "srd-condicoes", "SRD 5.1 — Condições", "condicoes", conv_condicao,
         "Condições do System Reference Document 5.1"),
    ]:
        dados, idioma = baixar_preferindo_pt(nome)
        sufixo = " (tradução da comunidade 5e-bits)." if idioma == "pt-BR" else " (em inglês)."
        pacotes.append(pacote(pid, titulo, desc + sufixo, idioma, cat, pub_jm,
                              [conv(x, idioma) for x in dados]))

    print("%-22s %-7s %6s %9s" % ("pacote", "idioma", "itens", "KB"))
    for p in pacotes:
        caminho = os.path.join(destino, p["id"] + ".json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=1)
            f.write("\n")
        kb = os.path.getsize(caminho) / 1024
        print("%-22s %-7s %6d %9.1f" % (p["id"], p["idioma"], len(p[p["categoria"]]), kb))


if __name__ == "__main__":
    main()
