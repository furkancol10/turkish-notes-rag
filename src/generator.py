"""ADIM 6 - ÜRET: Bulunan parçaları prompt'a koy, LLM sadece bunlara dayanarak cevaplasın."""
import ollama

from . import config, conversation, settings
from .chunker import chunk_label
from .formats import LABEL_TEXT
from .loader import list_note_files

SYSTEM = (
    "Sen kişisel not asistanısın. Soruyu SADECE aşağıdaki bağlama dayanarak Türkçe, kısa cevapla. "
    "Cevap bağlamda yoksa sadece 'Bu bilgi notlarda yok' de, tahmin etme. "
    "Cevabın sonunda kullandığın kaynakları [1], [2] gibi numaralarla belirt. "
    "Önceki konuşma sadece soruyu anlamak içindir; bilgiler yine bağlamdan gelmeli. "
    "Bağlamdaki her parçanın başlığında kaynak dosya adı (ve PDF ise sayfa) yazar: "
    "'hangi dosyada/kaynakta/sayfada' diye sorulursa bu başlıklardaki dosya adını ve sayfayı söyle."
)

FOLLOWUP_SYSTEM = (
    "Sen kişisel not asistanısın. Kullanıcı bir önceki cevabın hakkında soru soruyor "
    "(doğruluk, daha kısa anlatım, bir maddenin açıklaması, kaynak vb.). Yeni arama yapılmadı; "
    "elinde sohbet geçmişi ve önceki cevabın kaynakları var. Önceki cevaptaki iddiaları kaynaklarla "
    "karşılaştır. Cevap kaynaklarla çelişiyorsa veya kaynaklarda desteklenmiyorsa bunu açıkça söyle "
    "ve doğrusunu ver. Sadece kaynaklara dayan, tahmin etme. Türkçe, kısa cevapla ve "
    "dayandığın kaynakları [1], [2] gibi numaralarla belirt."
)


def build_prompt(question: str, results) -> str:
    # Her parçaya numara ve kaynak ver ki model atıf yapabilsin
    ctx = "\n\n".join(f"[{i}] ({chunk_label(c)})\n{c.text}"
                      for i, (c, _) in enumerate(results, 1))
    return f"Bağlam:\n{ctx}\n\nSoru: {question}"


def answer(question: str, results, history: list[dict] | None = None) -> str:
    history = list(history or [])
    if history:
        history, results = conversation.fit_budget(history, results, question, system=SYSTEM)
    resp = ollama.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": SYSTEM}, *history,
                  {"role": "user", "content": build_prompt(question, results)}],
        options=config.LLM_OPTIONS, keep_alive=config.LLM_KEEP_ALIVE, think=config.LLM_THINK,
    )
    return resp["message"]["content"].strip()


def _src_ctx(sources: list[dict]) -> str:
    def label(s):
        parts = [str(s.get("source", ""))]
        if s.get("heading"):
            parts.append(str(s["heading"]))
        if s.get("page"):
            parts.append(f"s.{s['page']}")
        return ", ".join(p for p in parts if p)
    return "\n\n".join(f"[{i}] ({label(s)})\n{s.get('text', '')}" for i, s in enumerate(sources, 1))


def answer_followup(question: str, history: list[dict], sources: list[dict], limit: int = 3000) -> str:
    """Önceki cevap hakkındaki soru: yeni arama yok, önceki cevabın kaynaklarıyla kontrol et."""
    tok = conversation.approx_tokens
    history, sources = list(history or []), list(sources or [])
    base = tok(FOLLOWUP_SYSTEM) + tok(question) + 40

    def total():
        return base + tok(_src_ctx(sources)) + sum(tok(h["content"]) + 4 for h in history)

    while history and total() > limit:
        history.pop(0)
    while len(sources) > 1 and total() > limit:
        sources.pop()
    resp = ollama.chat(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": FOLLOWUP_SYSTEM}, *history,
                  {"role": "user", "content": f"Önceki cevabın kaynakları:\n{_src_ctx(sources)}\n\nSoru: {question}"}],
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
