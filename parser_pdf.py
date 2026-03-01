import re
import pdfplumber

def parse_pdf_text(file_obj):
    """
    Extrait les donn\N{LATIN SMALL LETTER E}es d'un vrai fichier PDF en extrayant son contenu texte avec pdfplumber.
    """
    
    # 0. Lecture du PDF avec pdfplumber
    text = ""
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    data = {"ports": {}}
    
    # 1. En-t\N{LATIN SMALL LETTER E}te global (Navire, Voyage, Date)
    m_vessel = re.search(r'Vessel\s*:\s*(\S.*?)\s+Call date', text)
    data["navire_nom"] = m_vessel.group(1).strip() if m_vessel else "INCONNU"
        
    m_voyage = re.search(r'Voyage[\.\s]*:\s*(\S+)', text)
    data["navire_voyage"] = m_voyage.group(1).strip() if m_voyage else "INCONNU"
        
    m_date = re.search(r'Call date[\.\s]*:\s*([\d\/]+)', text)
    data["navire_eta"] = m_date.group(1).strip() if m_date else "INCONNU"
    
    m_pol = re.search(r'Port of loading[\.\s]*:\s*(.*?)\s*$', text, re.MULTILINE)
    data["port_loading"] = m_pol.group(1).strip() if m_pol else "INCONNU"
    
    m_pol_global = re.search(r'Port of loading[\.\s]*:\s*(.*?)\s*$', text, re.MULTILINE)
    data["port_loading"] = m_pol_global.group(1).strip() if m_pol_global else "INCONNU"
    
    # 2. R\N{LATIN SMALL LETTER E}cup\N{LATIN SMALL LETTER E}ration des POL et POD au fil du document
    pols = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Port of loading[\.\s]*:\s*(.*?)\s*$', text, re.MULTILINE)]
    pods_discharge = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Port of discharge[\.\s]*:\s*(.*?)\s*$', text, re.MULTILINE)]
    pods_delivery = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Place of delivery[\.\s]*:\s*(.*?)\s*$', text, re.MULTILINE)]
    
    def get_latest(positions_list, max_pos, default="INCONNU"):
        latest = default
        for pos, val in positions_list:
            if pos < max_pos:
                latest = val
            else:
                break
        return latest

    # 3. S\N{LATIN SMALL LETTER E}paration par Bloc de BL 
    bl_blocks = re.split(r'!(?=[A-Z0-9]{8,15}\s*!\s*SH[ \t]+)', text)
    current_search_pos = 0
    
    for block in bl_blocks:
        block_pos = text.find(block, current_search_pos)
        if block_pos != -1:
            current_search_pos = block_pos
            
        bl_match = re.search(r'^([A-Z0-9]+)\s*!', block)
        if not bl_match: continue
        bl_ref = bl_match.group(1).strip()
        
        # D\N{LATIN SMALL LETTER E}duire le POL et POD pour ce BL sp\N{LATIN SMALL LETTER E}cifique
        current_pol = get_latest(pols, current_search_pos, data["port_loading"])
        
        port_delivery = get_latest(pods_delivery, current_search_pos, None)
        port_discharge = get_latest(pods_discharge, current_search_pos, "PORT_INCONNU")
        
        default_port = port_delivery if port_delivery else port_discharge
        
        if default_port not in data["ports"]:
            data["ports"][default_port] = {"poids_brut_total": 0.0, "bls": {}}
        
        # 3. Extraction des acteurs logistiques (Shipper, Consignee, Notify)
        shipper, consignee, notify = "", "", ""
        
        m_sh = re.search(r'!\s*SH[ \t]+(.*?)\s*!', block)
        if m_sh: shipper = m_sh.group(1).strip()
            
        m_co = re.search(r'!\s*CO[ \t]+(.*?)\s*!', block)
        if m_co: consignee = m_co.group(1).strip()
            
        m_no = re.search(r'!\s*NO[ \t]+(.*?)\s*!', block)
        if m_no: notify = m_no.group(1).strip()
            
        # 4. Conteneurs
        # On cherche des numéros de conteneurs classiques (ex: NIDU2356619) et on va essayer de capter la ligne correspondante
        containers = {}
        
        # Le pattern trouve le conteneur, sa taille, le mot TARE! et tente de capturer jusqu'au poids brut qui est en fin de ligne
        # Exemple ligne : ! OERU4177992 ! 1 40' REEFER HIGH C TARE! 5880.000 ! 28620.000 ! 50.000 !
        # ou !OOLU2318619192 ! ... ! TEMU6639268 ! 1 40' DRY ...
        cont_matches = re.finditer(r'!\s*([A-Z]{4}\d{7})\s*!\s*(.*?)\s*TARE!\s*([\d\.]+)\s*!\s*(.*?)(?=\n|!)', block)
        
        for c in cont_matches:
            c_num = c.group(1)
            desc_type = c.group(2).strip()
            # group 3 is Tare
            remainder = c.group(4).strip()
            
            # Essayer d'extraire le Gross Weight qui est généralement le bloc de chiffres suivant
            # Sauf si c'est vide, car on a géré le bloc global plus bas.
            poids_brut_indiv = 0.0
            
            # Dans le cas de l'image, c'est sur 2 lignes:
            # Ligne cont: ! OERU4177992 ! 1 40' REEFER HIGH C TARE! 5880.000 ! !
            # Ligne suivante: ! SEAL... ! ! 28620.000 ! 50.000
            
            containers[c_num] = {
                "type": desc_type, 
                "poids_brut": poids_brut_indiv, # On va le raffiner
                "plomb": "", 
                "volume": "", 
                "package": "", 
                "nombre_colis": ""
            }
            
        # 5. Extraction complémentaire (Scellés et Poids individuels multi-lignes)
        for c_num in containers.keys():
            # Chercher le scellé
            seal_m = re.search(c_num + r'[\s\S]*?SEAL\s+([A-Z0-9]+)', block)
            if seal_m: 
                containers[c_num]["plomb"] = seal_m.group(1)
                
            # Pour le poids brut spécifique au conteneur, souvent sur la ligne du conteneur ou la ligne "SEAL"
            # On découpe le bloc à partir de l'identifiant du conteneur
            c_start = block.find(c_num)
            if c_start != -1:
                # Chercher le bloc de texte juste après TARE! xxxx
                sub_block = block[c_start:c_start+300] # Limiter la recherche aux lignes avoisinantes
                
                # Le poids brut est l'avant-dernier nombre avec décimales sur ces colonnes de droite.
                # On va chercher un nombre du style 28620.000 aligné à droite
                # Pattern: ! (espaces blancs eventuels) nombre (espaces) ! nombre
                
                weights_m = re.findall(r'!\s*([\d\.]+)\s*!', sub_block)
                # TARE est souvent le premier, GW le second ou la ligne en dessous
                valeurs_possibles = []
                for w in weights_m:
                    try:
                        valf = float(w)
                        if valf > 0: valeurs_possibles.append(valf)
                    except: pass
                
                # Logique heuristique : le plus grand chiffre n'étant pas la tare (tare ~3000-6000)
                # Souvent situé après TARE! XXXX
                
                tare_m = re.search(r'TARE!\s*([\d\.]+)', sub_block)
                tare = float(tare_m.group(1)) if tare_m else 0.0
                
                for v in valeurs_possibles:
                    if v != tare and v > 100: # Un conteneur fait rarement moins de 100 kgs
                        containers[c_num]["poids_brut"] = v
                        break
                        
            # Si malgré cela on n'a rien, on se rabat sur le poids total du BL à la fin
            if containers[c_num]["poids_brut"] == 0.0:
                 gw_m = re.search(r'GW EXCL\.CTR\.TARE\s*!\s*([\d\.]+)', block)
                 if gw_m:
                     weight_gw = float(gw_m.group(1))
                     # Si n conteneurs, divisé équitablement ? Pour l'instant on affecte
                     containers[c_num]["poids_brut"] = weight_gw / len(containers)
                     
            data["ports"][default_port]["poids_brut_total"] += containers[c_num]["poids_brut"]

        # Enregistrement final du BL
        data["ports"][default_port]["bls"][bl_ref] = {
            "pol": current_pol,
            "place_delivery": port_delivery,
            "consignee": consignee,
            "shipper": shipper,
            "notify": notify,
            "marchandise": "Voir PDF",
            "conteneurs": containers
        }

    return data
