//+------------------------------------------------------------------+
//|                                     DoubleTopBottomDetector.mq5 |
//|                         Professional Double Top/Bottom Detection |
//|                                   Monthly Data - All Timeframes  |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters - OPTIMIZED VALUES
input int    LookbackBars = 240;           // Lookback period (20 years)
input int    SwingOrder = 5;               // Swing point order
input double HorizontalThreshold = 3.5;    // Max % price difference for horizontal check
input double MaxSlopeAngle = 3.2;          // Max slope angle in degrees
input double MinValleyDrop = 5.0;          // Min % valley/peak between patterns
input int    MinBarsApart = 3;             // Min bars between peaks/bottoms
input int    MaxBarsApart = 50;            // Max bars between peaks/bottoms
input color  DoubleTopColor = clrRed;      // Double top color
input color  DoubleBottomColor = clrLime;  // Double bottom color
input int    LineWidth = 3;                // Connecting line width

//--- Global arrays for monthly data
datetime g_monthlyTime[];
double   g_monthlyHigh[];
double   g_monthlyLow[];
int      g_swingHighs[];
int      g_swingLows[];
int      g_numSwingHighs;
int      g_numSwingLows;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== Double Top/Bottom Detector Started ===");
   Print("Horizontal threshold: ", HorizontalThreshold, "%");
   Print("Max slope angle: ", MaxSlopeAngle, " degrees");
   Print("Min valley/peak: ", MinValleyDrop, "%");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, "DT_");
   ObjectsDeleteAll(0, "DB_");
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
   static datetime lastBar = 0;
   if(time[rates_total-1] == lastBar)
      return(rates_total);
   lastBar = time[rates_total-1];

   // Clear previous drawings
   ObjectsDeleteAll(0, "DT_");
   ObjectsDeleteAll(0, "DB_");

   // Load monthly data
   if(!LoadMonthlyData())
      return(rates_total);

   // Find swing points
   FindSwingPoints();

   Print("Found ", g_numSwingHighs, " swing highs and ", g_numSwingLows, " swing lows");

   // Detect patterns
   int dtCount = DetectDoubleTops();
   int dbCount = DetectDoubleBottoms();

   Print("Detected: ", dtCount, " Double Tops, ", dbCount, " Double Bottoms");

   return(rates_total);
}

//+------------------------------------------------------------------+
bool LoadMonthlyData()
{
   string symbol = Symbol();

   if(CopyTime(symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyTime) < LookbackBars)
      return false;
   if(CopyHigh(symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyHigh) < LookbackBars)
      return false;
   if(CopyLow(symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyLow) < LookbackBars)
      return false;

   ArraySetAsSeries(g_monthlyTime, true);
   ArraySetAsSeries(g_monthlyHigh, true);
   ArraySetAsSeries(g_monthlyLow, true);

   return true;
}

//+------------------------------------------------------------------+
void FindSwingPoints()
{
   ArrayResize(g_swingHighs, 0);
   ArrayResize(g_swingLows, 0);
   g_numSwingHighs = 0;
   g_numSwingLows = 0;

   // Find swing highs (local maxima)
   for(int i = SwingOrder; i < LookbackBars - SwingOrder; i++)
   {
      bool isSwingHigh = true;

      for(int j = i - SwingOrder; j <= i + SwingOrder; j++)
      {
         if(j == i) continue;
         if(g_monthlyHigh[j] >= g_monthlyHigh[i])
         {
            isSwingHigh = false;
            break;
         }
      }

      if(isSwingHigh)
      {
         ArrayResize(g_swingHighs, g_numSwingHighs + 1);
         g_swingHighs[g_numSwingHighs] = i;
         g_numSwingHighs++;
      }
   }

   // Find swing lows (local minima)
   for(int i = SwingOrder; i < LookbackBars - SwingOrder; i++)
   {
      bool isSwingLow = true;

      for(int j = i - SwingOrder; j <= i + SwingOrder; j++)
      {
         if(j == i) continue;
         if(g_monthlyLow[j] <= g_monthlyLow[i])
         {
            isSwingLow = false;
            break;
         }
      }

      if(isSwingLow)
      {
         ArrayResize(g_swingLows, g_numSwingLows + 1);
         g_swingLows[g_numSwingLows] = i;
         g_numSwingLows++;
      }
   }
}

//+------------------------------------------------------------------+
double CalculateSlopeAngle(double price1, double price2, int barDistance)
{
   if(barDistance == 0)
      return 0.0;

   double avgPrice = (price1 + price2) / 2.0;
   double priceDiffPercent = MathAbs(price2 - price1) / avgPrice * 100.0;

   // Calculate angle: tan(angle) = rise/run
   double angleRadians = MathArctan(priceDiffPercent / barDistance);
   double angleDegrees = angleRadians * 180.0 / M_PI;

   return angleDegrees;
}

