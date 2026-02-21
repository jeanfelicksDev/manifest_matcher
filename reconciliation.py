def reconcile_manifests(xml_data, pdf_data):
    """
    Compare les deux dictionnaires et retourne une liste de diff\N{LATIN SMALL LETTER E}rences pr\N{LATIN SMALL LETTER E}tes \N{LATIN SMALL LETTER A} \N{LATIN SMALL LETTER E}tre transform\N{LATIN SMALL LETTER E}es en DataFrame.
    """
    diffs = []
    
    def compare(contexte, identifiant, champ, v_xml, v_pdf):
        # Conversion en cha\N{LATIN SMALL LETTER I}ne pour s\N{LATIN SMALL LETTER E}curiser la comparaison
        s_xml = str(v_xml).strip().upper() if v_xml is not None else ""
        s_pdf = str(v_pdf).strip().upper() if v_pdf is not None else ""
        
        # Sauf pour les nombres pures (comme le poids)
        if isinstance(v_xml, float) or isinstance(v_pdf, float):
            try:
                # Tol\N{LATIN SMALL LETTER E}rance de 0.01 pour les erreurs d'arrondis
                if abs(float(v_xml) - float(v_pdf)) > 0.01:
                     diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, "Valeur XML": v_xml, "Valeur PDF": v_pdf})
            except ValueError:
                if s_xml != s_pdf:
                    diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, "Valeur XML": v_xml, "Valeur PDF": v_pdf})
        else:
            if s_xml != s_pdf:
                diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, "Valeur XML": s_xml, "Valeur PDF": s_pdf})

    # 1. Comparaison Globale Navire
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Nom (Callsign/Vessel)", xml_data.get("navire_nom"), pdf_data.get("navire_nom", "INCONNU"))
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Num\N{LATIN SMALL LETTER E}ro Voyage", xml_data.get("navire_voyage"), pdf_data.get("navire_voyage", "INCONNU"))
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Date ETA / Call Date", xml_data.get("navire_eta"), pdf_data.get("navire_eta", "INCONNU"))
    
    # R\N{LATIN SMALL LETTER E}cup\N{LATIN SMALL LETTER E}ration des ports
    ports_xml = xml_data.get("ports", {})
    ports_pdf = pdf_data.get("ports", {})
    
    all_ports = set(list(ports_xml.keys()) + list(ports_pdf.keys()))
    
    for port in all_ports:
        p_xml = ports_xml.get(port, {})
        p_pdf = ports_pdf.get(port, {})
        
        # 2. Comparaison Aggr\N{LATIN SMALL LETTER E}gation Port (Poids brut total)
        ctx_port = "Aggr\N{LATIN SMALL LETTER E}gation Port"
        if not p_xml:
            compare(ctx_port, port, "Pr\N{LATIN SMALL LETTER E}sence du port", "Manquant en XML", "Pr\N{LATIN SMALL LETTER E}sent")
            continue
        if not p_pdf:
            compare(ctx_port, port, "Pr\N{LATIN SMALL LETTER E}sence du port", "Pr\N{LATIN SMALL LETTER E}sent", "Manquant en PDF")
            continue
            
        compare(ctx_port, port, "Poids Brut Total", p_xml.get("poids_brut_total", 0), p_pdf.get("poids_brut_total", 0))

        # 3. Comparaison BLs
        bls_xml = p_xml.get("bls", {})
        bls_pdf = p_pdf.get("bls", {})
        
        # Dans le PDF partiel l'extraction du port peut diff\N{LATIN SMALL LETTER E}rer, mais s'ils sont dans le m\N{LATIN SMALL LETTER E}me port :
        all_bls = set(list(bls_xml.keys()) + list(bls_pdf.keys()))
        for bl in all_bls:
            b_xml = bls_xml.get(bl, {})
            b_pdf = bls_pdf.get(bl, {})
            
            ctx_bl = f"Port: {port} | BL"
            
            if not b_xml:
                compare(ctx_bl, bl, "Pr\N{LATIN SMALL LETTER E}sence BL", "Manquant en XML", "Pr\N{LATIN SMALL LETTER E}sent dans PDF")
                continue
            if not b_pdf:
                compare(ctx_bl, bl, "Pr\N{LATIN SMALL LETTER E}sence BL", "Pr\N{LATIN SMALL LETTER E}sent dans XML", "Manquant dans PDF")
                continue
                
            compare(ctx_bl, bl, "Consignee", b_xml.get("consignee"), b_pdf.get("consignee"))
            compare(ctx_bl, bl, "Shipper", b_xml.get("shipper"), b_pdf.get("shipper"))
            compare(ctx_bl, bl, "Notify", b_xml.get("notify"), b_pdf.get("notify"))
            
            # 4. Comparaison Conteneurs
            ct_xml = b_xml.get("conteneurs", {})
            ct_pdf = b_pdf.get("conteneurs", {})
            
            all_cts = set(list(ct_xml.keys()) + list(ct_pdf.keys()))
            for ct in all_cts:
                c_xml = ct_xml.get(ct, {})
                c_pdf = ct_pdf.get(ct, {})
                
                ctx_ct = f"Port: {port} | BL: {bl} | Conteneur"
                
                if not c_xml:
                    compare(ctx_ct, ct, "Pr\N{LATIN SMALL LETTER E}sence Conteneur", "Manquant en XML", "Pr\N{LATIN SMALL LETTER E}sent dans PDF")
                    continue
                if not c_pdf:
                    compare(ctx_ct, ct, "Pr\N{LATIN SMALL LETTER E}sence Conteneur", "Pr\N{LATIN SMALL LETTER E}sent dans XML", "Manquant dans PDF")
                    continue
                    
                compare(ctx_ct, ct, "Plomb (Seal)", c_xml.get("plomb"), c_pdf.get("plomb"))
                compare(ctx_ct, ct, "Type", c_xml.get("type"), c_pdf.get("type"))
                compare(ctx_ct, ct, "Poids Brut", c_xml.get("poids_brut"), c_pdf.get("poids_brut"))

    # Cas sp\N{LATIN SMALL LETTER E}cifique de d\N{LATIN SMALL LETTER E}calage de ports: 
    # Le PDF ne mentionne souvent qu'un seul port (en-t\N{LATIN SMALL LETTER E}te) alors que le XML ventile.
    # Dans ce cas, on regroupe les BL non trouv\N{LATIN SMALL LETTER E}s.
    
    return diffs

