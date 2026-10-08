import yfinance as yf


def fetch_close(ticker):
    """Historique complet des clotures d'un ticker Yahoo, avec des dates simples (sans heure ni fuseau)."""
    serie = yf.Ticker(ticker).history(period="max")["Close"].dropna()
    serie.index = serie.index.tz_localize(None).normalize()
    return serie[~serie.index.duplicated()]


def fetch_gas_history(ticker="TTF=F"):
    """Historique complet du gaz (TTF=F par defaut)."""
    return fetch_close(ticker)


def fetch_eurusd():
    """Taux de change EUR/USD (nombre de dollars pour 1 euro)."""
    return fetch_close("EURUSD=X")


if __name__ == "__main__":
    h = fetch_gas_history()
    print(len(h), "points,", h.index[0].date(), "->", h.index[-1].date())