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
**XML vs PDF** ou **PDF vs PDF** !
""", unsafe_allow_html=True)

mode = st.radio("Mode de comparaison :", ["XML vs PDF", "PDF vs PDF"], horizontal=True)

col1, col2 = st.columns(2)

if mode == "XML vs PDF":
    with col1:
        file1 = st.file_uploader("Charger le fichier XML", type=['xml'])
    with col2:
        file2 = st.file_uploader("Charger le fichier PDF", type=['pdf'])
else:
    with col1:
        file1 = st.file_uploader("Charger le Premier fichier PDF", type=['pdf'])
    with col2:
        file2 = st.file_uploader("Charger le Second fichier PDF", type=['pdf'])

st.write("") # Espace
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

with col_btn2:
    btn_lancer = st.button("Lancer la R\N{LATIN SMALL LETTER E}conciliation", type="primary", use_container_width=True)

if btn_lancer:
    if not file1 or not file2:
        st.error("Veuillez charger les deux fichiers avant de lancer la r\N{LATIN SMALL LETTER E}conciliation.")
    else:
        with st.spinner("Analyse et extraction des donn\N{LATIN SMALL LETTER E}es en cours..."):
            try:
                if mode == "XML vs PDF":
                    # Lecture du XML en mémoire
                    xml_content = file1.read()
                    
                    # Extraction
                    st.info("Extraction XML...")
                    data1 = parse_xml(xml_content)
                    st.success("XML extrait avec succ\N{LATIN SMALL LETTER E}s !")
                    
                    st.info("Extraction PDF...")
                    data2 = parse_pdf_text(file2)
                    st.success("PDF extrait avec succ\N{LATIN SMALL LETTER E}s !")
                    
                    label1, label2 = "Valeur XML", "Valeur PDF"
                    
                else:
                    st.info("Extraction PDF 1...")
                    data1 = parse_pdf_text(file1)
                    st.success("PDF 1 extrait avec succ\N{LATIN SMALL LETTER E}s !")
                    
                    st.info("Extraction PDF 2...")
                    data2 = parse_pdf_text(file2)
                    st.success("PDF 2 extrait avec succ\N{LATIN SMALL LETTER E}s !")
                    
                    label1, label2 = "Valeur PDF 1", "Valeur PDF 2"

                # R\N{LATIN SMALL LETTER E}conciliation
                st.info("Comparaison des donn\N{LATIN SMALL LETTER E}es...")
                differences = reconcile_manifests(data1, data2, label1, label2)
                
                st.subheader("📊 R\N{LATIN SMALL LETTER E}sultats de la comparaison")
                
                if not differences:
                    st.success("Aucune diff\N{LATIN SMALL LETTER E}rence majeure trouv\N{LATIN SMALL LETTER E}e entre les deux fichiers !")
                else:
                    st.warning(f"⚠️ {len(differences)} diff\N{LATIN SMALL LETTER E}rences trouv\N{LATIN SMALL LETTER E}es.")
                    df_diff = pd.DataFrame(differences)
                    
                    # R\N{LATIN SMALL LETTER E}organisation des colonnes pour la clart\N{LATIN SMALL LETTER E}
                    cols = ["Contexte", "Identifiant", "Champ", label1, label2]
                    df_diff = df_diff[[c for c in cols if c in df_diff.columns]]
                    
                    st.dataframe(df_diff, use_container_width=True)
                    
                    # Export CSV
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
