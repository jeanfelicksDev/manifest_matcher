"""
parser_sydam.py
---------------
Parseur dédié au format SYDAM (manifeste douanier de Côte d'Ivoire).

Anatomie d'une ligne BL principale (tout sur une seule ligne) :
  POL  N°Ligne  BL_REF  SHIPPER_TEXT  T.T.  RATIO  REF_CT1  QTY1 QTY2 QTY3 QTY4  TYPE  NB_COLIS  UNIT  DESCRIPTION  POIDS_BL

  Exemples réels :
  "CNSHA 1 OOLU2165193220 FEDRIGONI (ANHUI) SELF T 1/ C 1 KU719904 40 5 HC 26 PK SELF ADHESIVE MATERIAL - 50615"
   POL=CNSHA, N=1, BL=OOLU2165193220, SHIPPER=FEDRIGONI (ANHUI) SELF,
   T.T.=T (Transit), RATIO=1/C, CT1=KU719904, QTY=40 5, TYPE=HC,
   NB_COLIS=26 PK, DESC=SELF ADHESIVE MATERIAL -, POIDS=50615

  "CNTAO 2 OOLU2319022650 GUANGZHOU HUANRUN IMPORT O 1/1 OCU91149 4 2 0 0 HC 102 PK DISC PLOUGHBOOM... 28670"
   POL=CNTAO, N=2, SHIPPER=GUANGZHOU HUANRUN IMPORT, T.T.=O, RATIO=1/1,
   CT1=OCU91149, QTY=4 2 0 0 (=> 40'x2), TYPE=HC => 40HC,
   NB_COLIS=102 PK, POIDS=28670

  Observation clé :
  - QTY = 4 chiffres séparés : [taille_dizaine] [taille_unite] [nb_exp1] [nb_exp2]
    Ex: "4 5 0 9 HC" => size=45? Non : "40 5 HC" parfois, ou "4 2 0 0 HC" => 40 x 2 x 00 x 0 => taille 40
  - En pratique : si les chiffres précèdent HC/DV/HR, c'est toujours 40 ou 20

Lignes qui suivent la ligne BL (dans l'ordre variable) :
  - Scellé OOCL du 1er conteneur : "OOLKPP7439 COATED80..."
  - Suite de déscription ou localité
  - Numéros de conteneurs supplémentaires : "TIIU4912578 40 25,991 ..."
  - Type du conteneur sur ligne dédiée : "1/1 40HC"
  - Importateur + scellé éventuel : "AFRIPACK OOLKPP7474"
  - "Marques et colis"
  - "VMC"
  - Nom importateur / consignee / notify

Plan JSON (PlanJson.docx) :
{
  "navire": str,
  "numero_voyage": str,
  "eta": str,
  "ports": {
    "<POL>": {
      "bls": {
        "<BL_REF>": {
          "shipper":     str | None,
          "consignee":   str | None,
          "notify":      str | None,
          "designation": str | None,
          "conteneurs": {
            "<NUM_CT>": {
              "type":       str,    # "40HC", "20DV", "40HR"...
              "num_plomb":  str,    # scellé
              "nbre_colis": int,
              "poids_brut": float,
              "volume":     None    # SYDAM ne fournit pas le volume
            }
          }
        }
      }
    }
  }
}
"""

import re
import pdfplumber


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_type(size_str: str, variant_str: str) -> str:
    """
    Construit et normalise le type de conteneur.
    size_str    : "20" ou "40"
    variant_str : "HC", "HQ", "DV", "GP", "HR", "OT", "FR"...
    Retourne    : "40HC", "20DV", "40HR", etc.
    """
    variant = variant_str.upper()
    variant_map = {
        "HQ": "HC",   # High Cube = HC
        "GP": "DV",   # General Purpose = Dry Van
        "HC": "HC",
        "DV": "DV",
        "HR": "HR",   # Reefer
        "OT": "OT",   # Open Top
        "FR": "FR",   # Flat Rack
        "RF": "RF",   # Reefer variant
    }
    return size_str + variant_map.get(variant, variant)


