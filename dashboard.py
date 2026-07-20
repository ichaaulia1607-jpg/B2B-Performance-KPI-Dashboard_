import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter, MaxNLocator

# ==============================================================================
# 0. CONFIG & SETTINGS DASHBOARD
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Performansi Gangguan B2B - Telkom Akses",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Menghindari warning matplotlib di server cloud/Streamlit Share
import matplotlib
matplotlib.use("Agg")

# Formatter Jam untuk Sumbu Grafik
def jam_formatter(x, pos):
    return f'{x:,.0f} Jam'

# ==============================================================================
# 1. LOAD DATA & ADVANCED FEATURE ENGINEERING
# ==============================================================================
@st.cache_data
def load_and_clean_data():
    # Membaca kedua dataset terpisah
    df_g = pd.read_excel("DATA GANGGUAN.xlsx")
    df_t = pd.read_excel("DATA TEKNISI.xlsx")

    # Konversi kolom waktu ke format Datetime
    time_cols = ['Waktu_Open', 'Waktu_Respon', 'Waktu_Closed']
    for col in time_cols:
        if col in df_g.columns:
            df_g[col] = pd.to_datetime(df_g[col], errors='coerce')

    # Memastikan kolom target TTR berupa angka numerik
    if 'Target_TTR' in df_g.columns:
        df_g['Target_TTR'] = pd.to_numeric(df_g['Target_TTR'], errors='coerce')

    # --- PROSES FEATURE ENGINEERING OPERASIONAL ---
    # 1. Ekstraksi Waktu Tren Bulanan dan Nama Hari
    df_g['tahun'] = df_g['Waktu_Open'].dt.year
    df_g['bulan'] = df_g['Waktu_Open'].dt.to_period('M')
    df_g['bulan_nama'] = df_g['Waktu_Open'].dt.strftime('%B %Y')
    df_g['hari_nama'] = df_g['Waktu_Open'].dt.day_name()

    # 2. Hitung Durasi Nyata Penyelesaian Gangguan (TTR Jam)
    df_g['Durasi_TTR_Jam'] = (df_g['Waktu_Closed'] - df_g['Waktu_Open']) / pd.Timedelta(hours=1)

    # 3. Tentukan Status Pemenuhan KPI TTR (1 = Tercapai, 0 = Overdue)
    df_g['Status_KPI'] = (df_g['Durasi_TTR_Jam'] <= df_g['Target_TTR']).astype(int)

    return df_g, df_t

# Memuat data ke aplikasi
try:
    df_gangguan, df_teknisi = load_and_clean_data()
    data_loaded = True
except Exception as e:
    st.error(f"Gagal memuat file Excel. Pastikan file 'DATA GANGGUAN.xlsx' dan 'DATA TEKNISI.xlsx' sudah diunggah ke repositori. Detail Error: {e}")
    data_loaded = False

