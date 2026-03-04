"""
parser_xml.py
-------------
Parse un fichier XML douanier (SYDAM) et retourne un dict conforme
au plan JSON (PlanJson.docx).

Structure de sortie :
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
"""

import xmltodict


def parse_xml(xml_content) -> dict:
    """
    Parse un XML SYDAM et retourne un dict conforme au plan JSON.
    xml_content : bytes ou str.
    """
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8")

    doc = xmltodict.parse(xml_content)

    result = {
        "navire":        None,
        "numero_voyage": None,
        "eta":           None,
        "ports":         {}
    }

    # ── En-tête général ───────────────────────────────────────────────────
    root = doc.get("manifest", doc)
    general = root.get("manifest_general_segment", {})
    if not isinstance(general, dict):
        general = {}

    result["navire"]        = (general.get("transport_identity")
                               or general.get("callsign")
                               or None)
    result["numero_voyage"] = general.get("manifest_voyage_number") or None
    result["eta"]           = general.get("estimated_date_of_arrival") or None

    # ── BLs (waybills) ────────────────────────────────────────────────────
    waybills_node = root.get("waybills", {}).get("waybill", [])
    if isinstance(waybills_node, dict):
        waybills_node = [waybills_node]

    for wb in waybills_node:
        # Port de chargement (POL) → on utilise place_of_loading ou loading_port
        pol = (wb.get("place_of_loading_code")
               or wb.get("loading_port")
               or wb.get("port_of_loading_code")
               or "INCONNU")

        bl_ref = wb.get("waybill_reference_number", "BL_INCONNU")

        # Acteurs logistiques
        shipper    = wb.get("exporter_name")   or wb.get("shipper_name")   or None
        consignee  = wb.get("consignee_name")  or None
        notify     = wb.get("notify_name")     or None
        designation = wb.get("description_of_goods") or wb.get("goods_description") or None

        # ── Conteneurs ────────────────────────────────────────────────────
        containers_node = wb.get("containers", {}).get("container", [])
        if isinstance(containers_node, dict):
            containers_node = [containers_node]

        conteneurs = {}
        for ct in containers_node:
            ct_num = ct.get("container_number", "CONT_INCONNU")

            # Poids brut
            try:
                poids = float(ct.get("goods_weight", 0) or 0)
            except (ValueError, TypeError):
                poids = 0.0

            # Nombre de colis
            try:
                nb_colis = int(ct.get("number_of_packages")
                               or wb.get("manifested_packages")
                               or 0)
            except (ValueError, TypeError):
                nb_colis = 0

            # Volume
            try:
                volume = float(ct.get("volume", 0) or 0) or None
            except (ValueError, TypeError):
                volume = None

            conteneurs[ct_num] = {
                "type":       str(ct.get("container_type", "") or ""),
                "num_plomb":  str(ct.get("seals_number", "") or ""),
                "nbre_colis": nb_colis,
                "poids_brut": poids,
                "volume":     volume
            }

        # ── Insertion dans result ─────────────────────────────────────────
        if pol not in result["ports"]:
            result["ports"][pol] = {"bls": {}}

        result["ports"][pol]["bls"][bl_ref] = {
            "shipper":     shipper,
            "consignee":   consignee,
            "notify":      notify,
            "designation": designation,
            "conteneurs":  conteneurs
        }

    return result
