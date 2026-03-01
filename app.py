import streamlit as st
import pandas as pd
from parser_xml import parse_xml
from parser_pdf import parse_pdf_text
from reconciliation import reconcile_manifests
import io
from xhtml2pdf import pisa
from datetime import datetime

st.set_page_config(page_title="CONTROL FICHIER SYDAM", layout="wide")

# Injection de CSS personnalis\N{LATIN SMALL LETTER E} (Style "Duolingo")
st.markdown("""
<style>
    /* Arri\N{LATIN SMALL LETTER E}re-plan de la page complet et typographie */
    .stApp {
        background-color: #ffffff;
        font-family: 'Nunito', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        color: #4b4b4b;
    }

    /* Style du titre principal (Gros, rond, vert fonc\N{LATIN SMALL LETTER E} ou gris d\N{LATIN SMALL LETTER E}lav\N{LATIN SMALL LETTER E} comme Duolingo) */
    h1 {
        color: #3C3C3C;
        font-weight: 800 !important;
        text-align: center;
        letter-spacing: -0.5px;
        margin-bottom: 2rem !important;
    }
    
    /* Conteneurs secondaires et texte */
    .stMarkdown p {
        font-size: 1.1rem;
        line-height: 1.5;
        text-align: center;
        color: #777777;
    }

    /* Personnalisation des Widgets de File Uploader pour ressembler \N{LATIN SMALL LETTER A} des cartes Duolingo */
    [data-testid="stFileUploader"] {
        background-color: #f7f7f7;
        border: 2px dashed #cecece !important;
        border-radius: 16px !important;
        padding: 20px;
        transition: all 0.2s ease;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #58cc02 !important;
        background-color: #f1fbf0;
    }

    /* Bouton principal "Primary" - Style caract\N{LATIN SMALL LETTER E}ristique Duolingo (Vert vif avec ombre inf\N{LATIN SMALL LETTER E}rieure) */
    [data-testid="baseButton-primary"] {
        background-color: #58cc02 !important;
        color: white !important;
        font-weight:bold !important;
        font-size: 1.2rem !important;
        border-radius: 16px !important;
        border: none !important;
        padding: 15px 32px !important;
        box-shadow: 0px 4px 0px 0px #58a700 !important;
        transition: all 0.1s ease !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    [data-testid="baseButton-primary"]:active {
        transform: translateY(4px) !important;
        box-shadow: 0px 0px 0px 0px #58a700 !important;
    }
    
    [data-testid="baseButton-primary"]:hover {
        background-color: #61e002 !important;
    }
    
    /* Bouton Secondaire (Download) - Style Duolingo Bleu avec bordure foncée */
    [data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        color: #1cb0f6 !important;
        font-weight:bold !important;
        font-size: 1.1rem !important;
        border-radius: 16px !important;
        border: 2px solid #888888 !important;
        padding: 12px 24px !important;
        box-shadow: 0px 4px 0px 0px #cecece !important;
        transition: all 0.1s ease !important;
    }
    
    [data-testid="baseButton-secondary"]:active {
        transform: translateY(4px) !important;
        box-shadow: 0px 0px 0px 0px #cecece !important;
    }
    
    [data-testid="baseButton-secondary"]:hover {
        background-color: #f7f7f7 !important;
        border-color: #4b4b4b !important;
    }
    
    /* Rendre les cadres d'infos (alertes) plus doux */
    .stAlert {
        border-radius: 16px !important;
        border: 2px solid transparent !important;
    }
    .st-emotion-cache-1rqebx.e1tlf8w40 { /* Info standard */
        background-color: #ddf4ff !important;
        border-color: #84d8ff !important;
        color: #1cb0f6 !important;
    }
    .st-emotion-cache-10m60nw.e1tlf8w40 { /* Success */
        background-color: #d7ffb8 !important;
        border-color: #b7f582 !important;
        color: #58cc02 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("CONTROL FICHIER SYDAM")

st.markdown("""
Cette application compare deux manifestes pour relever les diff\N{LATIN SMALL LETTER E}rences en un clin d'\N{LATIN SMALL LETTER O}il : 
**XML vs PDF** ou **PDF vs PDF** ! Ou g\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rez un **RECAPITULATIF** depuis un PDF !
""", unsafe_allow_html=True)

mode = st.radio("Mode de fonctionnement :", ["XML vs PDF", "PDF vs PDF", "G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rer RECAP PDF"], horizontal=True)

type_recap = None
if mode == "G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rer RECAP PDF":
    type_recap = st.radio("Type de RECAP :", ["Export", "Import"], horizontal=True)

col1, col2 = st.columns(2)

if mode == "XML vs PDF":
    with col1:
        file1 = st.file_uploader("Charger le fichier XML", type=['xml'])
    with col2:
        file2 = st.file_uploader("Charger le fichier PDF", type=['pdf'])
elif mode == "PDF vs PDF":
    with col1:
        file1 = st.file_uploader("Charger le Premier fichier PDF", type=['pdf'])
    with col2:
        file2 = st.file_uploader("Charger le Second fichier PDF", type=['pdf'])
else:
    with col1:
        file_recap = st.file_uploader("Charger le fichier PDF pour le récapitulatif", type=['pdf'])
    with col2:
        date_signature = st.date_input("Date de signature pour le PDF", value=datetime.today(), format="DD/MM/YYYY")

st.write("") # Espace
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

with col_btn2:
    if mode == "G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rer RECAP PDF":
        btn_lancer = st.button("G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rer RECAP", type="primary", use_container_width=True)
    else:
        btn_lancer = st.button("Lancer la R\N{LATIN SMALL LETTER E}conciliation", type="primary", use_container_width=True)

if btn_lancer:
    if mode == "G\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}rer RECAP PDF":
        try:
            # Pour éviter NameError si file_recap n'est pas défini hors mode
            target_file = file_recap
        except NameError:
            target_file = None
            
        if not target_file:
            st.error("Veuillez charger le fichier PDF.")
        else:
            with st.spinner("Analyse et g\N{LATIN SMALL LETTER E}n\N{LATIN SMALL LETTER E}ration du RECAP en cours..."):
                try:
                    data = parse_pdf_text(target_file)
                    
                    recap_rows = []
                    
                    if type_recap == "Export":
                        # En Export: POL est toujours ABIDJAN, on groupe par POD (Destination)
                        pol_default = "ABIDJAN"
                        pod_groups = {}
                        hinterland_totals = {}
                        
                        for internal_pod, pod_data in data.get("ports", {}).items():
                            for bl_ref, bl_info in pod_data.get("bls", {}).items():
                                pod = internal_pod
                                dest = bl_info.get("place_delivery")
                                bl_w = float(sum(c.get("poids_brut", 0.0) for c in bl_info.get("conteneurs", {}).values()))
                                
                                # Hinterland en Export: destination finale inland (rare mais possible)
                                # On ignore ABIDJAN et le port de déchargement lui-même
                                if dest and str(dest).strip().upper() not in ["", "ABIDJAN", pod.upper(), "PORT_INCONNU", "INCONNU", "NONE"]:
                                    clean_dest = str(dest).strip().upper()
                                    if "OOCL HOUSE" not in clean_dest and "LEVINGTON" not in clean_dest and "ABIDJAN PROD" not in clean_dest:
                                        hinterland_totals[clean_dest] = hinterland_totals.get(clean_dest, 0.0) + bl_w
                                
                                if pod not in pod_groups:
                                    pod_groups[pod] = {"bls": 0, "20'": 0, "40'": 0, "poids": 0.0}
                                
                                pod_groups[pod]["bls"] += 1
                                for c_num, c_info in bl_info.get("conteneurs", {}).items():
                                    ctype = str(c_info.get("type", "")).upper()
                                    if "20'" in ctype or "20 " in ctype:
                                        pod_groups[pod]["20'"] += 1
                                    elif "40'" in ctype or "40 " in ctype:
                                        pod_groups[pod]["40'"] += 1
                                    else:
                                        pod_groups[pod]["20'"] += 1
                                    pod_groups[pod]["poids"] += c_info.get("poids_brut", 0.0)
                        
                        for pod, g_data in pod_groups.items():
                            recap_rows.append({
                                "POL": pol_default,
                                "POD": pod,
                                "BL": g_data["bls"],
                                "20'": g_data["20'"],
                                "40'": g_data["40'"],
                                "POIDS (kgs)": f"{g_data['poids']:,.2f}".replace(",", " "),
                                "OBSERVATIONS": "",
                                "_raw_poids": g_data["poids"]
                            })
                    else: # Import
                        # En Import: POD est toujours ABIDJAN, on liste tous les POLs du document
                        pod = "ABIDJAN"
                        pol_groups = {}
                        hinterland_totals = {}
                        
                        for internal_pod, pod_data in data.get("ports", {}).items():
                            for bl_ref, bl_info in pod_data.get("bls", {}).items():
                                pol = bl_info.get("pol", "INCONNU")
                                dest = bl_info.get("place_delivery")
                                bl_w = float(sum(c.get("poids_brut", 0.0) for c in bl_info.get("conteneurs", {}).values()))
                                
                                if dest and str(dest).strip().upper() not in ["", "ABIDJAN", "PORT_INCONNU", "INCONNU", "NONE"]:
                                    clean_dest = str(dest).strip().upper()
                                    if "OOCL HOUSE" not in clean_dest and "LEVINGTON" not in clean_dest and "ABIDJAN PROD" not in clean_dest:
                                        hinterland_totals[clean_dest] = hinterland_totals.get(clean_dest, 0.0) + bl_w
                                
                                if pol not in pol_groups:
                                    pol_groups[pol] = {"bls": 0, "20'": 0, "40'": 0, "poids": 0.0}
                                
                                pol_groups[pol]["bls"] += 1
                                
                                for c_num, c_info in bl_info.get("conteneurs", {}).items():
                                    ctype = str(c_info.get("type", "")).upper()
                                    if "20'" in ctype or "20 " in ctype:
                                        pol_groups[pol]["20'"] += 1
                                    elif "40'" in ctype or "40 " in ctype:
                                        pol_groups[pol]["40'"] += 1
                                    else:
                                        pol_groups[pol]["20'"] += 1
                                    
                                    # Additionner le poids par conteneur pour ce POL
                                    pol_groups[pol]["poids"] += c_info.get("poids_brut", 0.0)
                        
                        for pol, group_data in pol_groups.items():
                            recap_rows.append({
                                "POL": pol,
                                "POD": pod,
                                "BL": group_data["bls"],
                                "20'": group_data["20'"],
                                "40'": group_data["40'"],
                                "POIDS (kgs)": f'{group_data["poids"]:,.2f}'.replace(",", " "),
                                "OBSERVATIONS": "",
                                "_raw_poids": group_data["poids"]
                            })
                        
                    if recap_rows:
                        total_bl = sum(r["BL"] for r in recap_rows)
                        total_20 = sum(r["20'"] for r in recap_rows)
                        total_40 = sum(r["40'"] for r in recap_rows)
                        total_poids = sum(r["_raw_poids"] for r in recap_rows)
                        
                        # Remplissage des Hinterlands dans les colonnes OBSERVATIONS, ligne par ligne
                        hinterland_lines = []
                        tot_hint_global = 0.0
                        if hinterland_totals:
                            for dist, wg in hinterland_totals.items():
                                hinterland_lines.append(f"Total {dist} : {wg:,.2f}".replace(",", " "))
                                tot_hint_global += wg
                            if tot_hint_global > 0:
                                hinterland_lines.append(f"TOTAL HINTERLAND : {tot_hint_global:,.2f}".replace(",", " "))
                        
                        # Ajout du Total ABIDJAN
                        tot_abidjan = total_poids - tot_hint_global
                        hinterland_lines.append("") # Ligne vide pour aérer
                        hinterland_lines.append(f"TOTAL ABIDJAN : {tot_abidjan:,.2f}".replace(",", " "))
                        
                        obs_text = "\n\n".join(hinterland_lines)
                        if recap_rows:
                            recap_rows[0]["OBSERVATIONS"] = obs_text
                        for i in range(1, len(recap_rows)):
                            recap_rows[i]["OBSERVATIONS"] = ""
                                
                        for row in recap_rows:
                            del row["_raw_poids"]
                            
                        # Sauvegarde des données intactes pour le CSV
                        export_rows = list(recap_rows)

                        # Ligne de total
                        total_row = {
                            "POL": "TOTAL",
                            "POD": "",
                            "BL": total_bl,
                            "20'": total_20,
                            "40'": total_40,
                            "POIDS (kgs)": f"{total_poids:,.2f}".replace(",", " "),
                            "OBSERVATIONS": "*******************"
                        }
                        export_rows.append(total_row)
                        
                        df_recap = pd.DataFrame(export_rows)
                        st.subheader(f"📊 RECAPITULATIF ({type_recap.upper()})")
                        
                        # Générer tableau HTML avec rowspan pour centrer verticalement les fusions
                        pol_spans = [1] * len(recap_rows)
                        pod_spans = [1] * len(recap_rows)
                        
                        for i in range(len(recap_rows) - 1, 0, -1):
                            if recap_rows[i]["POL"] == recap_rows[i-1]["POL"]:
                                pol_spans[i-1] += pol_spans[i]
                                pol_spans[i] = 0
                            if recap_rows[i]["POD"] == recap_rows[i-1]["POD"]:
                                pod_spans[i-1] += pod_spans[i]
                                pod_spans[i] = 0
                                
                        html = "<table style='width: 60%; margin-left: auto; margin-right: auto; border-collapse: collapse; text-align: center; margin-bottom: 20px; font-size: 0.9rem; color: #4b4b4b; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.1); border: 1px solid #a0a0a0;'>"
                        html += "<thead><tr style='background-color: #f7f7f7; color: #3C3C3C; border-bottom: 2px solid #888888;'>"
                        for col in ["POL", "POD", "BL", "20'", "40'", "POIDS (kgs)", "OBSERVATIONS"]:
                            width = ""
                            if col == "POL": width = "width: 100px;"
                            elif col == "POD": width = "width: 100px;"
                            elif col in ["BL", "20'", "40'"]: width = "width: 35px;"
                            elif col == "POIDS (kgs)": width = "width: 75px;"
                            elif col == "OBSERVATIONS": width = "width: 185px;"
                            html += f"<th style='padding: 12px; border: 1px solid #a0a0a0; {width}'>{col}</th>"
                        html += "</tr></thead><tbody>"
                        
                        for i, row in enumerate(recap_rows):
                            html += "<tr>"
                            if pol_spans[i] > 0:
                                html += f"<td rowspan='{pol_spans[i]}' style='padding: 12px; border: 1px solid #a0a0a0; vertical-align: middle; font-weight: bold; width: 100px;'>{row['POL']}</td>"
                            if pod_spans[i] > 0:
                                html += f"<td rowspan='{pod_spans[i]}' style='padding: 12px; border: 1px solid #a0a0a0; vertical-align: middle; font-weight: bold; width: 100px;'>{row['POD']}</td>"
                            
                            html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{row['BL']}</td>"
                            val20 = row.get("20'", "")
                            val40 = row.get("40'", "")
                            html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{val20}</td>"
                            html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{val40}</td>"
                            html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 75px;'>{row['POIDS (kgs)']}</td>"
                            
                            if i == 0:
                                obs_html = str(row['OBSERVATIONS']).replace('\n', '<br>')
                                html += f"<td rowspan='{len(recap_rows)}' style='padding: 12px; border: 1px solid #a0a0a0; vertical-align: middle; text-align: center; font-weight: bold; color: #4b4b4b; width: 185px;'>{obs_html}</td>"
                                
                            html += "</tr>"
                            
                        # Ajout Ligne Total HTML
                        html += f"<tr style='font-weight: bold; background-color: #f7f7f7;'>"
                        html += f"<td colspan='2' style='padding: 12px; border: 1px solid #a0a0a0; text-align: center; width: 200px;'>{total_row['POL']}</td>"
                        total20 = total_row.get("20'", "")
                        total40 = total_row.get("40'", "")
                        html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{total_row['BL']}</td>"
                        html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{total20}</td>"
                        html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 35px;'>{total40}</td>"
                        html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 75px;'>{total_row['POIDS (kgs)']}</td>"
                        html += f"<td style='padding: 12px; border: 1px solid #a0a0a0; width: 185px;'>{total_row['OBSERVATIONS']}</td>"
                        html += "</tr>"
                        
                        html += "</tbody></table>"
                        st.markdown(html, unsafe_allow_html=True)
                    

                        # Version du tableau pour le PDF (Pleine largeur pour le mode Paysage)
                        pdf_table_html = html.replace("width: 60%", "width: 100%")
                        
                        pdf_html = f"""
                        <html>
                        <head>
                        <style>
                            @page {{
                                size: a4 landscape;
                                margin: 1.5cm;
                            }}
                            body {{
                                font-family: Helvetica, Arial, sans-serif;
                                font-size: 10px;
                                color: #333333;
                            }}
                            table {{
                                border-collapse: collapse;
                                width: 100%;
                            }}
                            th {{
                                background-color: #f7f7f7;
                                color: #3C3C3C;
                                font-weight: bold;
                                text-align: center;
                                border: 1px solid #a0a0a0;
                                padding: 8px;
                            }}
                            td {{
                                border: 1px solid #a0a0a0;
                                text-align: center;
                                padding: 8px;
                                vertical-align: middle;
                            }}
                        </style>
                        </head>
                        <body>
                            <h2 style="color: #4b4b4b; text-align: left; margin-bottom: 20px; font-size: 18px;">RECAPITULATIF DES MARCHANDISES ({type_recap.upper()})</h2>
                            {pdf_table_html}
                            
                            <div style="text-align: right; margin-top: 50px; margin-right: 50px; font-size: 12px; color: #1a1a1a;">
                                <p style="margin-bottom: 60px;">Fait le : {date_signature.strftime('%d/%m/%Y')}</p>
                                <p><strong>Cachet et Signature</strong></p>
                            </div>
                        </body>
                        </html>
                        """
                    pdf_buffer = io.BytesIO()
                    pisa_status = pisa.CreatePDF(io.StringIO(pdf_html), dest=pdf_buffer)
                    pdf_bytes = pdf_buffer.getvalue()

                    if not pisa_status.err:
                        col_btn_dl1, col_btn_dl2, col_btn_dl3 = st.columns([1.5, 1, 1.5])
                        with col_btn_dl2:
                            st.download_button(
                                label="📄 Télécharger le RECAP (PDF - Paysage)",
                                data=pdf_bytes,
                                file_name='recap_manifeste.pdf',
                                mime='application/pdf',
                                use_container_width=True
                            )
                    else:
                        st.error("Erreur lors de la génération du PDF")
                except Exception as e:
                    st.error(f"Une erreur est survenue : {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    else:
        try:
            f1 = file1
            f2 = file2
        except NameError:
            f1 = None
            f2 = None
            
        if not f1 or not f2:
            st.error("Veuillez charger les deux fichiers avant de lancer la r\N{LATIN SMALL LETTER E}conciliation.")
        else:
            with st.spinner("Analyse et extraction des donn\N{LATIN SMALL LETTER E}es en cours..."):
                try:
                    if mode == "XML vs PDF":
                        xml_content = f1.read()
                        st.info("Extraction XML...")
                        data1 = parse_xml(xml_content)
                        st.success("XML extrait avec succ\N{LATIN SMALL LETTER E}s !")
                        
                        st.info("Extraction PDF...")
                        data2 = parse_pdf_text(f2)
                        st.success("PDF extrait avec succ\N{LATIN SMALL LETTER E}s !")
                        
                        label1, label2 = "Valeur XML", "Valeur PDF"
                    else:
                        st.info("Extraction PDF 1...")
                        data1 = parse_pdf_text(f1)
                        st.success("PDF 1 extrait avec succ\N{LATIN SMALL LETTER E}s !")
                        
                        st.info("Extraction PDF 2...")
                        data2 = parse_pdf_text(f2)
                        st.success("PDF 2 extrait avec succ\N{LATIN SMALL LETTER E}s !")
                        
                        label1, label2 = "Valeur PDF 1", "Valeur PDF 2"

                    st.info("Comparaison des donn\N{LATIN SMALL LETTER E}es...")
                    differences = reconcile_manifests(data1, data2, label1, label2)
                    
                    st.subheader("📊 R\N{LATIN SMALL LETTER E}sultats de la comparaison")
                    
                    if not differences:
                        st.success("Aucune diff\N{LATIN SMALL LETTER E}rence majeure trouv\N{LATIN SMALL LETTER E}e entre les deux fichiers !")
                    else:
                        st.warning(f"⚠️ {len(differences)} diff\N{LATIN SMALL LETTER E}rences trouv\N{LATIN SMALL LETTER E}es.")
                        df_diff = pd.DataFrame(differences)
                        
                        cols = ["Contexte", "Identifiant", "Champ", label1, label2]
                        df_diff = df_diff[[c for c in cols if c in df_diff.columns]]
                        
                        st.dataframe(df_diff, use_container_width=True)
                        
                        csv = df_diff.to_csv(index=False, sep=';').encode('utf-8-sig')
                        st.download_button(
                            label="📥 T\N{LATIN SMALL LETTER E}l\N{LATIN SMALL LETTER E}charger le r\N{LATIN SMALL LETTER E}sum\N{LATIN SMALL LETTER E} des diff\N{LATIN SMALL LETTER E}rences (CSV)",
                            data=csv,
                            file_name='differences_manifeste.csv',
                            mime='text/csv',
                        )
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de l'analyse : {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