if data_loaded:
    # ==============================================================================
    # 2. SIDEBAR FILTER (Mata Rantai Utama Analisis Telkom Akses)
    # ==============================================================================
    st.sidebar.title("🔍 TA Pekanbaru B2B")
    st.sidebar.markdown("Monitoring Indeks Performansi Gangguan & Produktivitas Teknisi Lapangan.")
    st.sidebar.write("---")

    # Filter 1: Wilayah STO
    list_sto = ["Semua STO"] + sorted(list(df_gangguan['STO'].dropna().unique()))
    pilihan_sto = st.sidebar.selectbox("📍 Pilih Wilayah STO:", list_sto)

    # Filter 2: Periode Tahun (Multiselect)
    list_tahun = sorted([int(x) for x in df_gangguan['tahun'].dropna().unique()])
    pilihan_tahun = st.sidebar.multiselect("📅 Periode Tahun:", list_tahun, default=list_tahun)

    # Filter 3: Rentang Bulan Analisis (Slider)
    rentang_bulan = st.sidebar.slider("📅 Rentang Bulan Analisis (1-12):", 1, 12, (1, 12))

    # --- Proses Sinkronisasi Filter ke Dataframe Master ---
    df_filtered = df_gangguan[df_gangguan['tahun'].isin(pilihan_tahun)]
    df_filtered = df_filtered[(df_filtered['Waktu_Open'].dt.month >= rentang_bulan[0]) & (df_filtered['Waktu_Open'].dt.month <= rentang_bulan[1])]

    if pilihan_sto != "Semua STO":
        df_filtered = df_filtered[df_filtered['STO'] == pilihan_sto]

    # ==============================================================================
    # 3. TOP OPERATIONAL METRICS (KPI Cards Utama)
    # ==============================================================================
    st.title("⚡ Dashboard Performa Gangguan B2B Pekanbaru")
    st.markdown("Analisis komprehensif penanganan keluhan pelanggan corporate, pencapaian KPI TTR, dan beban kerja tim lapangan.")

    # Kalkulasi Metrik Utama Berdasarkan Filter
    total_tiket = len(df_filtered)
    rata_ttr = df_filtered['Durasi_TTR_Jam'].mean() if total_tiket > 0 else 0
    rasio_kpi = (df_filtered['Status_KPI'].mean() * 100) if total_tiket > 0 else 0

    # Standar KPI Korporat Umumnya 80%
    target_kpi_global = 80.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📥 Total Tiket Gangguan", f"{total_tiket} Kasus")
    col2.metric("⏱️ Rata-rata Durasi TTR", f"{rata_ttr:.2f} Jam")
    col3.metric("📈 Rasio Pencapaian KPI", f"{rasio_kpi:.2f}%")
    col4.metric("🎯 Standar Minimal Target", f"{target_kpi_global:.1f}%")

    st.write("---")

    # ==============================================================================
    # 4. TABS NAVIGATION (Memecah Setiap Pertanyaan Menjadi Halaman Eksklusif)
    # ==============================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Q1: Diagram Pareto Gejala",
        "📈 Q2: Tren Pencapaian KPI",
        "📍 Q3: Prioritas Wilayah STO",
        "👥 Q4: Beban Kerja Teknisi"
    ])

    # ------------------------------------------------------------------------------
    # TAB 1: PERTANYAAN 1 (Analisis Gejala Gangguan Terbanyak - Diagram Pareto)
    # ------------------------------------------------------------------------------
    with tab1:
        st.subheader("📌 Analisis Gejala Gangguan B2B Terbanyak (Diagram Pareto)")

        df_q1 = df_filtered.copy()

        if not df_q1.empty and 'Gejala_Symptom' in df_q1.columns:
            # Hitung jumlah total gangguan per Gejala_Symptom
            symptom_counts = df_q1['Gejala_Symptom'].value_counts().reset_index()
            symptom_counts.columns = ['Gejala_Symptom', 'Jumlah_Gangguan']

            # Hitung Persentase Kumulatif
            symptom_counts['Persentase'] = (symptom_counts['Jumlah_Gangguan'] / symptom_counts['Jumlah_Gangguan'].sum()) * 100
            symptom_counts['Kumulatif'] = symptom_counts['Persentase'].cumsum()

            col_g1, col_t1 = st.columns([2, 1])

            with col_g1:
                fig1, ax1 = plt.subplots(figsize=(10, 6))

                # Barplot Sumbu Utama (Kiri)
                sns.barplot(
                    x='Gejala_Symptom', y='Jumlah_Gangguan', data=symptom_counts,
                    color='#72BCD4', ax=ax1, hue='Gejala_Symptom', legend=False
                )
                ax1.set_title('Diagram Pareto Gejala Gangguan B2B', fontsize=14, fontweight='bold')
                ax1.set_xlabel('Gejala Gangguan')
                ax1.set_ylabel('Jumlah Gangguan (Tiket)')
                ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')

                # Lineplot Sumbu Kedua (Kanan) untuk Kumulatif
                ax2 = ax1.twinx()
                ax2.plot(symptom_counts['Gejala_Symptom'], symptom_counts['Kumulatif'], color='#D9534F', marker='D', ms=5, linewidth=2)
                ax2.set_ylabel('Persentase Kumulatif (%)')
                ax2.set_ylim(0, 110)
                ax2.axhline(80, color='red', linestyle='--', alpha=0.7, label='Batas Kritis 80%')

                st.pyplot(fig1)

            with col_t1:
                st.info("💡 **AI Insight Q1 (Pareto):**")
                gejala_utama = symptom_counts.iloc[0]['Gejala_Symptom']
                jumlah_utama = symptom_counts.iloc[0]['Jumlah_Gangguan']
                st.write(f"Kategori keluhan **{gejala_utama}** mendominasi dengan total **{jumlah_utama} kasus**. Fokus perbaikan infrastruktur pada sektor ini sangat direkomendasikan guna meredam keluhan hingga 80%.")
                st.dataframe(symptom_counts[['Gejala_Symptom', 'Jumlah_Gangguan', 'Kumulatif']].style.format({'Kumulatif': '{:.2f}%'}))
        else:
            st.warning("Data atau kolom 'Gejala_Symptom' tidak ditemukan.")

    # ------------------------------------------------------------------------------
    # TAB 2: PERTANYAAN 2 (Tren Rata-rata Pencapaian KPI TTR per Bulan)
    # ------------------------------------------------------------------------------
    with tab2:
        st.subheader("📌 Analisis Tren Efisiensi & Rata-rata Pencapaian KPI Bulanan")

        df_q2 = df_filtered.copy()

        if not df_q2.empty and not df_q2['bulan'].isna().all():
            # Hitung persentase pencapaian KPI rata-rata per periode bulan
            trend_kpi = df_q2.groupby('bulan')['Status_KPI'].mean().reset_index()
            trend_kpi['Persentase_Ach'] = trend_kpi['Status_KPI'] * 100
            trend_kpi = trend_kpi.sort_values('bulan')
            trend_kpi['bulan_str'] = trend_kpi['bulan'].astype(str)

            col_g2, col_t2 = st.columns([2, 1])

            with col_g2:
                fig2, ax2 = plt.subplots(figsize=(10, 5))
                sns.lineplot(x='bulan_str', y='Persentase_Ach', data=trend_kpi, marker='o', markersize=8, linewidth=3, color='#72BCD4', ax=ax2)

                # Garis ambang batas minimum KPI
                ax2.axhline(target_kpi_global, color='red', linestyle='--', label=f'Target Minimal KPI: {target_kpi_global}%')

                ax2.set_title('Tren Persentase Pemenuhan KPI TTR B2B per Bulan', fontsize=14, fontweight='bold')
                ax2.set_xlabel('Periode Bulan')
                ax2.set_ylabel('Pencapaian KPI (%)')
                ax2.set_ylim(0, 110)
                ax2.legend(loc='lower right')
                ax2.grid(axis='both', linestyle='--', alpha=0.5)
                ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{y:.0f}%'))
                st.pyplot(fig2)

            with col_t2:
                st.success("💡 **AI Insight Q2:**")
                bulan_terakhir = trend_kpi.iloc[-1]['bulan_str']
                ach_terakhir = trend_kpi.iloc[-1]['Persentase_Ach']

                if ach_terakhir >= target_kpi_global:
                    st.write(f"Selamat! Tim operasional **berhasil memenuhi target** minimum KPI B2B pada bulan terakhir ({bulan_terakhir}) dengan capaian sebesar **{ach_terakhir:.2f}%**.")
                else:
                    st.write(f"Perhatian! Performansi pemenuhan keluhan bulan ({bulan_terakhir}) hanya menyentuh **{ach_terakhir:.2f}%** (Berada di bawah target minimum {target_kpi_global}%). Evaluasi logistik teknisi perlu dilakukan.")
                st.dataframe(trend_kpi[['bulan_str', 'Persentase_Ach']].style.format({'Persentase_Ach': '{:.2f}%'}))
        else:
            st.warning("Data waktu tidak mencukupi untuk memetakan tren bulanan.")

    # ------------------------------------------------------------------------------
