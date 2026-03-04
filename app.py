import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime
from xhtml2pdf import pisa

from parser_xml   import parse_xml
from parser_sydam import parse_sydam
from parser_cargo import parse_cargo
from reconciliation import reconcile_manifests

# ── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(page_title="CONTROL FICHIER SYDAM", layout="wide")

# ── CSS Duolingo ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800;900&display=swap');

    .stApp {
        background-color: #ffffff;
        font-family: 'Nunito', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        color: #4b4b4b;
    }
    h1 {
        color: #3C3C3C;
        font-weight: 800 !important;
        text-align: center;
        letter-spacing: -0.5px;
        margin-bottom: 2rem !important;
    }
    .stMarkdown p {
        font-size: 1.05rem;
        line-height: 1.5;
        text-align: center;
        color: #777777;
    }
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
    [data-testid="baseButton-primary"] {
        background-color: #58cc02 !important;
        color: white !important;
        font-weight: bold !important;
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
    [data-testid="baseButton-secondary"] {
        background-color: #ffffff !important;
        color: #1cb0f6 !important;
        font-weight: bold !important;
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
    .stAlert { border-radius: 16px !important; }

    /* Badge format PDF détecté */
    .badge-sydam {
        background: #fff3cd; color: #856404; border: 1px solid #ffc107;
        border-radius: 8px; padding: 4px 12px; font-weight: bold;
        display: inline-block; margin-bottom: 8px;
    }
    .badge-cargo {
        background: #d1ecf1; color: #0c5460; border: 1px solid #17a2b8;
        border-radius: 8px; padding: 4px 12px; font-weight: bold;
        display: inline-block; margin-bottom: 8px;
    }
    .badge-xml {
        background: #d4edda; color: #155724; border: 1px solid #28a745;
        border-radius: 8px; padding: 4px 12px; font-weight: bold;
        display: inline-block; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def detect_pdf_format(file_obj) -> str:
    """
    Détecte le format du PDF en lisant les premières lignes.
    Retourne 'sydam' ou 'cargo'.
    """
    import pdfplumber
    try:
        file_obj.seek(0)
        with pdfplumber.open(file_obj) as pdf:
            first_page = pdf.pages[0].extract_text() or ""
        file_obj.seek(0)

        first_upper = first_page[:500].upper()
        if "ORIENT OVERSEAS" in first_upper or "CARGO MANIFEST" in first_upper or "B/L NUMBER" in first_upper:
            return "cargo"
        return "sydam"
    except Exception:
        file_obj.seek(0)
        return "sydam"


def parse_pdf_auto(file_obj) -> tuple:
    """
    Détecte le format et parse le PDF avec le bon parseur.
    Retourne (data_dict, format_detected) où format_detected in ['sydam', 'cargo'].
    """
    fmt = detect_pdf_format(file_obj)
    file_obj.seek(0)
    if fmt == "cargo":
        return parse_cargo(file_obj), "cargo"
    return parse_sydam(file_obj), "sydam"


def _fmt_num(n: float) -> str:
    """Formate un nombre avec séparateur espace."""
    return f"{n:,.2f}".replace(",", " ")


# ─────────────────────────────────────────────────────────────────────────────
# Interface principale
# ─────────────────────────────────────────────────────────────────────────────

st.title("CONTROL FICHIER SYDAM")
st.markdown(
    "Comparez deux manifestes pour relever les différences en un clin d'œil : "
    "**XML vs PDF** ou **PDF vs PDF** ! Ou générez un **RÉCAPITULATIF** depuis un PDF !"
)

mode = st.radio(
    "Mode de fonctionnement :",
    ["XML vs PDF", "PDF vs PDF", "Générer RECAP PDF"],
    horizontal=True
)

type_recap = None
if mode == "Générer RECAP PDF":
    type_recap = st.radio("Type de RECAP :", ["Export", "Import"], horizontal=True)

col1, col2 = st.columns(2)

if mode == "XML vs PDF":
    with col1:
        file1 = st.file_uploader("Charger le fichier XML (SYDAM)", type=["xml"])
    with col2:
        file2 = st.file_uploader("Charger le fichier PDF (CARGO Manifest)", type=["pdf"])

elif mode == "PDF vs PDF":
    with col1:
        file1 = st.file_uploader("Charger le 1er PDF (SYDAM ou CARGO)", type=["pdf"])
    with col2:
        file2 = st.file_uploader("Charger le 2ème PDF (SYDAM ou CARGO)", type=["pdf"])
else:
    with col1:
        file_recap = st.file_uploader("Charger le fichier PDF pour le RÉCAPITULATIF", type=["pdf"])
    with col2:
        date_signature = st.date_input("Date de signature", value=datetime.today(), format="DD/MM/YYYY")

st.write("")
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    if mode == "Générer RECAP PDF":
        btn_lancer = st.button("Générer RECAP", type="primary", use_container_width=True)
    else:
        btn_lancer = st.button("Lancer la Réconciliation", type="primary", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Mode : Générer RECAP PDF
# ─────────────────────────────────────────────────────────────────────────────
if btn_lancer and mode == "Générer RECAP PDF":
    target_file = file_recap if "file_recap" in dir() else None
    if not target_file:
        st.error("Veuillez charger le fichier PDF.")
    else:
        with st.spinner("Analyse et génération du RECAP en cours..."):
            try:
                data, fmt = parse_pdf_auto(target_file)

                recap_rows = []
                hinterland_totals = {}

                if type_recap == "Export":
                    pol_default = "ABIDJAN"
                    pod_groups  = {}

                    for pol, port_data in data.get("ports", {}).items():
                        for bl_ref, bl_info in port_data.get("bls", {}).items():
                            # Poids brut total du BL = somme de ses conteneurs
                            bl_w = sum(c.get("poids_brut", 0.0) for c in bl_info.get("conteneurs", {}).values())
                            if pol not in pod_groups:
                                pod_groups[pol] = {"bls": 0, "20": 0, "40": 0, "poids": 0.0}
                            pod_groups[pol]["bls"] += 1
                            for ct in bl_info.get("conteneurs", {}).values():
                                t = str(ct.get("type", "")).upper()
                                if "20" in t:
                                    pod_groups[pol]["20"] += 1
                                else:
                                    pod_groups[pol]["40"] += 1
                                pod_groups[pol]["poids"] += ct.get("poids_brut", 0.0)

                    for pod, g in pod_groups.items():
                        recap_rows.append({
                            "POL": pol_default, "POD": pod,
                            "BL": g["bls"], "20'": g["20"], "40'": g["40"],
                            "POIDS (kgs)": _fmt_num(g["poids"]),
                            "OBSERVATIONS": "",
                            "_raw_poids": g["poids"]
                        })

                else:  # Import
                    pod = "ABIDJAN"
                    pol_groups = {}

                    for pol, port_data in data.get("ports", {}).items():
                        for bl_ref, bl_info in port_data.get("bls", {}).items():
                            if pol not in pol_groups:
                                pol_groups[pol] = {"bls": 0, "20": 0, "40": 0, "poids": 0.0}
                            pol_groups[pol]["bls"] += 1
                            for ct in bl_info.get("conteneurs", {}).values():
                                t = str(ct.get("type", "")).upper()
                                if "20" in t:
                                    pol_groups[pol]["20"] += 1
                                else:
                                    pol_groups[pol]["40"] += 1
                                pol_groups[pol]["poids"] += ct.get("poids_brut", 0.0)

                    for pol, g in pol_groups.items():
                        recap_rows.append({
                            "POL": pol, "POD": pod,
                            "BL": g["bls"], "20'": g["20"], "40'": g["40"],
                            "POIDS (kgs)": _fmt_num(g["poids"]),
                            "OBSERVATIONS": "",
                            "_raw_poids": g["poids"]
                        })

                if recap_rows:
                    total_bl    = sum(r["BL"]    for r in recap_rows)
                    total_20    = sum(r["20'"]   for r in recap_rows)
                    total_40    = sum(r["40'"]   for r in recap_rows)
                    total_poids = sum(r["_raw_poids"] for r in recap_rows)

                    # Ligne TOTAL
                    if recap_rows:
                        recap_rows[0]["OBSERVATIONS"] = ""
                    for r in recap_rows:
                        del r["_raw_poids"]

                    total_row = {
                        "POL": "TOTAL", "POD": "",
                        "BL": total_bl, "20'": total_20, "40'": total_40,
                        "POIDS (kgs)": _fmt_num(total_poids),
                        "OBSERVATIONS": "*" * 19
                    }

                    # ── Tableau HTML ──────────────────────────────────────────
                    pol_spans = [1] * len(recap_rows)
                    pod_spans = [1] * len(recap_rows)
                    for i in range(len(recap_rows) - 1, 0, -1):
                        if recap_rows[i]["POL"] == recap_rows[i-1]["POL"]:
                            pol_spans[i-1] += pol_spans[i]; pol_spans[i] = 0
                        if recap_rows[i]["POD"] == recap_rows[i-1]["POD"]:
                            pod_spans[i-1] += pod_spans[i]; pod_spans[i] = 0

                    def _th(text, w=""):
                        style = f"padding:10px;border:1px solid #a0a0a0;{w}"
                        return f"<th style='{style}'>{text}</th>"

                    def _td(text, extra="", w=""):
                        style = f"padding:10px;border:1px solid #a0a0a0;vertical-align:middle;{w}{extra}"
                        return f"<td style='{style}'>{text}</td>"

                    html = (
                        "<table style='width:62%;margin:auto;border-collapse:collapse;"
                        "font-size:0.88rem;color:#4b4b4b;background:#fff;"
                        "border-radius:8px;overflow:hidden;box-shadow:0 0 10px rgba(0,0,0,0.1)'>"
                        "<thead><tr style='background:#f7f7f7;border-bottom:2px solid #888'>"
                    )
                    cols_w = {"POL":"width:100px", "POD":"width:100px",
                              "BL":"width:35px", "20'":"width:35px",
                              "40'":"width:35px", "POIDS (kgs)":"width:80px",
                              "OBSERVATIONS":"width:200px"}
                    for col in ["POL","POD","BL","20'","40'","POIDS (kgs)","OBSERVATIONS"]:
                        html += _th(col, cols_w.get(col, ""))
                    html += "</tr></thead><tbody>"

                    for i, row in enumerate(recap_rows):
                        html += "<tr>"
                        if pol_spans[i] > 0:
                            html += f"<td rowspan='{pol_spans[i]}' style='padding:10px;border:1px solid #a0a0a0;vertical-align:middle;font-weight:bold'>{row['POL']}</td>"
                        if pod_spans[i] > 0:
                            html += f"<td rowspan='{pod_spans[i]}' style='padding:10px;border:1px solid #a0a0a0;vertical-align:middle;font-weight:bold'>{row['POD']}</td>"
                        html += _td(row["BL"]) + _td(row["20'"]) + _td(row["40'"]) + _td(row["POIDS (kgs)"])
                        if i == 0:
                            obs_html = str(row["OBSERVATIONS"]).replace("\n", "<br>")
                            html += f"<td rowspan='{len(recap_rows)}' style='padding:10px;border:1px solid #a0a0a0;vertical-align:middle;text-align:center;font-weight:bold'>{obs_html}</td>"
                        html += "</tr>"

                    t20 = total_row["20'"]
                    t40 = total_row["40'"]
                    html += (
                        f"<tr style='font-weight:bold;background:#f7f7f7'>"
                        f"<td colspan='2' style='padding:10px;border:1px solid #a0a0a0;text-align:center'>TOTAL</td>"
                        + _td(total_row["BL"]) + _td(t20) + _td(t40)
                        + _td(total_row["POIDS (kgs)"]) + _td(total_row["OBSERVATIONS"])
                        + "</tr></tbody></table>"
                    )

                    st.subheader(f"RÉCAPITULATIF ({type_recap.upper()})")
                    fmt_badge = "cargo" if fmt == "cargo" else "sydam"
                    label_fmt = "CARGO Manifest" if fmt == "cargo" else "SYDAM"
                    st.markdown(f"<span class='badge-{fmt_badge}'>Format détecté : {label_fmt}</span>", unsafe_allow_html=True)
                    st.markdown(html, unsafe_allow_html=True)

                    # ── Génération PDF ───────────────────────────────────────
                    pdf_table = html.replace("width:62%", "width:100%")
                    pdf_html = f"""
                    <html><head><style>
                        @page {{ size: a4 landscape; margin: 1.5cm; }}
                        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 9px; color: #333; }}
                        table {{ border-collapse: collapse; width: 100%; }}
                        th, td {{ border: 1px solid #a0a0a0; padding: 4px 6px; text-align: center; vertical-align: middle; }}
                        th {{ background-color: #f7f7f7; font-weight: bold; }}
                    </style></head><body>
                        <h2 style="color:#4b4b4b;font-size:16px;margin-bottom:16px">
                            RÉCAPITULATIF DES MARCHANDISES ({type_recap.upper()})
                        </h2>
                        {pdf_table}
                        <div style="text-align:right;margin-top:50px;font-size:11px">
                            <p style="margin-bottom:60px">Fait le : {date_signature.strftime('%d/%m/%Y')}</p>
                            <p><strong>Cachet et Signature</strong></p>
                        </div>
                    </body></html>
                    """
                    buf = io.BytesIO()
                    pisa.CreatePDF(io.StringIO(pdf_html), dest=buf)
                    col_d1, col_d2, col_d3 = st.columns([1.5, 1, 1.5])
                    with col_d2:
                        st.download_button(
                            label="Télécharger RECAP (PDF)",
                            data=buf.getvalue(),
                            file_name="recap_manifeste.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                else:
                    st.warning("Aucune donnée extraite du fichier PDF.")

            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")
                import traceback
                st.code(traceback.format_exc())


# ─────────────────────────────────────────────────────────────────────────────
# Mode : Réconciliation (XML vs PDF  |  PDF vs PDF)
# ─────────────────────────────────────────────────────────────────────────────
elif btn_lancer:
    f1 = file1 if "file1" in dir() else None
    f2 = file2 if "file2" in dir() else None

    if not f1 or not f2:
        st.error("Veuillez charger les deux fichiers avant de lancer la réconciliation.")
    else:
        with st.spinner("Analyse et extraction des données en cours..."):
            try:
                if mode == "XML vs PDF":
                    # ── Fichier 1 : XML ────────────────────────────────────
                    st.info("Extraction XML…")
                    xml_bytes = f1.read()
                    data1 = parse_xml(xml_bytes)
                    st.success("XML extrait avec succès !")

                    # ── Fichier 2 : PDF auto-détecté ───────────────────────
                    st.info("Extraction PDF…")
                    data2, fmt2 = parse_pdf_auto(f2)
                    fmt2_label = "CARGO Manifest" if fmt2 == "cargo" else "SYDAM"
                    st.success(f"PDF extrait avec succès ! (Format détecté : {fmt2_label})")

                    label1, label2 = "Valeur XML", f"Valeur PDF ({fmt2_label})"

                else:  # PDF vs PDF
                    # ── Fichier 1 ─────────────────────────────────────────
                    st.info("Extraction PDF 1…")
                    data1, fmt1 = parse_pdf_auto(f1)
                    fmt1_label = "CARGO Manifest" if fmt1 == "cargo" else "SYDAM"
                    badge1 = "cargo" if fmt1 == "cargo" else "sydam"
                    st.success(f"PDF 1 extrait ! (Format : {fmt1_label})")

                    # ── Fichier 2 ─────────────────────────────────────────
                    st.info("Extraction PDF 2…")
                    data2, fmt2 = parse_pdf_auto(f2)
                    fmt2_label = "CARGO Manifest" if fmt2 == "cargo" else "SYDAM"
                    badge2 = "cargo" if fmt2 == "cargo" else "sydam"
                    st.success(f"PDF 2 extrait ! (Format : {fmt2_label})")

                    label1 = f"PDF 1 ({fmt1_label})"
                    label2 = f"PDF 2 ({fmt2_label})"

                # ── Résumé des fichiers ────────────────────────────────────
                st.subheader("📋 Résumé des fichiers")
                c1, c2 = st.columns(2)

                def _summary_card(col, data, lbl, badge="sydam"):
                    nb_ports = len(data.get("ports", {}))
                    nb_bls   = sum(len(p["bls"]) for p in data.get("ports", {}).values())
                    nb_cts   = sum(
                        len(b["conteneurs"])
                        for p in data.get("ports", {}).values()
                        for b in p["bls"].values()
                    )
                    with col:
                        st.markdown(f"<span class='badge-{badge}'>{lbl}</span>", unsafe_allow_html=True)
                        st.markdown(f"""
                        - **Navire** : {data.get('navire') or 'N/A'}
                        - **Voyage** : {data.get('numero_voyage') or 'N/A'}
                        - **ETA**    : {data.get('eta') or 'N/A'}
                        - **Ports**  : {nb_ports}
                        - **BLs**    : {nb_bls}
                        - **Conteneurs** : {nb_cts}
                        """)

                if mode == "XML vs PDF":
                    _summary_card(c1, data1, label1, "xml")
                    _summary_card(c2, data2, label2, badge2 if "badge2" in dir() else "sydam")
                else:
                    _summary_card(c1, data1, label1, badge1)
                    _summary_card(c2, data2, label2, badge2)

                # ── Réconciliation ─────────────────────────────────────────
                st.info("Comparaison des données…")
                differences = reconcile_manifests(data1, data2, label1, label2)

                st.subheader("📊 Résultats de la comparaison")
                if not differences:
                    st.success("✅ Aucune différence majeure trouvée entre les deux fichiers !")
                else:
                    st.warning(f"⚠️ {len(differences)} différence(s) trouvée(s).")
                    df_diff = pd.DataFrame(differences)
                    cols_order = ["Contexte", "Identifiant", "Champ", label1, label2]
                    df_diff = df_diff[[c for c in cols_order if c in df_diff.columns]]

                    # Coloration des lignes selon le contexte
                    st.dataframe(df_diff, use_container_width=True, height=min(600, 45 * len(df_diff) + 38))

                    csv = df_diff.to_csv(index=False, sep=";").encode("utf-8-sig")
                    st.download_button(
                        label="📥 Télécharger les différences (CSV)",
                        data=csv,
                        file_name="differences_manifeste.csv",
                        mime="text/csv",
                    )

            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")
                import traceback
                st.code(traceback.format_exc())
