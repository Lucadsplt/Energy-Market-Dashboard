import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.distribution import distribution
from pipeline.analysis.returns import log_returns
from pipeline.export.json_export import save_json
from pipeline.sources.oil_history import fetch_brent_history


def analyse_petrole():
    prix = fetch_brent_history(years=5)
    rendements = log_returns(prix)
    return {"brent": {"distribution": distribution(rendements)}}


if __name__ == "__main__":
    resultat = analyse_petrole()
    print(resultat["brent"]["distribution"]["stats"])
    save_json(resultat, "oil_analysis.json")