# TAB 3: PERTANYAAN 3 (Matriks Kuadran Prioritas Wilayah STO)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📍 Matriks Kuadran Prioritas Wilayah STO")
    
    if not df_filtered.empty and 'STO' in df_filtered.columns:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 1. Feature Engineering: Hitung durasi TTR nyata dalam satuan Jam
        df_filtered['Waktu_Open'] = pd.to_datetime(df_filtered['Waktu_Open'])
        df_filtered['Waktu_Closed'] = pd.to_datetime(df_filtered['Waktu_Closed'])
        df_filtered['Durasi_TTR_Jam'] = (df_filtered['Waktu_Closed'] - df_filtered['Waktu_Open']) / pd.Timedelta(hours=1)
        
        # Aggregate data per STO
        sto_analysis = df_filtered.groupby('STO').agg(
            Jumlah_Gangguan=('No_Tiket', 'count'),
            Rata_TTR=('Durasi_TTR_Jam', 'mean')
        ).reset_index()
        
        # Menentukan garis tengah kuadran berdasarkan rata-rata
        mid_x = sto_analysis['Jumlah_Gangguan'].mean()
        mid_y = sto_analysis['Rata_TTR'].mean()
        
        col_g3, col_t3 = st.columns([2, 1])
        
        with col_g3:
            # 2. Setup Tema Visual Premium
            sns.set_theme(style="whitegrid")
            fig3, ax3 = plt.subplots(figsize=(10, 6.5))
            
            # Mapping warna otomatis berdasarkan posisi kuadran
            colors = []
            for idx, row in sto_analysis.iterrows():
                if row['Jumlah_Gangguan'] >= mid_x and row['Rata_TTR'] >= mid_y:
                    colors.append('#E63946') # Red (Kuadran I - Kritis)
                elif row['Jumlah_Gangguan'] < mid_x and row['Rata_TTR'] >= mid_y:
                    colors.append('#F4A261') # Orange (Kuadran II - Slow but Low)
                elif row['Jumlah_Gangguan'] >= mid_x and row['Rata_TTR'] < mid_y:
                    colors.append('#457B9D') # Blue (Kuadran IV - Fast & High)
                else:
                    colors.append('#2A9D8F') # Green (Kuadran III - Aman)
                    
            # 3. Plotting Titik Data STO
            ax3.scatter(
                sto_analysis['Jumlah_Gangguan'], sto_analysis['Rata_TTR'], 
                s=350, c=colors, edgecolor='white', linewidth=2, alpha=0.9, zorder=3
            )
            
            # Mengatur batas dinamis agar teks info kuadran tidak terpotong
            xlim = (sto_analysis['Jumlah_Gangguan'].min() - 1, sto_analysis['Jumlah_Gangguan'].max() + 1)
            ylim = (sto_analysis['Rata_TTR'].min() - 1, sto_analysis['Rata_TTR'].max() + 1)
            ax3.set_xlim(xlim)
            ax3.set_ylim(ylim)
            
            # Membuat garis putus-putus pembagi kuadran
            ax3.axvline(mid_x, color='#A8DADC', linestyle='--', linewidth=1.5, zorder=1)
            ax3.axhline(mid_y, color='#A8DADC', linestyle='--', linewidth=1.5, zorder=1)
            
            # 4. Labeling Setiap Titik STO dengan Box Putih yang Rapi
            for i in range(sto_analysis.shape[0]):
                ax3.annotate(
                    sto_analysis.STO[i],
                    (sto_analysis.Jumlah_Gangguan[i], sto_analysis.Rata_TTR[i]),
                    textcoords="offset points", xytext=(0, 15), ha='center', fontsize=11, weight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", edgecolor='#E1E1E1', alpha=0.8, lw=1)
                )
                
            # 5. Dekorasi Banner Info Text di Setiap Sudut Kuadran
            ax3.text(xlim[1] - 0.2, ylim[1] - 0.4, "KUADRAN I: PRIORITAS UTAMA\n(Gangguan Banyak & Lambat)", color='#D62828', fontsize=9, weight='bold', ha='right', bbox=dict(boxstyle="square,pad=0.4", fc="#FFEAEA", ec="none", alpha=0.7))
            ax3.text(xlim[0] + 0.2, ylim[1] - 0.4, "KUADRAN II: SLOW BUT LOW\n(Gangguan Sedikit tapi Lambat)", color='#E65F2B', fontsize=9, weight='bold', ha='left', bbox=dict(boxstyle="square,pad=0.4", fc="#FFF2EA", ec="none", alpha=0.7))
            ax3.text(xlim[1] - 0.2, ylim[0] + 0.3, "KUADRAN IV: FAST & HIGH\n(Gangguan Banyak tapi Cepat)", color='#1D3557', fontsize=9, weight='bold', ha='right', bbox=dict(boxstyle="square,pad=0.4", fc="#EAF2FF", ec="none", alpha=0.7))
            ax3.text(xlim[0] + 0.2, ylim[0] + 0.3, "KUADRAN III: AMAN\n(Gangguan Sedikit & Cepat)", color='#2A9D8F', fontsize=9, weight='bold', ha='left', bbox=dict(boxstyle="square,pad=0.4", fc="#E9F7F5", ec="none", alpha=0.7))
            
            # Polishing Judul & Label Sumbu
            ax3.set_title('MATRIKS PRIORITAS PERFORMANSI WILAYAH STO\nTelkom Akses Pekanbaru', fontsize=13, pad=20, weight='bold', color='#1D3557')
            ax3.set_xlabel('Volume Gangguan (Jumlah Tiket Masuk)', fontsize=11, labelpad=10, weight='semibold')
            ax3.set_ylabel('Rata-rata Waktu Perbaikan / TTR (Jam)', fontsize=11, labelpad=10, weight='semibold')
            ax3.grid(True, linestyle=':', alpha=0.5, color='#CCCCCC')
            sns.despine(left=True, bottom=True)
            
            st.pyplot(fig3)
            
        with col_t3:
            st.warning("⚠️ **Analisis Strategis & Urgensi STO:**")
            
            # Menemukan STO yang masuk Kuadran Kritis (I)
            sto_kritis = sto_analysis[(sto_analysis['Jumlah_Gangguan'] >= mid_x) & (sto_analysis['Rata_TTR'] >= mid_y)]['STO'].tolist()
            
            if sto_kritis:
                kritis_str = ", ".join(sto_kritis)
                st.write(f"Wilayah STO **{kritis_str}** teridentifikasi masuk ke **KUADRAN I (Prioritas Utama)** karena memiliki jumlah gangguan di atas rata-rata sekaligus durasi perbaikan yang lambat.")
                st.markdown("💡 **Rekomendasi Operasional:**")
                st.write("- Lakukan audit logistik/material di wilayah tersebut.")
                st.write("- Tambah alokasi teknisi standby khusus penanganan B2B.")
            else:
                st.write("Kabar baik! Tidak ada wilayah STO yang masuk ke dalam Kuadran I (Kritis) untuk kombinasi filter saat ini.")
                
            st.write("---")
            st.markdown("**Data Resume Per Wilayah STO:**")
            st.dataframe(
                sto_analysis.sort_values('Jumlah_Gangguan', ascending=False)
                .style.format({'Rata_TTR': '{:.2f} Jam'})
            )
    else:
        st.warning("Data atau kolom 'STO' tidak ditemukan.")
    # ------------------------------------------------------------------------------
    # TAB 4: ADVANCED AI INSIGHTS & PRODUKTIVITAS TEKNISI (Pertanyaan 4 + Integrasi Data)
    # ------------------------------------------------------------------------------
    with tab4:
        st.subheader("🧠 FinTrack AI Smart Predictive Operations")
        st.markdown("Bagian analitis tingkat lanjut untuk mengukur beban kerja serta tingkat efisiensi durasi kerja para teknisi di lapangan secara komprehensif.")

        df_q4 = df_filtered.copy()

        # Cek ketersediaan nama kolom teknisi di berkas
        kolom_teknisi = 'Nama_Teknisi' if 'Nama_Teknisi' in df_q4.columns else ('Nama Teknisi' if 'Nama Teknisi' in df_q4.columns else None)

        if not df_q4.empty and kolom_teknisi:
            # Menggabungkan total tiket dan rata-rata TTR dari performansi riil teknisi (Feature Engineering Lanjutan)
            summary_teknisi = df_q4.groupby(kolom_teknisi).agg(
                Total_Tiket=(kolom_teknisi, 'count'),
                Rata_Rata_TTR=('Durasi_TTR_Jam', 'mean'),
                Rasio_Sukses_KPI=('Status_KPI', 'mean')
            ).reset_index()

            summary_teknisi['Rasio_Sukses_KPI'] = (summary_teknisi['Rasio_Sukses_KPI'] * 100).round(2)
            summary_teknisi = summary_teknisi.sort_values('Total_Tiket', ascending=False)

            st.write("### 👥 Distribusi Beban Kerja & Skor Performansi Pemenuhan KPI Teknisi")

            col_g4, col_t4 = st.columns([2, 1])

            with col_g4:
                fig4, ax4 = plt.subplots(figsize=(10, 6))
                colors_q4 = sns.color_palette("Blues_r", len(summary_teknisi))

                sns.barplot(
                    x='Total_Tiket', y=kolom_teknisi, data=summary_teknisi,
                    palette=colors_q4, ax=ax4, hue=kolom_teknisi, legend=False
                )

                rata_beban_kerja = summary_teknisi['Total_Tiket'].mean()
                ax4.axvline(rata_beban_kerja, color='red', linestyle='--', label=f'Rata-rata Beban Kerja: {rata_beban_kerja:.1f} Tiket')

                ax4.set_title('Perbandingan Total Penanganan Kasus antar Teknisi', fontsize=14, fontweight='bold')
                ax4.set_xlabel('Jumlah Tiket yang Diselesaikan')
                ax4.set_ylabel('Nama Teknisi')
                ax4.legend(loc='lower right')
                ax4.grid(axis='x', linestyle='--', alpha=0.5)
                ax4.xaxis.set_major_locator(MaxNLocator(integer=True))
                st.pyplot(fig4)

            with col_t4:
                st.info("📊 **Evaluasi Produktivitas Lapangan:**")
                teknisi_sibuk = summary_teknisi.iloc[0][kolom_teknisi]
                tiket_sibuk = summary_teknisi.iloc[0]['Total_Tiket']
                st.write(f"Teknisi dengan beban kerja terpadat saat ini adalah **{teknisi_sibuk}** dengan total penyelesaian **{tiket_sibuk} tiket**. Jaga ritme kerja tim agar indeks kelelahan kerja lapangan tetap seimbang.")

                # Tampilkan tabel analitik performa teknisi yang komprehensif
                st.dataframe(
                    summary_teknisi.style.format({
                        'Rata_Rata_TTR': '{:.2f} Jam',
                        'Rasio_Sukses_KPI': '{:.2f}%'
                    })
                )
        else:
            st.warning("Data atau kolom identitas 'Nama_Teknisi' tidak ditemukan. Harap periksa kembali berkas data kamu.")
