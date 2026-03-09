//+------------------------------------------------------------------+
//|                                             AutoTrendline_v2.mq5 |
//|                           Smart Trendline Detector - Version 2   |
//|                                                                  |
//| V2 CHANGES:                                                      |
//| - Detects trend direction (uptrend/downtrend)                    |
//| - Draws ONLY relevant trendline (support OR resistance)          |
//| - ALWAYS uses MONTHLY data (displays on all timeframes)          |
//| - Angle validation (5-70 degrees)                                |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot V2"
#property link      ""
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    LookbackBars = 60;        // Lookback period for major swing
input int    SwingOrder = 5;           // Swing detection order
input int    TrendDetectionBars = 20;  // Bars for trend detection
input double MinAngle = 5.0;           // Minimum valid angle (degrees)
input double MaxAngle = 70.0;          // Maximum valid angle (degrees)
input color  SupportColor = clrDodgerBlue;   // Support trendline color
input color  ResistanceColor = clrCrimson;   // Resistance trendline color
input int    LineWidth = 3;            // Trendline width
input ENUM_LINE_STYLE LineStyle = STYLE_DASH; // Line style
input bool   ShowInfo = true;          // Show info label

//--- Global variables
string trendlineName = "AutoTrendline_V2";
string infoLabelName = "AutoTrendline_Info";

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== AutoTrendline V2 Initialized ===");
   Print("This indicator ALWAYS uses MONTHLY data");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   // Only calculate on new bar
   static datetime lastTime = 0;
   if(rates_total > 0 && time[rates_total-1] == lastTime)
      return(rates_total);

   if(rates_total > 0)
      lastTime = time[rates_total-1];

   // Delete old objects
   ObjectDelete(0, trendlineName);
   ObjectDelete(0, infoLabelName);

   // FORCE MONTHLY TIMEFRAME - Get data from MN1
   Print("Fetching MONTHLY data...");

   double monthlyHigh[], monthlyLow[], monthlyClose[];
   datetime monthlyTime[];

   // Copy MONTHLY data (MN1)
   int monthlyBars = CopyHigh(_Symbol, PERIOD_MN1, 0, 120, monthlyHigh);
   CopyLow(_Symbol, PERIOD_MN1, 0, 120, monthlyLow);
   CopyClose(_Symbol, PERIOD_MN1, 0, 120, monthlyClose);
   CopyTime(_Symbol, PERIOD_MN1, 0, 120, monthlyTime);

   if(monthlyBars < 50)
   {
      Print("ERROR: Not enough monthly data. Got ", monthlyBars, " bars");
      return(rates_total);
   }

   Print("Successfully loaded ", monthlyBars, " monthly bars");

   // Detect trend direction from monthly data
   string trend = DetectTrendDirection(monthlyClose, monthlyHigh, monthlyLow, monthlyBars, TrendDetectionBars);
   Print("DETECTED TREND: ", trend);

   // Find swing points on MONTHLY data
   int swingHighs[], swingLows[];
   FindSwingPoints(monthlyBars, monthlyHigh, monthlyLow, SwingOrder, swingHighs, swingLows);

   Print("Found ", ArraySize(swingHighs), " monthly swing highs");
   Print("Found ", ArraySize(swingLows), " monthly swing lows");

   // Based on trend, find ONLY the relevant trendline
   bool isSupport = (trend == "UPTREND");
   int idx1, idx2;
   double price1, price2;
   bool found = false;

   if(isSupport && ArraySize(swingLows) > 0)
   {
      // Draw support for uptrend
      Print("Drawing SUPPORT trendline (uptrend detected)...");
      found = FindMajorTrendline(monthlyBars, monthlyLow, swingLows, LookbackBars, idx1, idx2, price1, price2);
   }
   else if(!isSupport && ArraySize(swingHighs) > 0)
   {
      // Draw resistance for downtrend
      Print("Drawing RESISTANCE trendline (downtrend detected)...");
      found = FindMajorTrendline(monthlyBars, monthlyHigh, swingHighs, LookbackBars, idx1, idx2, price1, price2);
   }

   if(found)
   {
      // Validate angle
      double angle = CalculateAngle(idx1, price1, idx2, price2);

      if(angle < MinAngle || angle > MaxAngle)
      {
         Print("WARNING: Angle ", DoubleToString(angle, 1), "° out of range (",
               MinAngle, "-", MaxAngle, "°) - Trendline rejected");
         return(rates_total);
      }

      // Draw trendline using MONTHLY times
      datetime time1 = monthlyTime[idx1];
      datetime time2 = monthlyTime[idx2];

      color lineColor = isSupport ? SupportColor : ResistanceColor;
      DrawTrendline(trendlineName, time1, price1, time2, price2, lineColor, isSupport);

      double slope = (price2 - price1) / (idx2 - idx1);
      string direction = (slope > 0) ? "BULLISH" : "BEARISH";

      Print("SUCCESS: ", (isSupport ? "SUPPORT" : "RESISTANCE"), " trendline drawn");
      Print("  From: Bar ", idx1, " @ ", DoubleToString(price1, 5));
      Print("  To:   Bar ", idx2, " @ ", DoubleToString(price2, 5));
      Print("  Slope: ", DoubleToString(slope, 8));
      Print("  Angle: ", DoubleToString(angle, 1), "°");
      Print("  Direction: ", direction);

      // Draw info label
      if(ShowInfo)
      {
         string info = StringFormat("%s TRENDLINE\nTrend: %s\nAngle: %.1f°\nDirection: %s\n(Monthly Data)",
                                   isSupport ? "SUPPORT" : "RESISTANCE",
                                   trend,
                                   angle,
                                   direction);
         DrawInfoLabel(info, lineColor);
      }
   }
   else
   {
      Print("ERROR: Could not find valid trendline");
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Detect trend direction                                           |
//+------------------------------------------------------------------+
string DetectTrendDirection(const double &close[], const double &high[],
                           const double &low[], int total, int lookback)
{
   if(total < lookback + 50)
      return "UPTREND"; // Default

   // Calculate simple MA
   int maPeriod = MathMin(50, total - 1);
   double ma = 0;
   for(int i = total - maPeriod; i < total; i++)
      ma += close[i];
   ma /= maPeriod;

   double currentPrice = close[total - 1];

   // Recent price action
   int recentStart = total - lookback;
   double firstPrice = close[recentStart];
   double lastPrice = close[total - 1];
   double priceChange = lastPrice - firstPrice;

   // Higher highs and higher lows
   bool higherHighs = high[total - 1] > high[recentStart];
   bool higherLows = low[total - 1] > low[recentStart];

   // Count signals
   int uptrendSignals = 0;
   int downtrendSignals = 0;

   if(currentPrice > ma)
      uptrendSignals++;
   else
      downtrendSignals++;

   if(priceChange > 0)
      uptrendSignals++;
   else
      downtrendSignals++;

   if(higherHighs && higherLows)
      uptrendSignals++;
   else if(!higherHighs && !higherLows)
      downtrendSignals++;

   return (uptrendSignals > downtrendSignals) ? "UPTREND" : "DOWNTREND";
}

//+------------------------------------------------------------------+
//| Find swing highs and lows                                        |
//+------------------------------------------------------------------+
void FindSwingPoints(int total, const double &high[], const double &low[],
                     int order, int &swingHighs[], int &swingLows[])
{
   ArrayResize(swingHighs, 0);
   ArrayResize(swingLows, 0);

   for(int i = order; i < total - order - 1; i++)
   {
      // Check for swing high
      bool isSwingHigh = true;
      for(int j = 1; j <= order; j++)
      {
         if(high[i] <= high[i-j] || high[i] <= high[i+j])
         {
            isSwingHigh = false;
            break;
         }
      }

      if(isSwingHigh)
      {
         int size = ArraySize(swingHighs);
         ArrayResize(swingHighs, size + 1);
         swingHighs[size] = i;
      }

      // Check for swing low
      bool isSwingLow = true;
      for(int j = 1; j <= order; j++)
      {
         if(low[i] >= low[i-j] || low[i] >= low[i+j])
         {
            isSwingLow = false;
            break;
         }
      }

      if(isSwingLow)
      {
         int size = ArraySize(swingLows);
         ArrayResize(swingLows, size + 1);
         swingLows[size] = i;
      }
   }
}

//+------------------------------------------------------------------+
//| Find major trendline                                             |
//+------------------------------------------------------------------+
bool FindMajorTrendline(int total, const double &price[], const int &swings[],
                        int lookback, int &idx1, int &idx2, double &price1, double &price2)
{
   if(ArraySize(swings) < 1)
      return false;

   int lookbackStart = MathMax(0, total - lookback);

   // Find absolute min/max in lookback
   idx1 = lookbackStart;
   price1 = price[lookbackStart];

   for(int i = lookbackStart; i < total - 3; i++)
   {
      if(price[i] < price1 || price[i] > price1) // Works for both min and max search
      {
         // Determine direction
         bool searchingMin = true;
         if(ArraySize(swings) > 0)
         {
            double avgSwing = 0;
            for(int s = 0; s < ArraySize(swings); s++)
               avgSwing += price[swings[s]];
            avgSwing /= ArraySize(swings);
            searchingMin = (avgSwing < price[total-1]);
         }

         if((searchingMin && price[i] < price1) || (!searchingMin && price[i] > price1))
         {
            price1 = price[i];
            idx1 = i;
         }
      }
   }

   // Find most recent swing after idx1
   idx2 = -1;
   for(int i = ArraySize(swings) - 1; i >= 0; i--)
   {
      if(swings[i] > idx1 && swings[i] < total - 3)
      {
         idx2 = swings[i];
         break;
      }
   }

   if(idx2 == -1)
   {
      for(int i = ArraySize(swings) - 1; i >= 0; i--)
      {
         if(swings[i] < idx1 && swings[i] >= lookbackStart)
         {
            idx2 = idx1;
            price2 = price1;
            idx1 = swings[i];
            price1 = price[idx1];
            return true;
         }
      }
      return false;
   }

   price2 = price[idx2];
   return true;
}

//+------------------------------------------------------------------+
//| Calculate angle                                                  |
//+------------------------------------------------------------------+
double CalculateAngle(int x1, double y1, int x2, double y2)
{
   if(x2 == x1)
      return 90.0;

   double slope = (y2 - y1) / (x2 - x1);
   double avgPrice = (y1 + y2) / 2.0;
   double angleRad = MathArctan(slope / avgPrice * 100);
   double angleDeg = angleRad * 180.0 / M_PI;

   return MathAbs(angleDeg);
}

//+------------------------------------------------------------------+
//| Draw trendline                                                   |
//+------------------------------------------------------------------+
void DrawTrendline(string name, datetime time1, double price1,
                   datetime time2, double price2, color clr, bool isSupport)
{
   ObjectCreate(0, name, OBJ_TREND, 0, time1, price1, time2, price2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, LineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);

   string desc = (isSupport ? "Support" : "Resistance") + " (Monthly)";
   ObjectSetString(0, name, OBJPROP_TEXT, desc);
}

//+------------------------------------------------------------------+
//| Draw info label                                                  |
//+------------------------------------------------------------------+
void DrawInfoLabel(string text, color clr)
{
   int x = 10;
   int y = 30;

   ObjectCreate(0, infoLabelName, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, infoLabelName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, infoLabelName, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, infoLabelName, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, infoLabelName, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, infoLabelName, OBJPROP_FONTSIZE, 10);
   ObjectSetString(0, infoLabelName, OBJPROP_FONT, "Arial Bold");
   ObjectSetString(0, infoLabelName, OBJPROP_TEXT, text);
   ObjectSetInteger(0, infoLabelName, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Deinitialize                                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectDelete(0, trendlineName);
   ObjectDelete(0, infoLabelName);
   Print("AutoTrendline V2 Removed");
}
//+------------------------------------------------------------------+
