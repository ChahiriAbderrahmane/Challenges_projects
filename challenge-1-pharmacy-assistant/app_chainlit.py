import logging
import threading

import chainlit as cl
import ollama
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Évite les générations simultanées sur les modèles partagés.
generation_lock = threading.Lock()
ollama_client = ollama.Client(timeout=180.0)

# English -> Darija
english_darija_tokenizer = AutoTokenizer.from_pretrained(
    "atlasia/Terjman-Ultra"
)
english_darija_model = AutoModelForSeq2SeqLM.from_pretrained(
    "atlasia/Terjman-Ultra"
).eval()

# Darija -> Arabic
darija_arabic_tokenizer = AutoTokenizer.from_pretrained(
    "Saidtaoussi/AraT5_Darija_to_MSA"
)
darija_arabic_model = AutoModelForSeq2SeqLM.from_pretrained(
    "Saidtaoussi/AraT5_Darija_to_MSA"
).eval()

# Arabic -> English
arabic_english_tokenizer = AutoTokenizer.from_pretrained(
    "Helsinki-NLP/opus-mt-ar-en"
)
arabic_english_model = AutoModelForSeq2SeqLM.from_pretrained(
    "Helsinki-NLP/opus-mt-ar-en"
).eval()


@torch.inference_mode()
def translate(text, tokenizer, model):
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    outputs = model.generate(
        **inputs,
        max_new_tokens=160,
        do_sample=False,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


def translate_darija_to_english(text):
    arabic_text = translate(
        text,
        darija_arabic_tokenizer,
        darija_arabic_model,
    )
    return translate(
        arabic_text,
        arabic_english_tokenizer,
        arabic_english_model,
    )


def translate_english_to_darija(text):
    return translate(
        text,
        english_darija_tokenizer,
        english_darija_model,
    )


def process_message(text, history):
    # Cette fonction sera exécutée dans un thread,
    # pour laisser Chainlit maintenir sa connexion au navigateur.
    with generation_lock:
        logger.info("Traduction de la question vers l'anglais...")
        english_query = translate_darija_to_english(text)

        # Conserve les derniers échanges, tous en anglais.
        messages = [
            {
                "role": "system",
                "content": (
    "You are a patient-to-pharmacy request assistant in Morocco. "
    "Answer in English, in 50 words or fewer; your answer will "
    "then be translated into Moroccan Darija. "
    "Help users formulate medication requests, availability questions, "
    "and requests for pharmacy phone numbers or locations. "
    "When greeted, briefly introduce your pharmacy assistance role. "
    "Ask a short clarification question when necessary. "
    "You have no access to live stock or a pharmacy directory: "
    "never invent availability, prices, phone numbers, or addresses. "
    "Do not diagnose, prescribe, recommend medicines or dosages. "
    "For medical advice, direct the user to a pharmacist. "
    "Politely redirect unrelated questions to pharmacy assistance."
),
            },
            *history[-12:],
            {"role": "user", "content": english_query},
        ]

        logger.info("Génération de la réponse avec Ollama...")
        result = ollama_client.chat(
            model="llama3.2",
            messages=messages,
            stream=False,
            options={"num_predict": 120},
        )

        english_answer = result["message"]["content"].strip()
        if not english_answer:
            raise RuntimeError("Ollama a retourné une réponse vide.")

        logger.info("Traduction de la réponse vers la darija...")
        darija_answer = translate_english_to_darija(english_answer)

        if not darija_answer.strip():
            raise RuntimeError("La traduction est vide.")

        updated_history = [
            *history[-12:],
            {"role": "user", "content": english_query},
            {"role": "assistant", "content": english_answer},
        ]

        return darija_answer, updated_history


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])


@cl.on_message
async def generate_response(query: cl.Message):
    text = query.content.strip()

    if not text:
        await cl.Message(content="Écris un message pour commencer.").send()
        return

    if len(text) > 2000:
        await cl.Message(
            content="Merci de limiter ton message à 2 000 caractères."
        ).send()
        return

    status = cl.Message(content="Traitement en cours…")
    await status.send()

    try:
        history = cl.user_session.get("chat_history") or []

        answer, updated_history = await cl.make_async(process_message)(
            text, history
        )

        cl.user_session.set("chat_history", updated_history)
        status.content = answer

    except Exception:
        logger.exception("Échec du traitement du message")
        status.content = (
            "Le traitement a échoué. Consulte le terminal "
            "pour voir le détail de l’erreur."
        )

    await status.update()
    logger.info("Mise à jour de la réponse terminée.")