def reconcile_manifests(data1, data2, label1="Valeur 1", label2="Valeur 2"):
    """
    Compare les deux dictionnaires et retourne une liste de diff\N{LATIN SMALL LETTER E}rences pr\N{LATIN SMALL LETTER E}tes \N{LATIN SMALL LETTER A} \N{LATIN SMALL LETTER E}tre transform\N{LATIN SMALL LETTER E}es en DataFrame.
    """
    diffs = []
    
    def compare(contexte, identifiant, champ, v1, v2):
        # Conversion en cha\N{LATIN SMALL LETTER I}ne pour s\N{LATIN SMALL LETTER E}curiser la comparaison
        s1 = str(v1).strip().upper() if v1 is not None else ""
        s2 = str(v2).strip().upper() if v2 is not None else ""
        
        # Sauf pour les nombres pures (comme le poids)
        if isinstance(v1, float) or isinstance(v2, float):
            try:
                # Tol\N{LATIN SMALL LETTER E}rance de 0.01 pour les erreurs d'arrondis
                if abs(float(v1) - float(v2)) > 0.01:
                     diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, label1: v1, label2: v2})
            except ValueError:
                if s1 != s2:
                    diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, label1: v1, label2: v2})
        else:
            if s1 != s2:
                diffs.append({"Contexte": contexte, "Identifiant": identifiant, "Champ": champ, label1: s1, label2: s2})

    # 1. Comparaison Globale Navire
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Nom (Callsign/Vessel)", data1.get("navire_nom"), data2.get("navire_nom", "INCONNU"))
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Num\N{LATIN SMALL LETTER E}ro Voyage", data1.get("navire_voyage"), data2.get("navire_voyage", "INCONNU"))
    compare("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ral", "Navire", "Date ETA / Call Date", data1.get("navire_eta"), data2.get("navire_eta", "INCONNU"))
    
    # R\N{LATIN SMALL LETTER E}cup\N{LATIN SMALL LETTER E}ration des ports
    ports1 = data1.get("ports", {})
    ports2 = data2.get("ports", {})
    
    all_ports = set(list(ports1.keys()) + list(ports2.keys()))
    
    for port in all_ports:
        p1 = ports1.get(port, {})
        p2 = ports2.get(port, {})
        
        # 2. Comparaison Aggr\N{LATIN SMALL LETTER E}gation Port (Poids brut total)
        ctx_port = "Aggr\N{LATIN SMALL LETTER E}gation Port"
        if not p1:
            compare(ctx_port, port, "Pr\N{LATIN SMALL LETTER E}sence du port", f"Manquant en {label1}", "Pr\N{LATIN SMALL LETTER E}sent")
            continue
        if not p2:
            compare(ctx_port, port, "Pr\N{LATIN SMALL LETTER E}sence du port", "Pr\N{LATIN SMALL LETTER E}sent", f"Manquant en {label2}")
            continue
            
        compare(ctx_port, port, "Poids Brut Total", p1.get("poids_brut_total", 0), p2.get("poids_brut_total", 0))

        # 3. Comparaison BLs
        bls1 = p1.get("bls", {})
        bls2 = p2.get("bls", {})
        
        all_bls = set(list(bls1.keys()) + list(bls2.keys()))
        for bl in all_bls:
            b1 = bls1.get(bl, {})
            b2 = bls2.get(bl, {})
            
            ctx_bl = f"Port: {port} | BL"
            
            if not b1:
                compare(ctx_bl, bl, "Pr\N{LATIN SMALL LETTER E}sence BL", f"Manquant en {label1}", f"Pr\N{LATIN SMALL LETTER E}sent dans {label2}")
                continue
            if not b2:
                compare(ctx_bl, bl, "Pr\N{LATIN SMALL LETTER E}sence BL", f"Pr\N{LATIN SMALL LETTER E}sent dans {label1}", f"Manquant dans {label2}")
                continue
                
            compare(ctx_bl, bl, "Consignee", b1.get("consignee"), b2.get("consignee"))
            compare(ctx_bl, bl, "Shipper", b1.get("shipper"), b2.get("shipper"))
            compare(ctx_bl, bl, "Notify", b1.get("notify"), b2.get("notify"))
            
            # 4. Comparaison Conteneurs
            ct1 = b1.get("conteneurs", {})
            ct2 = b2.get("conteneurs", {})
            
            all_cts = set(list(ct1.keys()) + list(ct2.keys()))
            for ct in all_cts:
                c1 = ct1.get(ct, {})
                c2 = ct2.get(ct, {})
                
                ctx_ct = f"Port: {port} | BL: {bl} | Conteneur"
                
                if not c1:
                    compare(ctx_ct, ct, "Pr\N{LATIN SMALL LETTER E}sence Conteneur", f"Manquant en {label1}", f"Pr\N{LATIN SMALL LETTER E}sent dans {label2}")
                    continue
                if not c2:
                    compare(ctx_ct, ct, "Pr\N{LATIN SMALL LETTER E}sence Conteneur", f"Pr\N{LATIN SMALL LETTER E}sent dans {label1}", f"Manquant dans {label2}")
                    continue
                    
                compare(ctx_ct, ct, "Plomb (Seal)", c1.get("plomb"), c2.get("plomb"))
                compare(ctx_ct, ct, "Type", c1.get("type"), c2.get("type"))
                compare(ctx_ct, ct, "Poids Brut", c1.get("poids_brut"), c2.get("poids_brut"))

    return diffs
