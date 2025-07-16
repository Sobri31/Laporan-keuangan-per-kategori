
import streamlit as st
import pdfplumber
import re
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Laporan Dana Otomatis", layout="wide")
st.title("📄 Aplikasi Otomatisasi Laporan Dana")

uploaded_file = st.file_uploader("Unggah file PDF laporan", type=["pdf"])

default_keywords = ["baut", "trass", "dinabol", "alat listrik", "klip wpc", "downled"]

user_keywords = st.text_area(
    "🛠️ Tambahkan kata kunci untuk kategori 'Baut, Trass, Dinabol' (pisahkan dengan koma)",
    value=", ".join(default_keywords),
    height=80
)

keywords = [k.strip().lower() for k in user_keywords.split(",") if k.strip()]

def parse_rupiah(text):
    try:
        return int(text.replace("Rp", "").replace(".", "").replace(",", "").strip())
    except:
        return 0
       
with pdfplumber.open(uploaded_file) as pdf:
        st.subheader("📄 Isi Mentah PDF:")
        for i, page in enumerate(pdf.pages):
            st.text(f"--- Halaman {i+1} ---")
            st.text(page.extract_text())

def extract_transactions(pdf_file):
    results = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().split("\n")
            i = 0
            while i < len(lines) - 2:
                line1 = lines[i].strip()
                line2 = lines[i+1].strip()
                line3 = lines[i+2].strip()
                if re.match(r"\d{1,2} \w+", line1) and "2025" in line3:
                    tanggal = f"{line1} 2025"
                    deskripsi = line2
                    if any(k in deskripsi.lower() for k in ["tes", "titipan", "salah input"]):
                        i += 1
                        continue
                    jenis = "Keluar" if "keluar" in deskripsi.lower() else "Masuk" if "masuk" in deskripsi.lower() else ""
                    masuk = keluar = ""
                    match = re.search(r"Rp[\d\.]+", deskripsi)
                    if match:
                        if jenis == "Keluar":
                            keluar = match.group(0)
                        elif jenis == "Masuk":
                            masuk = match.group(0)
                    if jenis:
                        results.append((tanggal, deskripsi, jenis, masuk, keluar))
                    i += 3
                else:
                    i += 1
    return results

def create_pdf(data_by_category):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "Laporan Kategori Pengeluaran", ln=True, align='C')
    pdf.ln(10)

    for category, rows in data_by_category.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, category, ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 8, "Tanggal", 1)
        pdf.cell(90, 8, "Deskripsi", 1)
        pdf.cell(30, 8, "Masuk", 1)
        pdf.cell(30, 8, "Keluar", 1)
        pdf.ln()
        total = 0
        pdf.set_font("Arial", '', 10)
        for row in rows:
            pdf.cell(40, 8, row[0], 1)
            pdf.cell(90, 8, row[1][:40], 1)
            pdf.cell(30, 8, row[3] if row[3] else "-", 1)
            pdf.cell(30, 8, row[4] if row[4] else "-", 1)
            pdf.ln()
            if row[4]:
                total += parse_rupiah(row[4])
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(160, 8, "TOTAL", 1)
        pdf.cell(30, 8, f"Rp{total:,.0f}".replace(",", "."), 1)
        pdf.ln(10)

    out_pdf = BytesIO()
    out_pdf.write(pdf.output(dest="S").encode("latin1"))
    out_pdf.seek(0)
    return out_pdf

if uploaded_file:
    try:
        data = extract_transactions(uploaded_file)
        keluar = [d for d in data if d[2].lower() == "keluar"]

        kategori_v = [d for d in keluar if "v" in d[1].lower()]
        kategori_transfer = [d for d in keluar if any(k in d[1].lower() for k in ["transfer", "setor", "setoran bagus"])]
        kategori_baut = [d for d in keluar if any(k in d[1].lower() for k in keywords)]
        kategori_bon = [d for d in keluar if "bon" in d[1].lower()]
        kategori_lain = [d for d in keluar if d not in kategori_v and d not in kategori_transfer and d not in kategori_baut and d not in kategori_bon]

        data_by_category = {
            "Kategori: V": kategori_v,
            "Kategori: Transfer & Setor Mandiri": kategori_transfer,
            "Kategori: Baut, Trass, Dinabol, dll": kategori_baut,
            "Kategori: Bon": kategori_bon,
            "Kategori: Pengeluaran Lainnya": kategori_lain
        }

        st.success("✅ Transaksi berhasil diproses!")

        for name, rows in data_by_category.items():
            st.subheader(name)
            if rows:
                st.table(rows)
            else:
                st.markdown("_Tidak ada data_")

        pdf_file = create_pdf(data_by_category)
        st.download_button("📥 Unduh Hasil sebagai PDF", data=pdf_file, file_name="Laporan_Hasil.pdf")

    except Exception as e:
        st.error(f"❌ Gagal memproses PDF: {e}")
