"""
A curated list of NSE-listed tickers (Yahoo Finance format, '.NS' suffix)
spanning large and mid caps across sectors. This satisfies the assignment's
"at least 100 Indian listed companies" requirement without needing a
ticker-discovery scraper, which would be its own multi-day project.

Feel free to add/remove tickers - everything downstream (ingestion,
backtest engine) just iterates over this list.
"""

NSE_TICKERS: list[str] = [
    # --- Nifty 50 core ---
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BAJAJFINSV.NS", "M&M.NS",
    "NTPC.NS", "POWERGRID.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "GRASIM.NS", "HINDALCO.NS", "COALINDIA.NS", "ONGC.NS", "BPCL.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "EICHERMOT.NS",
    "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "INDUSINDBK.NS", "TECHM.NS", "SBILIFE.NS",
    "HDFCLIFE.NS", "BRITANNIA.NS", "TATACONSUM.NS", "UPL.NS", "SHRIRAMFIN.NS",

    # --- Nifty Next 50 / strong mid-large caps ---
    "PIDILITIND.NS", "GODREJCP.NS", "DABUR.NS", "MARICO.NS", "COLPAL.NS",
    "HAVELLS.NS", "VOLTAS.NS", "SIEMENS.NS", "ABB.NS", "BOSCHLTD.NS",
    "CHOLAFIN.NS", "MUTHOOTFIN.NS", "BAJAJHLDNG.NS", "ICICIPRULI.NS", "ICICIGI.NS",
    "PFC.NS", "RECLTD.NS", "IRFC.NS", "BANKBARODA.NS", "PNB.NS",
    "CANBK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS", "AUBANK.NS", "BANDHANBNK.NS",
    "LUPIN.NS", "AUROPHARMA.NS", "ALKEM.NS", "TORNTPHARM.NS", "ZYDUSLIFE.NS",
    "MPHASIS.NS", "PERSISTENT.NS", "LTIM.NS", "COFORGE.NS", "OFSS.NS",
    "AMBUJACEM.NS", "SHREECEM.NS", "ACC.NS", "DALBHARAT.NS", "RAMCOCEM.NS",
    "VEDL.NS", "NMDC.NS", "SAIL.NS", "JINDALSTEL.NS", "NATIONALUM.NS",
    "GAIL.NS", "IOC.NS", "HINDPETRO.NS", "PETRONET.NS", "OIL.NS",

    # --- Consumer, retail, auto ancillary, diversified ---
    "TRENT.NS", "DMART.NS", "JUBLFOOD.NS", "VBL.NS", "PAGEIND.NS",
    "MOTHERSON.NS", "BHARATFORG.NS", "EXIDEIND.NS", "MRF.NS", "BALKRISIND.NS",
    "ASHOKLEY.NS", "TVSMOTOR.NS", "ESCORTS.NS", "CUMMINSIND.NS", "SRF.NS",
    "PIIND.NS", "DEEPAKNTR.NS", "AARTIIND.NS", "GUJGASLTD.NS", "IGL.NS",
    "CONCOR.NS", "CASTROLIND.NS", "BERGEPAINT.NS", "KANSAINER.NS", "WHIRLPOOL.NS",
]

# NIFTY 50 index, used as the benchmark series.
BENCHMARK_TICKER = "^NSEI"
