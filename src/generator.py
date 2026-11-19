"""ADIM 6 - ÜRET: Bulunan parçaları prompt'a koy, LLM sadece bunlara dayanarak cevaplasın."""
import ollama

from . import config, settings
from .chunker import chunk_label
from .formats import LABEL_TEXT
from .loader import list_note_files

SYSTEM = (
    "Sen kişisel not asistanısın. Soruyu SADECE aşağıdaki bağlama dayanarak Türkçe, kısa cevapla. "
    "Cevap bağlamda yoksa sadece 'Bu bilgi notlarda yok' de, tahmin etme. "
    "Cevabın sonunda kullandığın kaynakları [1], [2] gibi numaralarla belirt."
)


def build_prompt(question: str, results) -> str:
    # Her parçaya numara ve kaynak ver ki model atıf yapabilsin
    ctx = "\n\n".join(f"[{i}] ({chunk_label(c)})\n{c.text}"
                      for i, (c, _) in enumerate(results, 1))
    return f"Bağlam:\n{ctx}\n\nSoru: {question}"


def answer(question: str, results) -> str:
    resp = ollama.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": build_prompt(question, results)}],
        options=config.LLM_OPTIONS, keep_alive=config.LLM_KEEP_ALIVE, think=config.LLM_THINK,
    )
    return resp["message"]["content"].strip()


def meta_system() -> str:
    # Gerçekleri config'ten çek ki ayarlar değişince cevap da doğru kalsın
    n = len(list_note_files(settings.notes_dir()))
    return (
        "Sen 'Kişisel Not Arama asistanı'sın. Kullanıcının kendi notlarından (şu an "
        f"{n} not) soruları cevaplarsın. Notlar {config.EMBED_MODEL} embedding modeliyle "
        f"aranır, cevabı {config.LLM_MODEL} dil modeli yazar. Her şey yerel çalışır, "
        "veri dışarı gitmez. Selamlaşmalara ve sana dair sorulara Türkçe, çok kısa cevap ver. "
        f"Desteklenen not biçimleri: {LABEL_TEXT}. "
        "Kullanıcı yeni notu uygulamadaki 'Not ekle' ile ekleyip 'Yeniden indeksle'ye basar; "
        "sen sohbetten not ekleyemez/silemezsin. İnternet araması ve genel bilgi sorusu cevaplama yok; "
        "bunlar dışında yetenek uydurma, kullanıcıya notlarıyla ilgili soru sormasını öner."
    )


def answer_meta(question: str) -> str:
    resp = ollama.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": meta_system()},
                  {"role": "user", "content": question}],
        options=config.LLM_OPTIONS, keep_alive=config.LLM_KEEP_ALIVE, think=config.LLM_THINK,
    )
    return resp["message"]["content"].strip()
