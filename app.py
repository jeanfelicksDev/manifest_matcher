import streamlit as st
import pandas as pd
from parser_xml import parse_xml
from parser_pdf import parse_pdf_text
from reconciliation import reconcile_manifests
import io

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
    
    /* Bouton Secondaire (Download) - Style Duolingo Bleu */
    [data-testid="baseButton-secondary"] {
        background-color: #1cb0f6 !important;
        color: white !important;
        font-weight:bold !important;
        font-size: 1.1rem !important;
        border-radius: 16px !important;
        border: none !important;
        padding: 12px 24px !important;
        box-shadow: 0px 4px 0px 0px #1899d6 !important;
        transition: all 0.1s ease !important;
    }
    
    [data-testid="baseButton-secondary"]:active {
        transform: translateY(4px) !important;
        box-shadow: 0px 0px 0px 0px #1899d6 !important;
    }
    
    [data-testid="baseButton-secondary"]:hover {
        background-color: #21bdfaf !important;
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
        file_recap = st.file_uploader("Charger le fichier PDF pour le r\N{LATIN SMALL LETTER E}capitulatif", type=['pdf'])

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
                    pol = data.get("port_loading", "INCONNU")
                    for pod, pod_data in data.get("ports", {}).items():
                        nb_bl = len(pod_data.get("bls", {}))
                        nb_20 = 0
                        nb_40 = 0
                        
                        for bl_ref, bl_info in pod_data.get("bls", {}).items():
                            for c_num, c_info in bl_info.get("conteneurs", {}).items():
                                ctype = str(c_info.get("type", "")).upper()
                                if "20'" in ctype or "20 " in ctype:
                                    nb_20 += 1
                                elif "40'" in ctype or "40 " in ctype:
                                    nb_40 += 1
                                else:
                                    # Fallback arbitraire si c'est indéterminé
                                    nb_20 += 1
                                    
                        poids = pod_data.get("poids_brut_total", 0.0)
                        
                        recap_rows.append({
                            "POL": pol,
                            "POD": pod,
                            "BL": nb_bl,
                            "20'": nb_20,
                            "40'": nb_40,
                            "POIDS (kgs)": f"{poids:,.2f}".replace(",", " "),
                            "OBSERVATIONS": ""
                        })
                        
                    if recap_rows:
                        total_bl = sum(r["BL"] for r in recap_rows)
                        total_20 = sum(r["20'"] for r in recap_rows)
                        total_40 = sum(r["40'"] for r in recap_rows)
                        total_poids = sum(pod_data.get("poids_brut_total", 0.0) for pod_data in data.get("ports", {}).values())
                        
                        recap_rows.append({
                            "POL": "TOTAL",
                            "POD": "",
                            "BL": total_bl,
                            "20'": total_20,
                            "40'": total_40,
                            "POIDS (kgs)": f"{total_poids:,.2f}".replace(",", " "),
                            "OBSERVATIONS": "*******************"
                        })
                        
                    df_recap = pd.DataFrame(recap_rows)
                    st.subheader("📝 RECAPITULATIF (MANIFESTE EXPORT COMPLEMENTAIRE)")
                    st.dataframe(df_recap, use_container_width=True)
                    
                    csv = df_recap.to_csv(index=False, sep=';').encode('utf-8-sig')
                    st.download_button(
                        label="📥 T\N{LATIN SMALL LETTER E}l\N{LATIN SMALL LETTER E}charger le RECAP (CSV)",
                        data=csv,
                        file_name='recap_manifeste.csv',
                        mime='text/csv',
                    )
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
