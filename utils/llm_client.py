"""
LLM Client — wrapper untuk Google Gemini API dan Groq API.
Mendukung parameter kreatif: temperature, gaya bahasa, domain lock, dan system prompt dinamis.
"""

import os


SYSTEM_PROMPT_TEMPLATE = """Kamu adalah {bot_name}, asisten analis taktik sepak bola profesional.

ATURAN DOMAIN (WAJIB DIPATUHI):
- Kamu HANYA menjawab pertanyaan yang berkaitan dengan sepak bola: taktik, formasi, atribut pemain, analisis squad, strategi pertandingan, dan topik terkait.
- Jika pengguna bertanya di luar topik sepak bola, tolak dengan sopan dan arahkan kembali ke topik sepak bola.

GAYA BAHASA:
- Gunakan gaya bahasa {tone}.
- Jawaban harus terstruktur, jelas, dan mudah dipahami oleh pelatih maupun analis.

KONTEKS DATA:
{squad_context}

REFERENSI TAKTIK (dari dokumen yang diunggah, gunakan jika relevan):
{rag_context}

Jika data pemain atau dokumen referensi tersedia di atas, gunakan sebagai dasar analisis.
Jika tidak tersedia, jawab berdasarkan pengetahuan umum taktik sepak bola dan sebutkan bahwa itu adalah rekomendasi umum.
"""

TONE_MAP = {
    "Formal": "formal dan profesional, seperti laporan analis klub",
    "Santai": "santai namun tetap informatif, seperti obrolan dengan sesama pelatih",
    "Teknis/Detail": "sangat teknis dan mendetail, menyertakan istilah taktik spesifik",
}


def build_system_prompt(bot_name, tone_key, squad_context, rag_context):
    tone = TONE_MAP.get(tone_key, TONE_MAP["Formal"])
    return SYSTEM_PROMPT_TEMPLATE.format(
        bot_name=bot_name,
        tone=tone,
        squad_context=squad_context or "(Belum ada data squad diunggah)",
        rag_context=rag_context or "(Tidak ada referensi dokumen relevan)",
    )


def call_grog(api_key, system_prompt, chat_history, user_message, temperature=0.7, max_tokens=1024, model_name="openai/gpt-oss-20b"):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        },
    )

    # convert history ke format Gemini
    gemini_history = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(user_message)
    return response.text


def call_groq(api_key, system_prompt, chat_history, user_message, temperature=0.7, max_tokens=1024, model_name="openai/gpt-oss-20b"):
    from groq import Groq

    client = Groq(api_key=api_key)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


def get_response(provider, api_key, system_prompt, chat_history, user_message, temperature=0.7, max_tokens=1024, groq_model="openai/gpt-oss-20b"):
    """Dispatcher — pilih provider berdasarkan konfigurasi user."""
    if provider == "Google Gemini":
        return call_gemini(api_key, system_prompt, chat_history, user_message, temperature, max_tokens)
    elif provider == "Groq":
        return call_groq(api_key, system_prompt, chat_history, user_message, temperature, max_tokens, groq_model)
    else:
        raise ValueError(f"Provider tidak dikenal: {provider}")
