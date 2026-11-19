"""Streamlit yalnız bu bilgisayardan erişilebilir olmalı ve kullanım istatistiği göndermemeli."""
import pathlib
import tomllib

CFG = pathlib.Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"


def _cfg():
    return tomllib.loads(CFG.read_text(encoding="utf-8"))


def test_streamlit_localhost_only():
    assert _cfg()["server"]["address"] in ("localhost", "127.0.0.1")


def test_streamlit_no_usage_stats():
    assert _cfg()["browser"]["gatherUsageStats"] is False