def _extract_type_from_bl_line(text: str):
    """
    Extrait le type de conteneur depuis la zone QTY+TYPE d'une ligne BL.

    Formats observés :
      "40 5 HC"            -> 40HC
      "4 2 0 0 HC"         -> 40HC  (1er chiffre = dizaine taille, 2ème = unité)
      "4 5 0 9 HC"         -> 40HC
      "4 8 0 HR"           -> 40HR  (reefer)
      "2 3 0 2 DV"         -> 20DV
      "40 3 HC"            -> 40HC

    Retourne (size, variant) ou (None, None)
    """
    # Pattern 1 : "40 N TYPE" ou "20 N TYPE"
    m = re.search(r'\b(40|20)\s+\d+\s+(HC|HQ|DV|GP|HR|OT|RF|FR)\b', text)
    if m:
        return m.group(1), m.group(2)

    # Pattern 2 : "D U X Y TYPE" où D=dizaine, U=unité de la taille (ex: 4 5 => 40 ou 45?)
    # En pratique SYDAM : "4 X 0 Y HC" signifie 40'HC
    # On cherche le pattern : chiffre_seul ESPACE chiffre_seul ESPACE ... TYPE_2lettres
    m = re.search(r'\b([24])[\s]+(\d)[\s]+(\d)[\s]+(\d)[\s]+(HC|HQ|DV|GP|HR|OT|RF|FR)\b', text)
    if m:
        size = m.group(1) + "0"   # 4 => 40, 2 => 20
        return size, m.group(5)

    # Pattern 3 : juste le type seul (rare)
    m = re.search(r'\b(20|40)(HC|HQ|DV|GP|HR)\b', text)
    if m:
        return m.group(1), m.group(2)

    return None, None


# ── Regex principaux ──────────────────────────────────────────────────────────

# Ligne BL : POL (3-6 lettres majuscules) + N° + BL_REF
_RE_BL_START = re.compile(
    r'^([A-Z]{3,6})\s+(\d+)\s+'
    r'((?:OOLU|MSCU|HLCU|MAEU|CMAU|COSU|EVGU|YMLU|APLU|ANNU|SUDU|MEDU)[A-Z0-9]+)'
)

# Numéro de conteneur ISO long : 4 lettres + 7 chiffres (TIIU4912578)
_RE_CONT_ISO = re.compile(r'\b([A-Z]{4}\d{7})\b')

# Numéro de conteneur court OOCL dans la ligne BL : 3 lettres + 5-7 chiffres
# Ex: KU719904, OCU91149, SGU61687, MOU56713, OCU63436
# MAIS ce n'est pas le numéro ISO du conteneur physique, c'est la référence interne
# On l'utilise comme fallback si aucun conteneur ISO n'est trouvé
_RE_CONT_SHORT = re.compile(r'\b([A-Z]{2,3}\d{5,7})\b')

# Scellé OOCL : commence par OOL + 3-4 lettres + chiffres
_RE_SEAL = re.compile(r'\b(OOL[A-Z]{3,4}\d+)\b')

# Ligne de type dédiée : "1/1 40HC" ou "1/2 40HC" ou "40HC" seul
_RE_TYPE_LINE = re.compile(r'^(?:\d+/\d+\s+)?(20|40)(HC|HQ|DV|GP|HR|OT|FR|RF)\s*$')

# Nombre de colis + unité
_RE_COLIS = re.compile(
    r'\b(\d+)\s+(?:PK|CT|Colis|Carton|carton|package|PKG|SAC|BAG|DRUM|PCS|DR|pieces?)\b',
    re.IGNORECASE
)

# Poids BL = dernier entier seul en fin de ligne (4–7 chiffres)
_RE_POIDS_EOL = re.compile(r'\b(\d{4,7})\s*$')

# Lignes de mise en page à ignorer
_SKIP = re.compile(
    r'(^-{5,}'
    r'|^Port de\s'
    r'|^Chargement No'
    r'|^Ligne Conteneur'
    r'|^Marques et colis'
    r'|^\d{2}/\d{2}/\d{4}\s+\d+\s+\d+\s*$'
    r'|^R[eé]publique'
    r"|^d'Ivoire"
    r'|^MINISTERE'
    r'|^Union-Disc'
    r'|^No Validation'
    r'|^C\s*-\s*H'
    r'|^Nombre de page'
    r'|^Nombre total'
    r'|^Marchandises'
    r'|^ABIDJAN'
    r'|^Discharge\s'
    r'|^Entering\s'
    r'|^Port Douane'
    r'|^:\s'
    r'|^Tonne \(net\)'
    r'|^\("package"\)'
    r'|^Colis$'
    r'|^Carton$'
    r'|^Description de'
    r'|^Transporteur'
    r')'
)


