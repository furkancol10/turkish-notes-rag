from src.chunker import chunk_by_heading
from src.loader import Doc


def test_oversized_heading_section_is_split_with_overlap():
    body = " ".join(f"kelime{i}" for i in range(400))
    d = Doc("a.md", f"# Baslik\n{body}\n# Kisa\nx")
    cs = chunk_by_heading(d, size=200, overlap=20)
    assert len(cs) > 3
    assert all(len(c.text) <= 200 for c in cs)
    assert cs[0].heading == "Baslik" and cs[1].heading == "Baslik"
    assert cs[-1].heading == "Kisa"
    assert [c.id for c in cs] == [f"a.md#{i}" for i in range(len(cs))]
    assert cs[0].text[-20:] in cs[1].text  # örtüşme
