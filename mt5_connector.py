"""
MT5 Data Connector Module
"""

import MetaTrader5 as mt5
import pandas as pd


class MT5Connector:
    """MT5 connection and data fetching"""

    def __init__(self):
        self.connected = False

    def connect(self):
        """Initialize MT5 connection"""
        if not mt5.initialize():
            print(f"MT5 initialization failed, error code: {mt5.last_error()}")
            return False

        self.connected = True
        print(f"MT5 connected successfully")
        return True

    def disconnect(self):
        """Shutdown MT5 connection"""
        mt5.shutdown()
        self.connected = False
        print("MT5 disconnected")

    def get_ohlc_data(self, symbol, timeframe, num_bars=1000):
        """
        Fetch OHLC data from MT5

        Parameters:
        -----------
        symbol : str
            Trading symbol (e.g., 'EURUSD')
        timeframe : int
            MT5 timeframe constant
        num_bars : int
            Number of bars to fetch

        Returns:
        --------
        pd.DataFrame : OHLC data
        """
        if not self.connected:
            print("Not connected to MT5. Call connect() first.")
            return None

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)

        if rates is None:
            print(f"Failed to get data for {symbol}, error: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        return df


# Timeframe constants
TIMEFRAMES = {
    'M1': mt5.TIMEFRAME_M1,
    'M5': mt5.TIMEFRAME_M5,
    'M15': mt5.TIMEFRAME_M15,
    'M30': mt5.TIMEFRAME_M30,
    'H1': mt5.TIMEFRAME_H1,
    'H4': mt5.TIMEFRAME_H4,
    'D1': mt5.TIMEFRAME_D1,
    'W1': mt5.TIMEFRAME_W1,
    'MN1': mt5.TIMEFRAME_MN1
}
