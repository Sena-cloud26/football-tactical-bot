"""
⚽ Football Tactical Analyst Bot
Chatbot berbasis LLM (Gemini/Groq) untuk analisis taktik sepak bola,
dengan input Excel squad/atribut pemain dan RAG dari dokumen taktik.
"""

import streamlit as st
import pandas as pd

from utils.excel_parser import load_squad_excel, summarize_squad, basic_stats
from utils.rag_engine import TacticalKnowledgeBase
from utils.llm_client import build_system_prompt, get_response

# ---------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Football Tactical Analyst Bot",
    page_icon="⚽",
    layout="wide",
)

# ---------------------------------------------------------------------------
# STATE AWAL
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # memory percakapan
if "squad_df" not in st.session_state:
    st.session_state.squad_df = None
if "kb" not in st.session_state:
    st.session_state.kb = TacticalKnowledgeBase()

# ---------------------------------------------------------------------------
# SIDEBAR — KONFIGURASI PARAMETER KREATIF
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Konfigurasi Bot")

    st.subheader("1. Provider LLM")
    provider = st.selectbox("Pilih penyedia AI", ["Google Gemini", "Groq"])
    api_key = st.text_input(f"API Key — {provider}", type="password")

    if provider == "Groq":
        groq_model = st.selectbox(
            "Model Groq",
            ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3-8b-27b", "allam-2-7b"],
            help="Jika sebuah model menghasilkan error 'model_not_found', cek daftar model aktif akun kamu di https://api.groq.com/openai/v1/models — ketersediaan model berbeda per akun.",
        )
    else:
        groq_model = "openai/gpt-oss-20b"

    st.divider()
    st.subheader("2. Parameter Kreativitas")
    bot_name = st.text_input("Nama Bot", value="TacticalGPT")
    tone = st.selectbox("Gaya Bahasa", ["Formal", "Santai", "Teknis/Detail"])
    temperature = st.slider(
        "Tingkat Kreativitas (temperature)", 0.0, 1.0, 0.7, 0.05,
        help="Nilai rendah = jawaban konsisten & faktual. Nilai tinggi = jawaban lebih variatif/kreatif."
    )
    max_tokens = st.slider("Panjang Maksimal Jawaban (token)", 256, 2048, 1024, 128)

    st.divider()
    st.subheader("3. Domain Lock")
    st.info("🔒 Bot dikunci hanya untuk topik **sepak bola** (taktik, formasi, analisis pemain).")

    st.divider()
    if st.button("🗑️ Reset Memory Percakapan"):
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.title("⚽ Football Tactical Analyst Bot")
st.caption("Chatbot AI untuk analisis taktik, formasi, dan atribut pemain — didukung Gemini/Groq + RAG")

tab_chat, tab_data, tab_docs = st.tabs(["💬 Chat", "📊 Data Squad (Excel)", "📚 Dokumen Referensi (RAG)"])

# ---------------------------------------------------------------------------
# TAB: DATA SQUAD (EXCEL)
# ---------------------------------------------------------------------------
with tab_data:
    st.subheader("Upload Data Squad / Atribut Pemain")
    st.caption("Format: file Excel (.xlsx) berisi kolom seperti Nama, Posisi, Pace, Passing, Tackling, dll.")

    excel_file = st.file_uploader("Pilih file Excel squad", type=["xlsx", "xls"])

    if excel_file is not None:
        try:
            df = load_squad_excel(excel_file)
            st.session_state.squad_df = df
            st.success(f"✅ Berhasil memuat {len(df)} pemain dengan {len(df.columns)} kolom atribut.")

            st.dataframe(df, use_container_width=True, height=350)

            stats = basic_stats(df)
            if stats:
                st.subheader("📈 Statistik Cepat (Otomatis)")
                stat_cols = st.columns(min(len(stats), 4))
                for i, (col_name, s) in enumerate(stats.items()):
                    with stat_cols[i % 4]:
                        st.metric(label=col_name, value=s["rata-rata"], delta=f"max {s['tertinggi']} / min {s['terendah']}")
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
    elif st.session_state.squad_df is not None:
        st.dataframe(st.session_state.squad_df, use_container_width=True, height=350)
    else:
        st.info("Belum ada data squad diunggah. Bot tetap bisa menjawab pertanyaan taktik umum tanpa data ini.")

# ---------------------------------------------------------------------------
# TAB: DOKUMEN REFERENSI (RAG)
# ---------------------------------------------------------------------------
with tab_docs:
    st.subheader("Upload Dokumen Referensi Taktik")
    st.caption("Format: file .txt berisi catatan taktik, filosofi permainan, atau panduan formasi. Bot akan mengambil potongan paling relevan saat menjawab (RAG).")

    doc_file = st.file_uploader("Pilih dokumen (.txt)", type=["txt"])
    if doc_file is not None:
        content = doc_file.read().decode("utf-8", errors="ignore")
        st.session_state.kb.add_document(content, doc_file.name)
        st.success(f"✅ Dokumen '{doc_file.name}' ditambahkan ke knowledge base ({len(content)} karakter).")

    if st.session_state.kb.is_ready():
        st.write(f"📚 Total potongan dokumen tersimpan: **{len(st.session_state.kb.chunks)}**")
        if st.button("🗑️ Hapus semua dokumen referensi"):
            st.session_state.kb.reset()
            st.rerun()
    else:
        st.info("Belum ada dokumen referensi. Bot akan menjawab berdasarkan pengetahuan umum taktik.")

# ---------------------------------------------------------------------------
# TAB: CHAT
# ---------------------------------------------------------------------------
with tab_chat:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Tanyakan analisis taktik, formasi, atau rekomendasi pemain...")

    if user_input:
        if not api_key:
            st.error(f"⚠️ Masukkan API Key untuk {provider} di sidebar terlebih dahulu.")
        else:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Bangun konteks squad (jika ada)
            squad_context = ""
            if st.session_state.squad_df is not None:
                squad_context = summarize_squad(st.session_state.squad_df)

            # Bangun konteks RAG (jika ada dokumen relevan)
            rag_context = ""
            if st.session_state.kb.is_ready():
                results = st.session_state.kb.retrieve(user_input, top_k=3)
                if results:
                    rag_context = "\n\n".join(
                        [f"[Sumber: {r['source']}]\n{r['text']}" for r in results]
                    )

            system_prompt = build_system_prompt(bot_name, tone, squad_context, rag_context)

            with st.chat_message("assistant"):
                with st.spinner("Menganalisis taktik..."):
                    try:
                        answer = get_response(
                            provider=provider,
                            api_key=api_key,
                            system_prompt=system_prompt,
                            chat_history=st.session_state.chat_history[:-1],
                            user_message=user_input,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            groq_model=groq_model,
                        )
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        st.error(f"❌ Terjadi kesalahan saat memanggil API: {e}")

st.markdown("---")
st.caption("Dibuat dengan Streamlit • Google Gemini API / Groq API • RAG berbasis TF-IDF (scikit-learn)")
