//+------------------------------------------------------------------+
//|                                                AutoTrendline.mq5 |
//|                                  Professional Trendline Detector |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    LookbackBars = 60;        // Lookback period for major swing
input int    SwingOrder = 5;           // Swing detection order
input color  SupportColor = clrBlue;   // Support trendline color
input color  ResistanceColor = clrRed; // Resistance trendline color
input int    LineWidth = 2;            // Trendline width
input ENUM_LINE_STYLE LineStyle = STYLE_DASH; // Line style

//--- Global variables
string supportLineName = "AutoTrendline_Support";
string resistanceLineName = "AutoTrendline_Resistance";

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("AutoTrendline Indicator Initialized");
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
   if(time[rates_total-1] == lastTime)
      return(rates_total);
   lastTime = time[rates_total-1];

   // Delete old trendlines
   ObjectDelete(0, supportLineName);
   ObjectDelete(0, resistanceLineName);

   // Find swing points
   int swingHighs[], swingLows[];
   FindSwingPoints(rates_total, high, low, SwingOrder, swingHighs, swingLows);

   Print("Found ", ArraySize(swingHighs), " swing highs and ", ArraySize(swingLows), " swing lows");

   // Find and draw support trendline
   if(ArraySize(swingLows) > 0)
   {
      int idx1, idx2;
      double price1, price2;
      if(FindMajorTrendline(rates_total, low, swingLows, LookbackBars, idx1, idx2, price1, price2))
      {
         DrawTrendline(supportLineName, time[idx1], price1, time[idx2], price2, SupportColor, true);

         double slope = (price2 - price1) / (idx2 - idx1);
         double angle = CalculateAngle(idx1, price1, idx2, price2);
         Print("SUPPORT: Bar ", idx1, " @ ", price1, " to Bar ", idx2, " @ ", price2,
               " | Slope: ", slope, " | Angle: ", angle, "°");
      }
   }

   // Find and draw resistance trendline
   if(ArraySize(swingHighs) > 0)
   {
      int idx1, idx2;
      double price1, price2;
      if(FindMajorTrendline(rates_total, high, swingHighs, LookbackBars, idx1, idx2, price1, price2))
      {
         DrawTrendline(resistanceLineName, time[idx1], price1, time[idx2], price2, ResistanceColor, false);

         double slope = (price2 - price1) / (idx2 - idx1);
         double angle = CalculateAngle(idx1, price1, idx2, price2);
         Print("RESISTANCE: Bar ", idx1, " @ ", price1, " to Bar ", idx2, " @ ", price2,
               " | Slope: ", slope, " | Angle: ", angle, "°");
      }
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Find swing highs and lows                                        |
//+------------------------------------------------------------------+
void FindSwingPoints(int total, const double &high[], const double &low[],
                     int order, int &swingHighs[], int &swingLows[])
{
   ArrayResize(swingHighs, 0);
   ArrayResize(swingLows, 0);

   // Find swing highs
   for(int i = order; i < total - order - 1; i++)
   {
      bool isSwingHigh = true;

      // Check left side
      for(int j = 1; j <= order; j++)
      {
         if(high[i] <= high[i-j])
         {
            isSwingHigh = false;
            break;
         }
      }

      // Check right side
      if(isSwingHigh)
      {
         for(int j = 1; j <= order; j++)
         {
            if(high[i] <= high[i+j])
            {
               isSwingHigh = false;
               break;
            }
         }
      }

      if(isSwingHigh)
      {
         int size = ArraySize(swingHighs);
         ArrayResize(swingHighs, size + 1);
         swingHighs[size] = i;
      }
   }

   // Find swing lows
   for(int i = order; i < total - order - 1; i++)
   {
      bool isSwingLow = true;

      // Check left side
      for(int j = 1; j <= order; j++)
      {
         if(low[i] >= low[i-j])
         {
            isSwingLow = false;
            break;
         }
      }

      // Check right side
      if(isSwingLow)
      {
         for(int j = 1; j <= order; j++)
         {
            if(low[i] >= low[i+j])
            {
               isSwingLow = false;
               break;
            }
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
//| Find major trendline from absolute low/high to recent swing      |
//+------------------------------------------------------------------+
bool FindMajorTrendline(int total, const double &price[], const int &swings[],
                        int lookback, int &idx1, int &idx2, double &price1, double &price2)
{
   if(ArraySize(swings) < 1)
      return false;

   // Define lookback window
   int lookbackStart = MathMax(0, total - lookback);

   // Find absolute lowest/highest in lookback period
   idx1 = lookbackStart;
   price1 = price[lookbackStart];

   // Determine if we're looking for min or max
   bool isLow = (price[swings[0]] < price[total-1]); // Heuristic

   for(int i = lookbackStart; i < total - 3; i++)
   {
      if(isLow)
      {
         if(price[i] < price1)
         {
            price1 = price[i];
            idx1 = i;
         }
      }
      else
      {
         if(price[i] > price1)
         {
            price1 = price[i];
            idx1 = i;
         }
      }
   }

   // Find most recent swing point after idx1
   idx2 = -1;
   for(int i = ArraySize(swings) - 1; i >= 0; i--)
   {
      if(swings[i] > idx1 && swings[i] < total - 3)
      {
         idx2 = swings[i];
         break;
      }
   }

   // If no swing after idx1, try before
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
//| Calculate trendline angle in degrees                             |
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
//| Draw trendline on chart                                          |
//+------------------------------------------------------------------+
void DrawTrendline(string name, datetime time1, double price1,
                   datetime time2, double price2, color clr, bool isSupport)
{
   // Create trendline
   ObjectCreate(0, name, OBJ_TREND, 0, time1, price1, time2, price2);

   // Set properties
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, LineStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);  // Extend to right
   ObjectSetInteger(0, name, OBJPROP_BACK, true);       // Background
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);

   // Add description
   string desc = (isSupport ? "Support" : "Resistance") + " Trendline";
   ObjectSetString(0, name, OBJPROP_TEXT, desc);
}

//+------------------------------------------------------------------+
//| Indicator deinitialization function                              |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Delete trendlines on removal
   ObjectDelete(0, supportLineName);
   ObjectDelete(0, resistanceLineName);
   Print("AutoTrendline Indicator Removed");
}
//+------------------------------------------------------------------+
