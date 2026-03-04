"""
reconciliation.py
-----------------
Compare deux dictionnaires conformes au plan JSON (PlanJson.docx) et
retourne une liste de différences prêtes à être affichées.

Structure attendue en entrée :
{
  "navire":        str,
  "numero_voyage": str,
  "eta":           str,
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
              "type":       str,
              "num_plomb":  str,
              "nbre_colis": int,
              "poids_brut": float,
              "volume":     float | None
            }
          }
        }
      }
    }
  }
}

Format de sortie :
[
  {
    "Contexte":   str,   # ex: "Général", "BL", "Conteneur"
    "Identifiant": str,  # ex: numéro de BL, de conteneur
    "Champ":      str,   # ex: "Navire", "Type", "Poids Brut"
    "<label1>":   str,   # valeur dans le fichier 1
    "<label2>":   str,   # valeur dans le fichier 2
  }
]
"""

import re


def reconcile_manifests(data1: dict, data2: dict,
                        label1: str = "Valeur 1",
                        label2: str = "Valeur 2") -> list:
    """
    Compare les deux dicts JSON et retourne une liste de différences.
    Chaque élément = une ligne du tableau de résultats dans l'app.
    """
    diffs = []

    def _str(v) -> str:
        """Normalise une valeur en chaîne majuscule pour comparaison."""
        if v is None:
            return ""
        return str(v).strip().upper()

    def _add(contexte, identifiant, champ, v1, v2):
        """Ajoute une différence si les valeurs diffèrent."""
        s1, s2 = _str(v1), _str(v2)

        # Si les deux sont vides/absents, aucune différence
        if not s1 and not s2:
            return

        # Si l'un est absent mais pas l'autre
        if not s1:
            diffs.append({
                "Contexte":    contexte,
                "Identifiant": identifiant,
                "Champ":       champ,
                label1:        "Manquant",
                label2:        v2,
            })
            return
        if not s2:
            diffs.append({
                "Contexte":    contexte,
                "Identifiant": identifiant,
                "Champ":       champ,
                label1:        v1,
                label2:        "Manquant",
            })
            return

        # Les deux valeurs sont présentes : cas numérique
        if isinstance(v1, (float, int)) or isinstance(v2, (float, int)):
            try:
                # Tolérance de 0.01 pour CBM, 0.5 pour KG
                tol = 0.01 if "Volume" in champ else 0.5
                diff = abs(float(v1) - float(v2))
                if diff > tol:
                    diffs.append({
                        "Contexte":    contexte,
                        "Identifiant": identifiant,
                        "Champ":       champ,
                        label1:        v1,
                        label2:        v2,
                    })
            except (TypeError, ValueError):
                pass
            return

        # Les deux valeurs sont présentes : cas texte
        if s1 != s2:
            s1_clean = " ".join(s1.split())
            s2_clean = " ".join(s2.split())
            
            # Tolérance d'inclusion pour ces champs spécifiques (ex: SYDAM coupé)
            if champ in ["Shipper", "Consignee", "Notify", "Désignation"]:
                if s1_clean in s2_clean or s2_clean in s1_clean:
                    return

            diffs.append({
                "Contexte":    contexte,
                "Identifiant": identifiant,
                "Champ":       champ,
                label1:        v1,
                label2:        v2,
            })

    # ── 1. Comparaison en-tête global ───────────────────────────────────────
    _add("Général", "Navire",  "Nom du navire",  data1.get("navire"),        data2.get("navire"))
    _add("Général", "Voyage",  "Numéro voyage",  data1.get("numero_voyage"), data2.get("numero_voyage"))
    _add("Général", "ETA",     "Date d'arrivée", data1.get("eta"),           data2.get("eta"))

    # ── 1.5 Comparaison des Ports ───────────────────────────────────────────
    ports1 = set(data1.get("ports", {}).keys())
    ports2 = set(data2.get("ports", {}).keys())
    all_ports = sorted(ports1 | ports2)
    
    for port in all_ports:
        if port not in ports1:
            _add("Général", port, "Présence Port", f"Manquant dans {label1}", f"Présent dans {label2}")
        elif port not in ports2:
            _add("Général", port, "Présence Port", f"Présent dans {label1}", f"Manquant dans {label2}")

    # ── 2. Construire un index plat BL_REF -> bl_data pour chaque doc ──────
    # On ignore le niveau "port" pour l'appariement : on compare BL par BL_REF
    def _flat_bls(data: dict) -> dict:
        """Retourne {bl_ref: (pol, bl_data)} depuis toute la structure ports."""
        result = {}
        for pol, port_data in data.get("ports", {}).items():
            for bl_ref, bl_data in port_data.get("bls", {}).items():
                result[bl_ref] = (pol, bl_data)
        return result

    bls1 = _flat_bls(data1)
    bls2 = _flat_bls(data2)

    aligned_bls1 = dict(bls1)
    aligned_bls2 = dict(bls2)

    for b1 in list(aligned_bls1.keys()):
        for b2 in list(aligned_bls2.keys()):
            if b1 != b2:
                if len(b1) < len(b2) and b1 in b2:
                    aligned_bls1[b2] = aligned_bls1.pop(b1)
                elif len(b2) < len(b1) and b2 in b1:
                    aligned_bls2[b1] = aligned_bls2.pop(b2)

    all_bls = sorted(set(list(aligned_bls1.keys()) + list(aligned_bls2.keys())))

    for bl_ref in all_bls:
        ctx_bl = f"BL"

        # BL présent dans un seul doc
        if bl_ref not in aligned_bls1:
            _add(ctx_bl, bl_ref, "Présence BL",
                 f"Manquant dans {label1}", f"Présent dans {label2}")
            continue
        if bl_ref not in aligned_bls2:
            _add(ctx_bl, bl_ref, "Présence BL",
                 f"Présent dans {label1}", f"Manquant dans {label2}")
            continue

        pol1, b1 = aligned_bls1[bl_ref]
        pol2, b2 = aligned_bls2[bl_ref]

        # Port de chargement
        _add(ctx_bl, bl_ref, "Port", pol1, pol2)

        # Acteurs logistics
        _add(ctx_bl, bl_ref, "Shipper",   b1.get("shipper"),   b2.get("shipper"))
        _add(ctx_bl, bl_ref, "Consignee", b1.get("consignee"), b2.get("consignee"))
        _add(ctx_bl, bl_ref, "Notify",    b1.get("notify"),    b2.get("notify"))

        # Désignation marchandise
        _add(ctx_bl, bl_ref, "Désignation", b1.get("designation"), b2.get("designation"))

        # ── 3. Comparaison des conteneurs ─────────────────────────────────
        cts1 = b1.get("conteneurs", {})
        cts2 = b2.get("conteneurs", {})

        # Tentative d'alignement des numéros de conteneurs tronqués (ex: OCU49138 vs OOCU4913816)
        aligned_cts1 = dict(cts1)
        aligned_cts2 = dict(cts2)

        for c1 in list(aligned_cts1.keys()):
            for c2 in list(aligned_cts2.keys()):
                if c1 != c2:
                    if len(c1) < len(c2) and c1 in c2:
                        aligned_cts1[c2] = aligned_cts1.pop(c1)
                    elif len(c2) < len(c1) and c2 in c1:
                        aligned_cts2[c1] = aligned_cts2.pop(c2)

        all_cts = sorted(set(list(aligned_cts1.keys()) + list(aligned_cts2.keys())))

        for ct_num in all_cts:
            ctx_ct = f"Conteneur (BL: {bl_ref})"

            if ct_num not in aligned_cts1:
                _add(ctx_ct, ct_num, "Présence conteneur",
                     f"Manquant dans {label1}", f"Présent dans {label2}")
                continue
            if ct_num not in aligned_cts2:
                _add(ctx_ct, ct_num, "Présence conteneur",
                     f"Présent dans {label1}", f"Manquant dans {label2}")
                continue

            c1 = aligned_cts1[ct_num]
            c2 = aligned_cts2[ct_num]

            _add(ctx_ct, ct_num, "Type conteneur", c1.get("type"),       c2.get("type"))
            _add(ctx_ct, ct_num, "Plomb / Scellé", c1.get("num_plomb"),  c2.get("num_plomb"))
            _add(ctx_ct, ct_num, "Nombre de colis",
                 c1.get("nbre_colis"), c2.get("nbre_colis"))
            _add(ctx_ct, ct_num, "Poids brut (kg)",
                 c1.get("poids_brut"), c2.get("poids_brut"))
            _add(ctx_ct, ct_num, "Volume", 
                 c1.get("volume"), c2.get("volume"))

    return diffs
