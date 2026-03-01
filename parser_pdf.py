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
        
    m_voyage = re.search(r'Voyage\s*\.\.\.:\s*(\S+)', text)
    data["navire_voyage"] = m_voyage.group(1).strip() if m_voyage else "INCONNU"
        
    m_date = re.search(r'Call date\s*:\s*([\d\/]+)', text)
    data["navire_eta"] = m_date.group(1).strip() if m_date else "INCONNU"
    
    m_pol = re.search(r'Port of loading\s*\.\.\.:\s*(.*?)\s*$', text, re.MULTILINE)
    data["port_loading"] = m_pol.group(1).strip() if m_pol else "INCONNU"
    
    m_pol_global = re.search(r'Port of loading\s*\.\.\.:\s*(.*?)\s*$', text, re.MULTILINE)
    data["port_loading"] = m_pol_global.group(1).strip() if m_pol_global else "INCONNU"
    
    # 2. R\N{LATIN SMALL LETTER E}cup\N{LATIN SMALL LETTER E}ration des POL et POD au fil du document
    pols = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Port of loading\s*\.\.\.:\s*(.*?)\s*$', text, re.MULTILINE)]
    pods_discharge = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Port of discharge\s*:\s*(.*?)\s*$', text, re.MULTILINE)]
    pods_delivery = [(m.start(), m.group(1).strip()) for m in re.finditer(r'Place of delivery\s*:\s*(.*?)\s*$', text, re.MULTILINE)]
    
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
        # On cherche des num\N{LATIN SMALL LETTER E}ros de conteneurs classiques (ex: NIDU2356619)
        containers = {}
        cont_matches = re.finditer(r'!\s*([A-Z]{4}\d{7})\s*!\s*(.*?)\s*TARE!\s*([\d\.]+)?', block)
        
        for c in cont_matches:
            c_num = c.group(1)
            desc_type = c.group(2).strip()
            
            # The matched weight here is TARE! weight, not gross weight.
            containers[c_num] = {
                "type": desc_type, 
                "poids_brut": 0.0, 
                "plomb": "", 
                "volume": "", 
                "package": "", 
                "nombre_colis": ""
            }
            
        # 5. Extraction compl\N{LATIN SMALL LETTER E}mentaire des conteneurs (Scell\N{LATIN SMALL LETTER E}s et Poids global en bas de bloc)
        for c_num in containers.keys():
            # Chercher le scell\N{LATIN SMALL LETTER E} associ\N{LATIN SMALL LETTER E} en dessous du conteneur dans l'affichage texte
            seal_m = re.search(c_num + r'[\s\S]*?SEAL\s+([A-Z0-9]+)', block)
            if seal_m: 
                containers[c_num]["plomb"] = seal_m.group(1)
                
            # Si le poids \N{LATIN SMALL LETTER E}tait vide \N{LATIN SMALL LETTER A} c\N{LATIN SMALL LETTER O}t\N{LATIN SMALL LETTER E} du TARE!, chercher "GW EXCL.CTR.TARE !"
            if containers[c_num]["poids_brut"] == 0.0:
                 gw_m = re.search(r'GW EXCL\.CTR\.TARE\s*!\s*([\d\.]+)', block)
                 if gw_m:
                     weight_gw = float(gw_m.group(1))
                     containers[c_num]["poids_brut"] = weight_gw
                     data["ports"][default_port]["poids_brut_total"] += weight_gw

        # Enregistrement final du BL
        data["ports"][default_port]["bls"][bl_ref] = {
            "pol": current_pol,
            "consignee": consignee,
            "shipper": shipper,
            "notify": notify,
            "marchandise": "Voir PDF",
            "conteneurs": containers
        }

    return data
