from parser_cargo import parse_cargo

def test_cargo_shipper_extraction_layout():
    # Avec l'ancien parseur, l'utilisation de layout=True briserait la logique de ' . ' pour séparer les colonnes
    c = parse_cargo("CARGO ZOI.pdf")
    bl = list(list(c["ports"].values())[0]["bls"].values())[0]
    shipper = bl.get("shipper", "")
    
    # On s'assure qu'on n'a pas inclus la colonne de droite "VOLUME:" ou "KG" dans le shipper
    assert "VOLUME" not in shipper
    assert len(shipper) > 10, "Shipper doit être trouvé correctement"
