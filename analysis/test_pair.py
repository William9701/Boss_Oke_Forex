from mt5_connector import MT5Connector, TIMEFRAMES

connector = MT5Connector()
if connector.connect():
    print("Testing USDJPY...")
    df = connector.get_ohlc_data('USDJPY', TIMEFRAMES['MN1'], 120)
    if df is not None:
        print(f"SUCCESS - USDJPY fetched {len(df)} bars")
        print(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    else:
        print("USDJPY failed")

    connector.disconnect()
