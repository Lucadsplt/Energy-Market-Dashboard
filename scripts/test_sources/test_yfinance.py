import yfinance as yf

# Deux marchés du gaz : Europe (TTF) et US (Henry Hub)
tickers = {
    "Gaz Europe (TTF)": "TTF=F",
    "Gaz US (Henry Hub)": "NG=F",
}

for nom, symbole in tickers.items():
    print(f"\n=== {nom} — {symbole} ===")
    ticker = yf.Ticker(symbole)
    df = ticker.history(period="5d")  # les 5 derniers jours

    if df.empty:
        print("  Aucune donnee recue (ticker invalide ou marche ferme ?)")
    else:
        print(df[["Open", "High", "Low", "Close", "Volume"]])