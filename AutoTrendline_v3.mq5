//+------------------------------------------------------------------+
//|                                             AutoTrendline_v3.mq5 |
//|                           Smart Trendline Detector - Version 3   |
//|                                                                  |
//| V3 CHANGES:                                                      |
//| - IMPROVED trend detection (more reliable)                       |
//| - Uses slope of major trendline to determine trend               |
//| - No more false detections                                       |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot V3"
#property link      ""
#property version   "3.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    LookbackBars = 60;
input int    SwingOrder = 5;
input double MinAngle = 5.0;
input double MaxAngle = 70.0;
input color  SupportColor = clrDodgerBlue;
input color  ResistanceColor = clrCrimson;
input int    LineWidth = 3;
input ENUM_LINE_STYLE LineStyle = STYLE_DASH;
input bool   ShowInfo = true;

//--- Global variables
string trendlineName = "AutoTrendline_V3";
string infoLabelName = "AutoTrendline_Info";

//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== AutoTrendline V3 Initialized ===");
   return(INIT_SUCCEEDED);
}

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
   static datetime lastTime = 0;
   if(rates_total > 0 && time[rates_total-1] == lastTime)
      return(rates_total);

   if(rates_total > 0)
      lastTime = time[rates_total-1];

   ObjectDelete(0, trendlineName);
   ObjectDelete(0, infoLabelName);

   Print("Fetching MONTHLY data...");

   double monthlyHigh[], monthlyLow[], monthlyClose[];
   datetime monthlyTime[];

   int monthlyBars = CopyHigh(_Symbol, PERIOD_MN1, 0, 120, monthlyHigh);
   CopyLow(_Symbol, PERIOD_MN1, 0, 120, monthlyLow);
   CopyClose(_Symbol, PERIOD_MN1, 0, 120, monthlyClose);
   CopyTime(_Symbol, PERIOD_MN1, 0, 120, monthlyTime);

   if(monthlyBars < 50)
   {
      Print("ERROR: Not enough monthly data");
      return(rates_total);
   }

   Print("Loaded ", monthlyBars, " monthly bars");

   // Find swing points
   int swingHighs[], swingLows[];
   FindSwingPoints(monthlyBars, monthlyHigh, monthlyLow, SwingOrder, swingHighs, swingLows);

   Print("Found ", ArraySize(swingHighs), " swing highs");
   Print("Found ", ArraySize(swingLows), " swing lows");

   // Try BOTH support and resistance
   int supportIdx1, supportIdx2, resistanceIdx1, resistanceIdx2;
   double supportPrice1, supportPrice2, resistancePrice1, resistancePrice2;

   bool foundSupport = false;
   bool foundResistance = false;

   if(ArraySize(swingLows) > 0)
      foundSupport = FindMajorTrendline(monthlyBars, monthlyLow, swingLows, LookbackBars,
                                       supportIdx1, supportIdx2, supportPrice1, supportPrice2);

   if(ArraySize(swingHighs) > 0)
      foundResistance = FindMajorTrendline(monthlyBars, monthlyHigh, swingHighs, LookbackBars,
                                          resistanceIdx1, resistanceIdx2, resistancePrice1, resistancePrice2);

   // Calculate slopes
   double supportSlope = 0;
   double resistanceSlope = 0;

   if(foundSupport)
      supportSlope = (supportPrice2 - supportPrice1) / (supportIdx2 - supportIdx1);

   if(foundResistance)
      resistanceSlope = (resistancePrice2 - resistancePrice1) / (resistanceIdx2 - resistanceIdx1);

   // SMART DECISION: Choose based on slope direction and current price position
   bool drawSupport = false;
   string trend = "";

   if(foundSupport && foundResistance)
   {
      // If support is RISING (bullish) - draw support
      // If resistance is FALLING (bearish) - draw resistance
      if(supportSlope > 0)
      {
         drawSupport = true;
         trend = "UPTREND";
      }
      else if(resistanceSlope < 0)
      {
         drawSupport = false;
         trend = "DOWNTREND";
      }
      else
      {
         // Both slopes same direction - choose based on recency
         drawSupport = (supportIdx2 > resistanceIdx2);
         trend = drawSupport ? "UPTREND" : "DOWNTREND";
      }
   }
   else if(foundSupport)
   {
      drawSupport = true;
      trend = (supportSlope > 0) ? "UPTREND" : "RANGE";
   }
   else if(foundResistance)
   {
      drawSupport = false;
      trend = (resistanceSlope < 0) ? "DOWNTREND" : "RANGE";
   }
   else
   {
      Print("ERROR: No valid trendlines found");
      return(rates_total);
   }

   // Draw the selected trendline
   int idx1, idx2;
   double price1, price2;
   bool isSupport;

   if(drawSupport)
   {
      idx1 = supportIdx1;
      idx2 = supportIdx2;
      price1 = supportPrice1;
      price2 = supportPrice2;
      isSupport = true;
      Print("Drawing SUPPORT trendline (", trend, ")");
   }
   else
   {
      idx1 = resistanceIdx1;
      idx2 = resistanceIdx2;
      price1 = resistancePrice1;
      price2 = resistancePrice2;
      isSupport = false;
      Print("Drawing RESISTANCE trendline (", trend, ")");
   }

   // Validate angle
   double angle = CalculateAngle(idx1, price1, idx2, price2);

   if(angle < MinAngle || angle > MaxAngle)
   {
      Print("WARNING: Angle out of range - rejected");
      return(rates_total);
   }

   // Draw trendline
   datetime time1 = monthlyTime[idx1];
   datetime time2 = monthlyTime[idx2];

   color lineColor = isSupport ? SupportColor : ResistanceColor;
   DrawTrendline(trendlineName, time1, price1, time2, price2, lineColor, isSupport);

   double slope = (price2 - price1) / (idx2 - idx1);
   string direction = (slope > 0) ? "BULLISH" : "BEARISH";

   Print("SUCCESS: ", (isSupport ? "SUPPORT" : "RESISTANCE"), " trendline");
   Print("  Slope: ", DoubleToString(slope, 8));
   Print("  Angle: ", DoubleToString(angle, 1), "°");
   Print("  Direction: ", direction);

   if(ShowInfo)
   {
      string info = StringFormat("%s TRENDLINE  Trend: %s\nAngle: %.1f°  Direction: %s\n(Monthly Data)",
                                isSupport ? "SUPPORT" : "RESISTANCE",
                                trend,
                                angle,
                                direction);
      DrawInfoLabel(info, lineColor);
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
void FindSwingPoints(int total, const double &high[], const double &low[],
                     int order, int &swingHighs[], int &swingLows[])
{
   ArrayResize(swingHighs, 0);
   ArrayResize(swingLows, 0);

   for(int i = order; i < total - order - 1; i++)
   {
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
bool FindMajorTrendline(int total, const double &price[], const int &swings[],
                        int lookback, int &idx1, int &idx2, double &price1, double &price2)
{
   if(ArraySize(swings) < 1)
      return false;

   int lookbackStart = MathMax(0, total - lookback);

   idx1 = lookbackStart;
   price1 = price[lookbackStart];

   for(int i = lookbackStart; i < total - 3; i++)
   {
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

   string desc = (isSupport ? "Support" : "Resistance") + " (Monthly)";
   ObjectSetString(0, name, OBJPROP_TEXT, desc);
}

//+------------------------------------------------------------------+
void DrawInfoLabel(string text, color clr)
{
   ObjectCreate(0, infoLabelName, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, infoLabelName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, infoLabelName, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, infoLabelName, OBJPROP_YDISTANCE, 30);
   ObjectSetInteger(0, infoLabelName, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, infoLabelName, OBJPROP_FONTSIZE, 10);
   ObjectSetString(0, infoLabelName, OBJPROP_FONT, "Arial Bold");
   ObjectSetString(0, infoLabelName, OBJPROP_TEXT, text);
   ObjectSetInteger(0, infoLabelName, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectDelete(0, trendlineName);
   ObjectDelete(0, infoLabelName);
   Print("AutoTrendline V3 Removed");
}
//+------------------------------------------------------------------+