# ─────────────────────────────────────────────────────────────────────────────
# Parseur principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_sydam(file_obj) -> dict:
    """
    Parse un fichier PDF SYDAM et retourne un dict conforme au plan JSON.
    file_obj : chemin (str) ou file-like object (Streamlit UploadedFile).
    """

    # ── Lecture du texte brut ──────────────────────────────────────────────
    all_lines = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            txt = page.extract_text(layout=True)
            if txt:
                for line in txt.split("\n"):
                    all_lines.append(line)

    # ── Résultat ──────────────────────────────────────────────────────────
    result = {
        "navire":        None,
        "numero_voyage": None,
        "eta":           None,
        "ports":         {}
    }

    # ── En-tête global ────────────────────────────────────────────────────
    header = "\n".join(all_lines[:20])
    m = re.search(r'Navire\s*:\s*(.+)', header)
    if m:
        result["navire"] = m.group(1).strip()
    m = re.search(r'No\.?\s*Voyage\s+(\S+)', header)
    if m:
        result["numero_voyage"] = m.group(1).strip()
    m = re.search(r"Date d.arriv[eé]e?\s*:\s*([\d/]+)", header)
    if m:
        result["eta"] = m.group(1).strip()

    # ── Variables d'état ──────────────────────────────────────────────────
    current_pol  = None
    current_bl   = None
    after_vmc    = False
    pending_ct   = None   # dernier numéro de conteneur en attente de son type

    # ── Parcours ligne par ligne ───────────────────────────────────────────
    for raw_line in all_lines:
        line = raw_line.strip()
        if not line:
            continue

        # ── NOUVELLE LIGNE BL PRINCIPALE ──────────────────────────────────
        m_bl = _RE_BL_START.match(line)
        if m_bl:
            after_vmc  = False
            pending_ct = None
            current_pol = m_bl.group(1)
            bl_ref      = m_bl.group(3)
            current_bl  = bl_ref

            # Zone après le BL_REF
            after_bl = line[m_bl.end():].strip()

            # ── Poids brut BL (dernier entier de la ligne) ─────────────────
            m_p = _RE_POIDS_EOL.search(line)
            poids_bl = float(m_p.group(1)) if m_p else 0.0

            # ── Nombre de colis ────────────────────────────────────────────
            m_c = _RE_COLIS.search(line)
            nb_colis_bl = int(m_c.group(1)) if m_c else 0

            # ── Désignation marchandise ────────────────────────────────────
            # Entre l'unité de colis et le poids final
            designation = None
            m_desc = re.search(
                r'\b(?:PK|CT|Colis|Carton|carton|package|PKG|PCS)\s+(.+?)\s+\d{4,7}\s*$',
                line, re.IGNORECASE
            )
            if m_desc:
                designation = m_desc.group(1).strip()

            # ── Shipper ────────────────────────────────────────────────────
            # Format : SHIPPER_TEXT  T.T.(1 lettre)  RATIO  CT_REF  QTY TYPE ...
            # On veut le texte AVANT le T.T. (lettre isolée + ratio 1/X)
            m_sh = re.match(
                r'(.+?)\s+[A-Z]\s+\d+/\s*[A-Z0-9]\s+\d',
                after_bl
            )
            if m_sh:
                shipper = m_sh.group(1).strip()
            else:
                # Fallback : tout avant le 1er chiffre
                m_sh2 = re.match(r'([A-Za-z][A-Za-z\s,\.\(\)]+?)\s+\d', after_bl)
                shipper = m_sh2.group(1).strip() if m_sh2 else None

            # Nettoyer le shipper (enlever le T.T. s'il est collé)
            if shipper:
                # Le T.T. est une lettre isolée (T, O, B, C, F) en fin de shipper
                shipper = re.sub(r'\s+[TOBCFE]$', '', shipper).strip()

            # ── Type du 1er conteneur ─────────────────────────────────────
            size_ct, variant_ct = _extract_type_from_bl_line(after_bl)
            first_ct_type = _normalize_type(size_ct, variant_ct) if size_ct else None

            # ── Référence interne du 1er conteneur ────────────────────────
            # Ex: "KU719904", "OCU91149", "SGU61687", "MOU56713"
            m_ct1_ref = re.search(
                r'\d+/[A-Z0-9\s]+\s+([A-Z]{2,4}\d{5,7})\s+\d',
                after_bl
            )
            initial_ct = {}
            short_ct_ref = None
            if m_ct1_ref:
                short_ct_ref = m_ct1_ref.group(1)
                initial_ct[short_ct_ref] = {
                    "type": first_ct_type or "",
                    "num_plomb": "",
                    "nbre_colis": nb_colis_bl,
                    "poids_brut": poids_bl,
                    "volume": None
                }

            # ── Initialisation du BL ──────────────────────────────────────
            if current_pol not in result["ports"]:
                result["ports"][current_pol] = {"bls": {}}
            if bl_ref not in result["ports"][current_pol]["bls"]:
                result["ports"][current_pol]["bls"][bl_ref] = {
                    "shipper":       shipper,
                    "consignee":     None,
                    "notify":        None,
                    "designation":   designation,
                    "conteneurs":    initial_ct,
                    # Clés temporaires
                    "_first_ct_type": first_ct_type,
                    "_poids_bl":      poids_bl,
                    "_nb_colis_bl":   nb_colis_bl,
                    "_short_ct_ref":  short_ct_ref,
                }
            continue

        # ── Pas de BL courant → ignorer ───────────────────────────────────
        if current_bl is None or current_pol not in result["ports"]:
            continue

        bl_data = result["ports"][current_pol]["bls"].get(current_bl)
        if bl_data is None:
            continue

        # ── "VMC" → la ligne suivante = importateur (consignee & notify) ──
        # VMC peut être seul ("VMC") ou en fin de ligne ("OOLKPY7584 VMC")
        has_vmc = line == "VMC" or line.endswith(" VMC") or re.match(r'^OOL[A-Z]{3,4}\d+\s+VMC$', line)
        if has_vmc:
            # Si scellé + VMC sur la même ligne → enregistrer le scellé aussi
            if line != "VMC":
                m_seal_vmc = _RE_SEAL.search(line)
                if m_seal_vmc and bl_data["conteneurs"]:
                    for ct_num in reversed(list(bl_data["conteneurs"].keys())):
                        if not bl_data["conteneurs"][ct_num]["num_plomb"]:
                            bl_data["conteneurs"][ct_num]["num_plomb"] = m_seal_vmc.group(1)
                            break
            after_vmc = True
            continue

        if after_vmc:
            if _SKIP.search(line):
                continue
            
            # Sortir de after_vmc si on tombe sur un conteneur, un scellé ou le prochain BL
            if _RE_CONT_ISO.search(line) or _RE_SEAL.search(line) or _RE_BL_START.match(line):
                after_vmc = False
                # Ne pas utiliser 'continue', on doit traiter cette ligne (c'est un conteneur/seal !)
                pass
            else:
                # C'est donc bien la suite du consignee / notify
                clean_name = re.sub(r'\s+OOLU\w+\s+\d+.*$', '', line).strip()
                clean_name = re.sub(r'\s+OOL[A-Z]{3,4}\d+.*$', '', clean_name).strip()
                
                if clean_name:
                    if not bl_data["consignee"]:
                        bl_data["consignee"] = clean_name
                    elif clean_name not in bl_data["consignee"]:
                        bl_data["consignee"] += " " + clean_name

                    if not bl_data["notify"]:
                        bl_data["notify"] = clean_name
                    elif clean_name not in bl_data["notify"]:
                        bl_data["notify"] += " " + clean_name
                continue

        # ── Ignorer les lignes de mise en page ────────────────────────────
        if _SKIP.search(line):
            continue

        # ── Ligne de type dédiée : "1/1 40HC" ────────────────────────────
        m_type_only = _RE_TYPE_LINE.match(line)
        if m_type_only:
            ct_type = _normalize_type(m_type_only.group(1), m_type_only.group(2))
            # Associer au dernier conteneur sans type
            found = False
            if pending_ct and pending_ct in bl_data["conteneurs"]:
                if not bl_data["conteneurs"][pending_ct]["type"]:
                    bl_data["conteneurs"][pending_ct]["type"] = ct_type
                    found = True
                pending_ct = None
            if not found:
                for ct_num in reversed(list(bl_data["conteneurs"].keys())):
                    if not bl_data["conteneurs"][ct_num]["type"]:
                        bl_data["conteneurs"][ct_num]["type"] = ct_type
                        break
            continue

        # ── Numéro de conteneur ISO (format physique XXXX1234567) ────────
        m_cont = _RE_CONT_ISO.search(line)
        if m_cont:
            ct_num = m_cont.group(1)
            if ct_num == current_bl:
                continue   # éviter confusion BL ref / conteneur

            ct_seal = ""
            short_ref = bl_data.get("_short_ct_ref")
            if short_ref and short_ref in bl_data["conteneurs"]:
                ct_seal = bl_data["conteneurs"][short_ref].get("num_plomb", "")
                del bl_data["conteneurs"][short_ref]
                bl_data["_short_ct_ref"] = None

            # Scellé OOCL sur cette même ligne ou ligne "OOLKXXX..."
            m_seal = _RE_SEAL.search(line)
            if m_seal:
                ct_seal = m_seal.group(1)
            elif bl_data.get("_seal_pending"):
                ct_seal = bl_data.pop("_seal_pending")

            # Type : sur cette ligne ou (souvent) sur la ligne suivante "1/1 40HC"
            m_type_inline = re.search(r'\b(20|40)(HC|HQ|DV|GP|HR|OT|RF|FR)\b', line)
            if m_type_inline:
                ct_type = _normalize_type(m_type_inline.group(1), m_type_inline.group(2))
            else:
                # Le type viendra sur la prochaine ligne "1/1 40HC"
                # En attendant, utiliser _first_ct_type
                ct_type = bl_data.get("_first_ct_type") if not bl_data["conteneurs"] else ""

            # Nbre colis du conteneur (1er chiffre après le num CT)
            after_ct = line[m_cont.end():].strip()
            m_nc = re.match(r'(\d+)', after_ct)
            nbre_colis_ct = int(m_nc.group(1)) if m_nc else bl_data.get("_nb_colis_bl", 0)

            # Poids individuel du conteneur (entier 4-7 en fin de ligne)
            m_pw = _RE_POIDS_EOL.search(line)
            ct_poids = float(m_pw.group(1)) if m_pw else bl_data.get("_poids_bl", 0.0)

            bl_data["conteneurs"][ct_num] = {
                "type":       ct_type or "",
                "num_plomb":  ct_seal,
                "nbre_colis": nbre_colis_ct,
                "poids_brut": ct_poids,
                "volume":     None
            }
            if not ct_type:
                pending_ct = ct_num   # attendre la ligne "1/1 40HC"
            continue

        # ── Scellé OOCL seul sur une ligne ──
        m_seal_only = _RE_SEAL.search(line)
        if m_seal_only:
            seal = m_seal_only.group(1)
            if bl_data["conteneurs"]:
                # Attribuer au dernier conteneur sans plomb
                for ct_num in reversed(list(bl_data["conteneurs"].keys())):
                    if not bl_data["conteneurs"][ct_num]["num_plomb"]:
                        bl_data["conteneurs"][ct_num]["num_plomb"] = seal
                        break
            else:
                bl_data["_seal_pending"] = seal
            
            # Suite de la designation après / avant le seal
            rest = line.replace(seal, '').strip()
            # Nettoyage des mots clés SYDAM
            rest = re.sub(r'\b(CT|PK|Colis|package|PCS|DRUM|BAG|CARTON)\b', '', rest, flags=re.IGNORECASE).strip()
            rest = rest.replace('()', '').replace('("")', '').strip()
            if rest:
                if bl_data["designation"] and rest not in bl_data["designation"]:
                    bl_data["designation"] += " " + rest
                elif not bl_data["designation"]:
                    bl_data["designation"] = rest
            continue

        # ── Lignes orphelines avant VMC (suite de Shipper / Designation) ──
        if not after_vmc:
            # Avec layout=True, on peut isoler gauche et droite par les "grands espaces"
            clean_raw = raw_line.rstrip()
            started_with_spaces = clean_raw.startswith('    ')
            parts = [p.strip() for p in re.split(r'\s{4,}', clean_raw) if p.strip()]

            left, right = "", ""
            if len(parts) >= 2:
                left, right = parts[0], parts[1]
            elif len(parts) == 1:
                # Si ça commence avec bcp d'espaces, c'est la colonne designation (droite)
                if started_with_spaces:
                    right = parts[0]
                else:
                    left = parts[0]

            # Nettoyage
            def _clean_str(s):
                return re.sub(r'\b(Colis|package|Marques et colis)\b', '', s, flags=re.IGNORECASE).replace('()', '').replace('("")', '').replace('"', '').strip()

            left, right = _clean_str(left), _clean_str(right)

            if left:
                if bl_data["shipper"] and left not in bl_data["shipper"]:
                    bl_data["shipper"] += " " + left
                elif not bl_data["shipper"]:
                    bl_data["shipper"] = left
                    
            if right:
                if bl_data["designation"] and right not in bl_data["designation"]:
                    bl_data["designation"] += " " + right
                elif not bl_data["designation"]:
                    bl_data["designation"] = right

    # ── Nettoyage des clés temporaires ───────────────────────────────────
    for port_data in result["ports"].values():
        for bl_data in port_data["bls"].values():
            for key in ["_first_ct_type", "_poids_bl", "_nb_colis_bl", "_seal_pending", "_short_ct_ref"]:
                bl_data.pop(key, None)
            
            # Prune Consignee name from Shipper if it leaked
            if bl_data.get("shipper") and bl_data.get("consignee"):
                cname = bl_data["consignee"]
                if cname in bl_data["shipper"]:
                    bl_data["shipper"] = bl_data["shipper"].replace(cname, "").strip()
                    # Remplacer les doubles espaces post-nettoyage
                    bl_data["shipper"] = re.sub(r'\s{2,}', ' ', bl_data["shipper"])

    return result