//+------------------------------------------------------------------+
int DetectDoubleTops()
{
   int count = 0;

   for(int i = 0; i < g_numSwingHighs; i++)
   {
      for(int j = i + 1; j < g_numSwingHighs; j++)
      {
         int firstIdx = g_swingHighs[i];
         int secondIdx = g_swingHighs[j];

         // Check bar distance
         int barDistance = secondIdx - firstIdx;
         if(barDistance < MinBarsApart || barDistance > MaxBarsApart)
            continue;

         double firstHigh = g_monthlyHigh[firstIdx];
         double secondHigh = g_monthlyHigh[secondIdx];

         // Check horizontal alignment
         double avgHigh = (firstHigh + secondHigh) / 2.0;
         double heightDiff = MathAbs(firstHigh - secondHigh) / avgHigh * 100.0;

         if(heightDiff > HorizontalThreshold)
            continue;

         // Check slope angle
         double slopeAngle = CalculateSlopeAngle(firstHigh, secondHigh, barDistance);
         if(slopeAngle > MaxSlopeAngle)
            continue;

         // Check for valley between them
         double valleyLow = g_monthlyLow[firstIdx];
         for(int k = firstIdx; k <= secondIdx; k++)
         {
            if(g_monthlyLow[k] < valleyLow)
               valleyLow = g_monthlyLow[k];
         }

         double valleyDrop = (avgHigh - valleyLow) / avgHigh * 100.0;
         if(valleyDrop < MinValleyDrop)
            continue;

         // Valid Double Top found - Draw it!
         string patternID = IntegerToString(count);

         // Draw horizontal line connecting the two peaks (like PNG)
         DrawHorizontalLine(g_monthlyTime[firstIdx], firstHigh,
                          g_monthlyTime[secondIdx], secondHigh,
                          "DT_LINE_" + patternID, DoubleTopColor);

         // Draw peak markers
         DrawPeakMarker(g_monthlyTime[firstIdx], firstHigh,
                       "DT_MARKER1_" + patternID, DoubleTopColor, true);
         DrawPeakMarker(g_monthlyTime[secondIdx], secondHigh,
                       "DT_MARKER2_" + patternID, DoubleTopColor, true);

         // Draw label
         datetime midTime = (datetime)((g_monthlyTime[firstIdx] + g_monthlyTime[secondIdx]) / 2);
         double midPrice = (firstHigh + secondHigh) / 2.0;
         DrawLabel(midTime, midPrice, "DT_LABEL_" + patternID, "DOUBLE TOP", DoubleTopColor, true);

         count++;
      }
   }

   return count;
}

//+------------------------------------------------------------------+
int DetectDoubleBottoms()
{
   int count = 0;

   for(int i = 0; i < g_numSwingLows; i++)
   {
      for(int j = i + 1; j < g_numSwingLows; j++)
      {
         int firstIdx = g_swingLows[i];
         int secondIdx = g_swingLows[j];

         // Check bar distance
         int barDistance = secondIdx - firstIdx;
         if(barDistance < MinBarsApart || barDistance > MaxBarsApart)
            continue;

         double firstLow = g_monthlyLow[firstIdx];
         double secondLow = g_monthlyLow[secondIdx];

         // Check horizontal alignment
         double avgLow = (firstLow + secondLow) / 2.0;
         double heightDiff = MathAbs(firstLow - secondLow) / avgLow * 100.0;

         if(heightDiff > HorizontalThreshold)
            continue;

         // Check slope angle
         double slopeAngle = CalculateSlopeAngle(firstLow, secondLow, barDistance);
         if(slopeAngle > MaxSlopeAngle)
            continue;

         // Check for peak between them
         double peakHigh = g_monthlyHigh[firstIdx];
         for(int k = firstIdx; k <= secondIdx; k++)
         {
            if(g_monthlyHigh[k] > peakHigh)
               peakHigh = g_monthlyHigh[k];
         }

         double peakRise = (peakHigh - avgLow) / avgLow * 100.0;
         if(peakRise < MinValleyDrop)
            continue;

         // Valid Double Bottom found - Draw it!
         string patternID = IntegerToString(count);

         // Draw horizontal line connecting the two bottoms (like PNG)
         DrawHorizontalLine(g_monthlyTime[firstIdx], firstLow,
                          g_monthlyTime[secondIdx], secondLow,
                          "DB_LINE_" + patternID, DoubleBottomColor);

         // Draw bottom markers
         DrawPeakMarker(g_monthlyTime[firstIdx], firstLow,
                       "DB_MARKER1_" + patternID, DoubleBottomColor, false);
         DrawPeakMarker(g_monthlyTime[secondIdx], secondLow,
                       "DB_MARKER2_" + patternID, DoubleBottomColor, false);

         // Draw label
         datetime midTime = (datetime)((g_monthlyTime[firstIdx] + g_monthlyTime[secondIdx]) / 2);
         double midPrice = (firstLow + secondLow) / 2.0;
         DrawLabel(midTime, midPrice, "DB_LABEL_" + patternID, "DOUBLE BOTTOM", DoubleBottomColor, false);

         count++;
      }
   }

   return count;
}

//+------------------------------------------------------------------+
void DrawHorizontalLine(datetime time1, double price1, datetime time2, double price2,
                       string name, color clr)
{
   ObjectDelete(0, name);

   if(ObjectCreate(0, name, OBJ_TREND, 0, time1, price1, time2, price2))
   {
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, LineWidth);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   }
}

//+------------------------------------------------------------------+
void DrawPeakMarker(datetime time, double price, string name, color clr, bool isTop)
{
   ObjectDelete(0, name);

   if(ObjectCreate(0, name, OBJ_ARROW, 0, time, price))
   {
      if(isTop)
         ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 234); // Down arrow
      else
         ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 233); // Up arrow

      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 4);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
   }
}

//+------------------------------------------------------------------+
void DrawLabel(datetime time, double price, string name, string text,
              color clr, bool isTop)
{
   ObjectDelete(0, name);

   if(ObjectCreate(0, name, OBJ_TEXT, 0, time, price))
   {
      ObjectSetString(0, name, OBJPROP_TEXT, text);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clrWhite);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
      ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);

      if(isTop)
         ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LOWER);
      else
         ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_UPPER);
   }
}
//+------------------------------------------------------------------+
