import yfinance as yf


def fetch_gas_history(ticker="TTF=F"):
    """Historique complet des cloture du gaz (TTF=F par defaut), sans valeurs vides."""
    return yf.Ticker(ticker).history(period="max")["Close"].dropna()


if __name__ == "__main__":
    h = fetch_gas_history()
    print(len(h), "points,", h.index[0].date(), "->", h.index[-1].date())   # attendu : ~2250 points