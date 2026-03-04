from parser_cargo import parse_cargo

def test_cargo_shipper_extraction_layout():
    # Avec l'ancien parseur, l'utilisation de layout=True briserait la logique de ' . ' pour séparer les colonnes
    c = parse_cargo("CARGO ZOI.pdf")
    bl = list(list(c["ports"].values())[0]["bls"].values())[0]
    shipper = bl.get("shipper", "")
    
    # On s'assure qu'on n'a pas inclus la colonne de droite "VOLUME:" ou "KG" dans le shipper
    assert "VOLUME" not in shipper
    assert len(shipper) > 10, "Shipper doit être trouvé correctement"
from parser_sydam import parse_sydam

def test_sydam_shipper_designation_separation():
    s = parse_sydam('SYDAM ZOI.pdf')
    bl = list(list(s['ports'].values())[0]['bls'].values())[0]
    shipper = bl.get('shipper', '')
    assert 'PLASTIC' not in shipper
    assert 'CONTAINS NO' not in shipper

