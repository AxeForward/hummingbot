import requests
import pandas as pd
import time
from decimal import Decimal
import logging

# Configuration (Matches your v2_funding_rate_arb_real.py)
TOKENS = ["ETH", "SOL"]
CONNECTORS = ["hyperliquid_perpetual", "binance_perpetual"]
POSITION_SIZE_QUOTE = Decimal("100")
LEVERAGE = 20
MIN_PROFITABILITY = Decimal("0.001")
PROFITABILITY_TO_TAKE_PROFIT = Decimal("0.01")

# Constants
FUNDING_PAYMENT_INTERVAL_MAP = {
    "binance_perpetual": 60 * 60 * 8,
    "hyperliquid_perpetual": 60 * 60 * 1
}
FUNDING_PROFITABILITY_INTERVAL = 60 * 60 * 24

# API Endpoints
BINANCE_API_URL = "https://fapi.binance.com"
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"

def get_binance_data(tokens):
    data = {}
    try:
        # Exchange Info for Rules
        exch_info = requests.get(f"{BINANCE_API_URL}/fapi/v1/exchangeInfo").json()
        # Premium Index for Prices/Funding
        premium_index = requests.get(f"{BINANCE_API_URL}/fapi/v1/premiumIndex").json()
        
        premium_map = {item['symbol']: item for item in premium_index}
        
        for token in tokens:
            symbol = f"{token}USDT"
            symbol_info = next((s for s in exch_info['symbols'] if s['symbol'] == symbol), None)
            market_data = premium_map.get(symbol)
            
            if symbol_info and market_data:
                # Extract Rules
                min_qty = 0
                min_notional = 0
                for f in symbol_info['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        min_qty = float(f['minQty'])
                    if f['filterType'] == 'MIN_NOTIONAL':
                        min_notional = float(f['notional'])

                data[token] = {
                    "price": float(market_data['markPrice']),
                    "fundingRate": float(market_data['lastFundingRate']),
                    "min_qty": min_qty,
                    "min_notional": min_notional,
                    "fee": 0.0005  # Assume VIP 0 Taker
                }
    except Exception as e:
        print(f"Error fetching Binance data: {e}")
    return data

def get_hyperliquid_data(tokens):
    data = {}
    try:
        # Meta and Asset Ctxs
        payload = {"type": "metaAndAssetCtxs"}
        response = requests.post(f"{HYPERLIQUID_API_URL}/info", json=payload).json()
        
        universe = response[0]['universe']
        asset_ctxs = response[1]
        
        for token in tokens:
            # Find index of token
            idx = next((i for i, u in enumerate(universe) if u['name'] == token), None)
            if idx is not None:
                ctx = asset_ctxs[idx]
                sz_decimals = universe[idx]['szDecimals']
                
                # HL Rules (Simplified)
                # Min size is usually determined by decimals, but let's assume raw precision
                min_qty = 1 / (10 ** sz_decimals) if sz_decimals else 0.1 # Approximate
                # HL usually has min notional around $10 but not in API meta?
                min_notional = 10.0 

                data[token] = {
                    "price": float(ctx['markPx']),
                    "fundingRate": float(ctx['funding']),
                    "min_qty": min_qty,
                    "min_notional": min_notional,
                    "fee": 0.00025 # Taker
                }
    except Exception as e:
        print(f"Error fetching Hyperliquid data: {e}")
    return data

def get_normalized_funding_rate(rate, connector):
    return rate / FUNDING_PAYMENT_INTERVAL_MAP.get(connector, 28800)

def main():
    print(f"Checking Funding Arb Opportunities without Account Keys...")
    print(f"Tokens: {TOKENS}")
    print(f"Position Size: {POSITION_SIZE_QUOTE} Quote")
    print("-" * 50)

    binance_data = get_binance_data(TOKENS)
    hyperliquid_data = get_hyperliquid_data(TOKENS)

    all_funding_info = []
    
    for token in TOKENS:
        b_data = binance_data.get(token)
        h_data = hyperliquid_data.get(token)

        if not b_data or not h_data:
            print(f"Skipping {token}: Data missing")
            continue

        # 1. Check Rules
        # Binance
        amount_b = float(POSITION_SIZE_QUOTE) / b_data['price']
        valid_b = amount_b >= b_data['min_qty'] and (amount_b * b_data['price']) >= b_data['min_notional']
        msg_b = "OK" if valid_b else f"Fail (Amt: {amount_b:.4f}<{b_data['min_qty']} or Notional < {b_data['min_notional']})"

        # Hyperliquid
        amount_h = float(POSITION_SIZE_QUOTE) / h_data['price']
        valid_h = amount_h >= h_data['min_qty'] and (amount_h * h_data['price']) >= h_data['min_notional']
        msg_h = "OK" if valid_h else f"Fail (Amt: {amount_h:.4f}<{h_data['min_qty']} or Notional < {h_data['min_notional']})"

        # 2. Calculate Funding Arb
        b_rate_norm = get_normalized_funding_rate(b_data['fundingRate'], "binance_perpetual")
        h_rate_norm = get_normalized_funding_rate(h_data['fundingRate'], "hyperliquid_perpetual")
        
        diff = abs(b_rate_norm - h_rate_norm) * FUNDING_PROFITABILITY_INTERVAL
        
        # Decide Side
        # If Bin rate < HL rate: Buy Bin, Sell HL
        if b_rate_norm < h_rate_norm:
            long_conn = "Binance"
            short_conn = "Hyperliquid"
            entry_price_long = b_data['price']
            entry_price_short = h_data['price']
            fee_long = b_data['fee']
            fee_short = h_data['fee']
        else:
            long_conn = "Hyperliquid"
            short_conn = "Binance"
            entry_price_long = h_data['price']
            entry_price_short = b_data['price']
            fee_long = h_data['fee']
            fee_short = b_data['fee']
            
        # 3. Calculate Trade Profitability (PNL after fees)
        # PNL = (Price_Short - Price_Long) / Price_Long  ( Simplified "market entry" simulation )
        # Actually in original code:
        # if Long C1, Short C2:
        # pnl = (Price_C2 - Price_C1) / Price_C1
        
        price_diff_pct = (entry_price_short - entry_price_long) / entry_price_long
        net_profitability = price_diff_pct - fee_long - fee_short

        row = {
            "Token": token,
            "Binance Rate (8h)": f"{b_data['fundingRate']:.4%}",
            "HL Rate (1h)": f"{h_data['fundingRate']:.4%}",
            "Diff (24h)": f"{diff:.4%}",
            "Long": long_conn,
            "Short": short_conn,
            "Trade PNL": f"{net_profitability:.4%}",
            "Binance Rule": msg_b,
            "HL Rule": msg_h
        }
        all_funding_info.append(row)

    df = pd.DataFrame(all_funding_info)
    print(df.to_markdown(index=False))

    print("\n" + "-" * 50)
    print("Minimum Trading Rules Details:")
    min_rules_data = []
    for token in TOKENS:
        b_data = binance_data.get(token)
        h_data = hyperliquid_data.get(token)
        if b_data and h_data:
            min_rules_data.append({
                "Token": token,
                "Bin Min Qty": f"{b_data['min_qty']:.6f}",
                "Bin Min Notional ($)": f"{b_data['min_notional']:.2f}",
                "HL Min Qty": f"{h_data['min_qty']:.6f}",
                "HL Min Notional ($)": f"{h_data['min_notional']:.2f}"
            })
    
    if min_rules_data:
        df_rules = pd.DataFrame(min_rules_data)
        print(df_rules.to_markdown(index=False))

if __name__ == "__main__":
    main()
