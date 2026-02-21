import xmltodict

def parse_xml(xml_content):
    """
    Extrait les informations cl\N{LATIN SMALL LETTER E}s d'un XML conform\N{LATIN SMALL LETTER E}ment au sch\N{LATIN SMALL LETTER E}ma douanier.
    """
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode('utf-8')
    
    # Parser strict avec xmltodict, qui transforme le XML en dictionnaire Python
    doc = xmltodict.parse(xml_content)
    
    data = {}
    
    # 1. Informations G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rales Navire
    # On cherche le noeud 'manifest_general_segment', soit \N{LATIN SMALL LETTER A} la racine, soit sous 'manifest'
    general = doc.get("manifest", doc).get("manifest_general_segment", {})
    if not isinstance(general, dict) and 'manifest_general_segment' in doc:
        general = doc['manifest_general_segment']
        
    data["navire_nom"] = general.get("callsign", "")
    data["navire_nom_alt"] = general.get("transport_identity", "")
    data["navire_voyage"] = general.get("manifest_voyage_number", "")
    data["navire_eta"] = general.get("estimated_date_of_arrival", "")
    data["ports"] = {}
    
    # 2. Informations Waybills (BLs)
    waybills_node = doc.get("manifest", doc).get("waybills", {}).get("waybill", [])
    # Si dictionnaire, c'est qu'il n'y a qu'un seul BL, on le transforme en liste
    if isinstance(waybills_node, dict):
        waybills_node = [waybills_node]
        
    for wb in waybills_node:
        port_unloading = wb.get("place_of_unloading_code", "PORT_INCONNU")
        
        # Initialisation du port si inxistant
        if port_unloading not in data["ports"]:
            data["ports"][port_unloading] = {"poids_brut_total": 0.0, "bls": {}}
            
        bl_ref = wb.get("waybill_reference_number", "BL_INCONNU")
        bl_data = {
            "consignee": wb.get("consignee_name", ""),
            "shipper": wb.get("exporter_name", ""),
            "notify": wb.get("notify_name", ""),
            "marchandise": wb.get("description_of_goods", ""),
            "conteneurs": {}
        }
        
        # 3. Informations Conteneurs
        containers_node = wb.get("containers", {}).get("container", [])
        if isinstance(containers_node, dict):
            containers_node = [containers_node]
            
        for ct in containers_node:
            ct_num = ct.get("container_number", "CONT_INCONNU")
            
            poids_brut_str = ct.get("goods_weight", "0")
            try:
                poids_brut = float(poids_brut_str)
            except ValueError:
                poids_brut = 0.0
                
            # Aggr\N{LATIN SMALL LETTER E}gation pour le port
            data["ports"][port_unloading]["poids_brut_total"] += poids_brut
                
            bl_data["conteneurs"][ct_num] = {
                "plomb": ct.get("seals_number", ""),
                "type": ct.get("container_type", ""),
                "poids_brut": poids_brut,
                "volume": ct.get("volume", ""), # Peut \N{LATIN SMALL LETTER E}tre vide
                "package": wb.get("package_code", ""), # Souvent d\N{LATIN SMALL LETTER E}clar\N{LATIN SMALL LETTER E} au niveau du BL
                "nombre_colis": ct.get("number_of_packages", wb.get("manifested_packages", ""))
            }
            
        data["ports"][port_unloading]["bls"][bl_ref] = bl_data
        
    return data
