"""ADIM 6 - ÜRET: Bulunan parçaları prompt'a koy, LLM sadece bunlara dayanarak cevaplasın."""

from . import config, conversation, llm, settings
from .chunker import chunk_label
from .formats import LABEL_TEXT
from .loader import list_note_files

SYSTEM = (
    "Sen kişisel not asistanısın. Soruyu SADECE aşağıdaki bağlama dayanarak Türkçe, kısa cevapla. "
    "Cevap bağlamda yoksa sadece 'Bu bilgi notlarda yok' de, tahmin etme. "
    "Bağlam '### Belge: dosya' başlıklı gruplara ayrılmıştır; parçaların [n] numaraları genel numaradır. "
    "Her bilgi yalnızca göründüğü belgeden alınmalı ve o belgenin [n] numarasıyla atıflanmalı. "
    "Soru karşılaştırma istemedikçe farklı belgelerdeki maddeleri tek listede birleştirme. "
    "Soru belirli bir belgeyi/kişiyi/projeyi/aracı anıyorsa SADECE o belgenin bölümlerini kullan; "
    "orada yoksa 'Bu bilgi notlarda yok' de (başka belgede olsa bile onu cevap diye verme; "
    "istersen 'başka belgede X var [n]' diye ekle). "
    "Liste isteniyorsa (ör. 'hangi projeleri önermiş') o belgenin bağlamındaki tüm maddeleri say. "
    "Sadece bağlam sorulan konu/varlıkla AYNI şey hakkındaysa cevapla; ilişkili ama farklı bir şey "
    "hakkındaysa onu cevap olarak verme. "
    "Atıfı cümlenin/maddenin sonuna koy, ör. '... önerdi [3].'; cevabın sonuna [1][2]...[10] yığını ekleme. "
    "Önceki konuşma sadece soruyu anlamak içindir; bilgiler yine bağlamdan gelmeli. "
    "'hangi dosyada/sayfada' diye sorulursa belge başlığındaki dosya adını ve parça başlığındaki sayfayı söyle."
)

FOLLOWUP_SYSTEM = (
    "Sen kişisel not asistanısın. Kullanıcı bir önceki cevabın hakkında soru soruyor "
    "(doğruluk, daha kısa anlatım, bir maddenin açıklaması, kaynak vb.). Yeni arama yapılmadı; "
    "elinde sohbet geçmişi ve önceki cevabın kaynakları var. Önceki cevaptaki iddiaları kaynaklarla "
    "karşılaştır. Cevap kaynaklarla çelişiyorsa veya kaynaklarda desteklenmiyorsa bunu açıkça söyle "
    "ve doğrusunu ver. Sadece kaynaklara dayan, tahmin etme. Türkçe, kısa cevapla ve "
    "dayandığın kaynakları [1], [2] gibi numaralarla belirt."
)


def _loc(c) -> str:
    parts = [f"s. {c.page}"] if c.page else []
    if c.heading:
        parts.append(c.heading)
    return " / ".join(parts)


def _group_ctx(results) -> str:
    """Parçaları belgeye göre grupla (belgeler en iyi skora göre); [n] genel numarası korunur."""
    groups: dict[str, list] = {}
    best: dict[str, float] = {}
    for i, (c, sc) in enumerate(results, 1):
        groups.setdefault(c.source, []).append((i, c))
        best[c.source] = max(best.get(c.source, float("-inf")), sc)
    order = sorted(groups, key=lambda d: -best[d])  # sorted kararlı: eşitlikte ilk görülen önce
    blocks = []
    for d in order:
        items = "\n\n".join(f"[{i}] ({_loc(c)})\n{c.text}" if _loc(c) else f"[{i}]\n{c.text}"
                             for i, c in groups[d])
        blocks.append(f"### Belge: {d}\n{items}")
    return "\n\n".join(blocks)


def build_prompt(question: str, results) -> str:
    return f"Bağlam:\n{_group_ctx(results)}\n\nSoru: {question}"


def answer(question: str, results, history: list[dict] | None = None) -> str:
    history = list(history or [])
    if history:
        history, results = conversation.fit_budget(
            history, results, question, system=SYSTEM,
            limit=3000 - 12 * len({c.source for c, _ in results}))
    resp = llm.chat(
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
    resp = llm.chat(
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
    resp = llm.chat(
        messages=[{"role": "system", "content": meta_system()},
                  {"role": "user", "content": question}],
        options=config.LLM_OPTIONS, keep_alive=config.LLM_KEEP_ALIVE, think=config.LLM_THINK,
    )
    return resp["message"]["content"].strip()
