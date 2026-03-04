"""
parser_cargo.py
---------------
Parseur dédié au format OOCL Cargo Manifest (INBOUND).

Structure du PDF CARGO :
  En-tête (répété sur chaque page) :
    VESSEL : (CODE) NOM_NAVIRE  SHIP FLAG : PAYS
    VOYAGE : XXX ...
    ARRIVAL DATE : DD/MM/YYYY  (ou vide)
    PORT OF LOAD : VILLE
    PORT OF DISCHARGE : VILLE

  Bloc BL :
    B/L NUMBER: OOLUXXXXXXXXXX IB CARGO PICKUP: ...
    SHIPPER: NOM_SHIPPER.  NB_COLIS UNITE  DESCRIPTION  GROSS WEIGHT : XXX KG .
             SUITE_SHIPPER . . VOLUME : XXX CBM .
             ...
    CONSIGNEE:
    NOM_CONSIGNEE
    ADRESSE...
    NOTIFY PARTY:
    NOM_NOTIFY
    ADRESSE...
    ALSO NOTIFY PARTY:
    ...
    ** TOTAL : NB_COLIS UNITE  GROSS WEIGHT : XXX KG
    VOLUME : XXX CBM
    ...

  Tableau conteneurs (avant ou après le BL suivant) :
    CONTAINER NUM  SEAL NUMBER  SZTY  NUM OF PACKS  TRAFFIC  SHPR WT (KG)  REMARKS WEIGHT
    CSNU8817661    OOLJWV8819   40HQ  419 CT        FCL/FCL  23547.050    TARE WT : 4.00
    TCNU6317960    OOLJWV8915   40HQ  421 CT        FCL/FCL  23597.050    TARE WT : 3.90

Format JSON de sortie (plan PlanJson.docx) :
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
              "type":       str,    # ex: "40HC", "20DV"
              "num_plomb":  str,    # seal number
              "nbre_colis": int,
              "poids_brut": float,  # poids shipper individuel par conteneur (KG)
              "volume":     float | None  # CBM
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

def _normalize_type(size: str, variant: str) -> str:
    """
    Normalise le type de conteneur OOCL en format standard.
    OOCL utilise :
      40HQ = High Cube 40' -> 40HC
      20GP = General Purpose 20' -> 20DV
      40GP = General Purpose 40' -> 40DV
      40HC -> 40HC
      20DV -> 20DV
      40OT -> 40OT
      40FR -> 40FR
    """
    variant = variant.upper()
    variant_map = {
        "HQ": "HC",
        "GP": "DV",
        "HC": "HC",
        "DV": "DV",
        "OT": "OT",
        "FR": "FR",
        "RF": "RF",
        "HR": "HR",
    }
    return size + variant_map.get(variant, variant)


# Regex : ligne tableau conteneur
# Ex: "CSNU8817661 OOLJWV8819 40HQ 419 CT FCL/FCL 23547.050 TARE WT : 4.00"
_RE_CT_LINE = re.compile(
    r'^([A-Z]{4}\d{7})\s+'          # G1 : numéro conteneur
    r'([A-Z0-9]{6,12})\s+'          # G2 : scellé (seal)
    r'(20|40)([A-Z]{2})\s+'         # G3+G4 : taille + variant (40HQ, 20GP...)
    r'(\d+)\s+\w+\s+'               # G5 : nombre de colis
    r'(?:FCL/FCL|LCL/LCL|FCL/LCL|LCL/FCL)\s+'
    r'([\d\.]+)',                    # G6 : poids shipper (KG)
)

# Regex: ligne tableau conteneur sans trafic (format alternatif)
_RE_CT_LINE_ALT = re.compile(
    r'^([A-Z]{4}\d{7})\s+'
    r'([A-Z0-9]{6,12})\s+'
    r'(20|40)([A-Z]{2})\s+'
    r'(\d+)\s+\w+\s+'
    r'([\d\.]+)',
)

# Regex : en-tête de page (à ignorer pour le parsing BL)
_RE_PAGE_HEADER = re.compile(
    r'(ORIENT OVERSEAS|CARGO MANIFEST|SERVICE\s*:|VESSEL\s*:|VOYAGE\s*:'
    r'|ARRIVAL DATE|PLACE OF RECEIPT|PORT OF (?:LOAD|DISCHARGE|DELIVERY)'
    r'|CUSTOMER INFORMATION|OF PKGS|_{10,}|CONTAINER NUM|REPORT ID\s*:)',
    re.IGNORECASE
)

# Lignes bruyantes (à ignorer)
_RE_SKIP = re.compile(
    r'(See Clause|PAGE NUMBER|DESTINATION CHARGES|LAWFULLY DEMANDS'
    r'|SHIPPER LOAD AND COUNT|DESTINATION OFFICE|AFRICA GLOBAL|AVENUE CHRISTIANI'
    r'|ABIDJAN, COTE|CALCULATION OF PACKAGE|TOTAL NO\. OF CONTAINERS)',
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────────────────────
# Parseur principal
# ─────────────────────────────────────────────────────────────────────────────

def parse_cargo(file_obj) -> dict:
    """
    Parse un fichier PDF OOCL Cargo Manifest et retourne un dict conforme
    au plan JSON.
    file_obj : chemin (str) ou file-like object
    """

    # ── Lecture page par page ──────────────────────────────────────────────
    pages_lines = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            page_lines = txt.split("\n") if txt else []
            pages_lines.append(page_lines)

    # ── Résultat ──────────────────────────────────────────────────────────
    result = {
        "navire": None,
        "numero_voyage": None,
        "eta": None,
        "ports": {}
    }

    # ── En-tête global (page 1) ────────────────────────────────────────────
    header = "\n".join(pages_lines[0][:15]) if pages_lines else ""

    m = re.search(r'VESSEL\s*:\s*\([^)]+\)\s+(.+?)\s+SHIP FLAG', header, re.IGNORECASE)
    if m:
        result["navire"] = m.group(1).strip()

    m = re.search(r'VOYAGE\s*:\s*(.+)', header, re.IGNORECASE)
    if m:
        # Tout ce qui est sur la ligne après "VOYAGE :"
        raw_voy = m.group(1).split("NAME OF MASTER")[0].strip()
        result["numero_voyage"] = raw_voy

    m = re.search(r'ARRIVAL DATE\s*:\s*([\d/]+)', header, re.IGNORECASE)
    result["eta"] = m.group(1).strip() if m else None

    # POL par défaut (peut changer page par page selon "PORT OF LOAD")
    pol_default = "INCONNU"
    m = re.search(r'PORT OF LOAD\s*:\s*(\S+)', header, re.IGNORECASE)
    if m:
        pol_default = m.group(1).strip()

    # ── Reconstruction du texte global en séquence de lignes ──────────────
    # On aplatit toutes les pages, mais on garde la notion de page
    # pour retrouver le POL (PORT OF LOAD) qui peut changer.
    # Structure : liste de (texte_ligne, pol_courant)

    annotated_lines = []   # [(line_str, pol)]
    for page_lines in pages_lines:
        pol_page = pol_default
        # Chercher PORT OF LOAD sur cette page
        page_text = "\n".join(page_lines)
        m_pol = re.search(r'PORT OF LOAD\s*:\s*(\S+)', page_text, re.IGNORECASE)
        if m_pol:
            pol_page = m_pol.group(1).strip()

        for line in page_lines:
            annotated_lines.append((line.strip(), pol_page))

    # ── Machine à états : parcours des lignes ─────────────────────────────
    # États possibles : 'idle' | 'in_shipper' | 'in_consignee' | 'in_notify'
    #                   | 'in_also_notify' | 'in_total'

    current_bl     = None
    current_pol    = pol_default
    state          = 'idle'
    shipper_lines  = []
    consignee_lines = []
    notify_lines   = []

    # Conteneurs en attente d'être attribués à un BL
    # (les lignes conteneurs apparaissent parfois AVANT le bloc BL suivant)
    pending_containers = {}   # {bl_ref: [ct_dict, ...]}
    current_bl_containers = {}  # conteneurs du BL courant accumulés

    def _flush_bl():
        """Sauvegarde le BL courant dans result."""
        nonlocal current_bl, current_pol, shipper_lines, consignee_lines, notify_lines
        nonlocal current_bl_containers

        if current_bl is None:
            return

        # ── Shipper ───────────────────────────────────────────────────────
        # Dans le PDF CARGO, les colonnes sont séparées par " . " (espace-point-espace).
        # Chaque ligne du bloc SHIPPER peut avoir du texte de colonne droite fusionné :
        #   "CHONGQING DALONGYUFENG . AAM2412-30 VOLUME : 145.570 CBM ."
        #   => shipper = "CHONGQING DALONGYUFENG"
        #
        # Cas N/M : la 1ère ligne = "N/M.  NB UNITE DESCRIPTION  GROSS WEIGHT..."
        #   => le vrai nom est sur les lignes suivantes, même règle de coupure " . "
        #
        # Règle universelle :
        #   1. Trouver la ligne avec le nom (1ère non-N/M, non-adresse)
        #   2. Couper avant " . " pour enlever le texte de colonne droite
        #   3. Nettoyer les trailers (., ,, &)

        def _extract_name_from_shipper_line(sl: str) -> str:
            """Extrait le nom depuis une ligne shipper (côté gauche avant ' . ' ou '. chiffre')."""
            sl = sl.strip()
            if not sl or sl in (".", ".."):
                return ""
            # Coupure avant " . " (séparateur de colonnes gauche/droite dans PDF)
            if ' . ' in sl:
                sl = sl.split(' . ')[0]
            # Coupure avant ". NB " (ex: "SONLINK. 747 PACKAGES...")
            elif re.search(r'\.\s+\d', sl):
                sl = re.split(r'\.\s+\d', sl)[0]
            # Nettoyer les fins parasites
            sl = re.sub(r'\s*[,\.\&]\s*$', '', sl).strip()
            return sl

        def _is_address_line(sl: str) -> bool:
            """Vrai si la ligne ressemble à une adresse/info (pas un nom de société)."""
            return bool(re.match(
                r'^(ADD|TEL|FAX|NO\.|ROOM|BUILD|ROAD|TOWN|DIST|CITY|PHONE|E-MAIL|PASSPORT|TAX|VAT|NINEA|ID\s*NO|IDNO)',
                sl.strip(), re.IGNORECASE
            ))

        def _extract_actor_name(lines, is_shipper=False):
            left_parts = []
            right_parts = []
            # Mots clés typiques de la colonne de droite (Désignation / Poids) dans CARGO
            right_kw = r'(GROSS WEIGHT|VOLUME:|CARGO IN|ON-CARRIAGE|ARRANGED BY|THEIR RESPONSIBILITY|THEIR COSTS|FREIGHT PREPAID|OCEAN FREIGHT)'

            for sl in lines:
                sl = sl.strip()
                if not sl or sl in (".", ".."):
                    continue
                if sl.upper() == "SAME AS CONSIGNEE":
                    break
                
                # Retirer N° de suivi/TVA (alphanum > 10 chars isolé ou en fin)
                sl = re.sub(r'\s+[A-Z0-9-]{10,}$', '', sl).strip()
                if re.match(r'^[A-Z0-9-]{10,}$', sl):
                    continue

                left = sl
                right = ""

                # Tentative de séparation gauche (Shipper) / droite (Désignation)
                if ' . ' in sl:
                    sp = sl.split(' . ', 1)
                    left, right = sp[0].strip(), sp[1].strip()
                elif re.search(r'\.\s+\d', sl):
                    sp = re.split(r'\.\s+(?=\d)', sl, 1)
                    left, right = sp[0].strip(), sp[1].strip()
                else:
                    # Séparation par mot-clé de la colonne droite s'ils sont collés
                    m = re.search(r'\s+(' + right_kw + r'.*)', sl, re.IGNORECASE)
                    if m:
                        left = sl[:m.start()].strip()
                        right = m.group(1).strip()

                # Nettoyage
                left = re.sub(r'\s*[,\.\&]\s*$', '', left).strip()

                if left and left.upper() not in ('N/M', ''):
                    left_parts.append(left)
                if right:
                    right_parts.append(right)
            
            # Pour le Shipper, on retourne (Texte_Gauche, Texte_Droite)
            if is_shipper:
                return " ".join(left_parts) if left_parts else None, " ".join(right_parts) if right_parts else None
            else:
                return " ".join(left_parts) if left_parts else None

        # ── Extraction Shipper / Désignation ──
        shipper, raw_designation = _extract_actor_name(shipper_lines, is_shipper=True)

        consignee = _extract_actor_name(consignee_lines)
        notify    = _extract_actor_name(notify_lines)

        # Désignation : on nettoie la colonne de droite (on garde tout sur une seule ligne)
        designation = None
        if raw_designation:
            designation = re.sub(r'\s+', ' ', raw_designation).strip()

        if current_pol not in result["ports"]:
            result["ports"][current_pol] = {"bls": {}}

        result["ports"][current_pol]["bls"][current_bl] = {
            "shipper":     shipper,
            "consignee":   consignee,
            "notify":      notify,
            "designation": designation,
            "conteneurs":  current_bl_containers
        }

        shipper_lines   = []
        consignee_lines = []
        notify_lines    = []
        current_bl_containers = {}

    # ── Parcours ───────────────────────────────────────────────────────────
    for line, pol in annotated_lines:

        if not line:
            continue

        # Ignorer les lignes de mise en page
        if _RE_PAGE_HEADER.search(line) or _RE_SKIP.search(line):
            continue

        # ── Début d'un nouveau BL ──────────────────────────────────────────
        m_bl = re.match(
            r'B/L NUMBER:\s+'
            r'((?:OOLU|MSCU|HLCU|MAEU|CMAU|COSU|EVGU|YMLU|APLU|ANNU|SUDU|MEDU)[A-Z0-9]+)',
            line, re.IGNORECASE
        )
        if m_bl:
            _flush_bl()
            current_bl  = m_bl.group(1).strip().upper()
            current_pol = pol
            state       = 'in_shipper'
            current_bl_containers = {}
            continue

        if current_bl is None:
            # Chercher des lignes conteneurs avant le premier BL (rare)
            _try_parse_container(line, None, pending_containers)
            continue

        # ── Transitions d'état ─────────────────────────────────────────────
        if re.match(r'^SHIPPER\s*:', line, re.IGNORECASE):
            state = 'in_shipper'
            # La 1ère ligne shipper peut être sur la même ligne
            rest = re.sub(r'^SHIPPER\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            if rest:
                shipper_lines.append(rest)
            continue

        if re.match(r'^CONSIGNEE\s*:', line, re.IGNORECASE):
            state = 'in_consignee'
            rest = re.sub(r'^CONSIGNEE\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            if rest:
                consignee_lines.append(rest)
            continue

        if re.match(r'^NOTIFY PARTY\s*:', line, re.IGNORECASE):
            state = 'in_notify'
            rest = re.sub(r'^NOTIFY PARTY\s*:\s*', '', line, flags=re.IGNORECASE).strip()
            if rest:
                notify_lines.append(rest)
            continue

        if re.match(r'^ALSO NOTIFY PARTY\s*:', line, re.IGNORECASE):
            state = 'in_also_notify'
            continue

        if re.match(r'^\*\*\s*TOTAL\s*:', line, re.IGNORECASE):
            state = 'in_total'
            continue

        if re.match(r'^CODE IMPORT-EXPORT\s*:', line, re.IGNORECASE):
            state = 'idle'
            continue

        # ── Lignes de conteneurs (tableau) ─────────────────────────────────
        ct_parsed = _try_parse_container(line, current_bl, pending_containers)
        if ct_parsed:
            current_bl_containers[ct_parsed["num"]] = {
                "type":       ct_parsed["type"],
                "num_plomb":  ct_parsed["seal"],
                "nbre_colis": ct_parsed["nb_colis"],
                "poids_brut": ct_parsed["poids"],
                "volume":     None   # le volume est au niveau BL, pas conteneur
            }
            continue

        # ── Accumulation selon l'état ──────────────────────────────────────
        # Ignorer les lignes commençant par * (suite adresse ALSO NOTIFY)
        if line.startswith("*") or line.startswith("**"):
            continue

        if state == 'in_shipper':
            # Arrêter si ressemble à une adresse (ADD:, TEL:, etc.)
            if re.match(r'^(ADD|TEL|FAX|E-MAIL|ROOM|NO\.|BUILDING)', line, re.IGNORECASE):
                state = 'idle'
            else:
                shipper_lines.append(line)

        elif state == 'in_consignee':
            if re.match(r'^(ADD|TEL|FAX|E-MAIL|01\s*BP|QUARTIER|CODE IMPORT)', line, re.IGNORECASE):
                pass  # on ignore les adresses
            else:
                consignee_lines.append(line)

        elif state == 'in_notify':
            if re.match(r'^(ADD|TEL|FAX|E-MAIL|01\s*BP|QUARTIER)', line, re.IGNORECASE):
                pass
            else:
                notify_lines.append(line)

        elif state == 'in_total':
            # VOLUME sur la ligne suivant ** TOTAL
            m_vol = re.match(r'^VOLUME\s*:\s*([\d\.]+)\s*CBM', line, re.IGNORECASE)
            if m_vol:
                # On stocke le volume pour le BL courant
                # On le répartira plus tard
                result.setdefault("_bl_volumes", {})[current_bl] = float(m_vol.group(1))
            state = 'idle'

    # ── Flush du dernier BL ────────────────────────────────────────────────
    _flush_bl()

    # ── Répartition des volumes par BL -> conteneur ────────────────────────
    bl_volumes = result.pop("_bl_volumes", {})
    for port_data in result["ports"].values():
        for bl_ref, bl_data in port_data["bls"].items():
            vol = bl_volumes.get(bl_ref)
            if vol is None:
                continue
            nb_ct = len(bl_data["conteneurs"])
            if nb_ct == 0:
                continue
            # Répartition proportionnelle au poids si possible, sinon égale
            total_poids = sum(c["poids_brut"] for c in bl_data["conteneurs"].values())
            for ct_num, ct_data in bl_data["conteneurs"].items():
                if total_poids > 0:
                    ct_data["volume"] = round(vol * ct_data["poids_brut"] / total_poids, 3)
                else:
                    ct_data["volume"] = round(vol / nb_ct, 3)

    return result


def _try_parse_container(line: str, current_bl, pending: dict):
    """
    Tente de parser une ligne tableau conteneur.
    Retourne un dict avec les infos du conteneur ou None.
    """
    m = _RE_CT_LINE.match(line)
    if not m:
        m = _RE_CT_LINE_ALT.match(line)
        if not m:
            return None

    ct_num   = m.group(1).upper()
    seal     = m.group(2).upper()
    size     = m.group(3)
    variant  = m.group(4)
    nb_colis = int(m.group(5))
    poids    = float(m.group(6))
    ct_type  = _normalize_type(size, variant)

    return {
        "num":      ct_num,
        "seal":     seal,
        "type":     ct_type,
        "nb_colis": nb_colis,
        "poids":    poids,
    }
