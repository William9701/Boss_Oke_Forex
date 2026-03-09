//+------------------------------------------------------------------+
//|                                   DoubleTopBottomDetector_v5.mq5 |
//|                         Professional Double Top/Bottom Detection |
//|                                   Monthly Data - All Timeframes  |
//|                                                                  |
//| V5 Changes:                                                      |
//| - Added prominence filter (min 7%) - only major structural peaks |
//| - Line intersection check with tolerance (2%)                    |
//| - Market respect validation - checks next 15 bars after pattern  |
//| - Increased MAX_BARS_APART to 120 for long-term patterns         |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot"
#property link      ""
#property version   "5.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters - OPTIMIZED VALUES V5
input int    LookbackBars = 240;           // Lookback period (20 years)
input int    SwingOrder = 5;               // Swing point order
input double MinProminence = 7.0;          // V5: Min % prominence for valid swing points
input double HorizontalThreshold = 3.5;    // Max % price difference for horizontal check
input double MaxSlopeAngle = 2.8;          // Max slope angle in degrees
input double MinValleyDrop = 5.0;          // Min % valley/peak between patterns
input int    MinBarsApart = 3;             // Min bars between peaks/bottoms
input int    MaxBarsApart = 120;           // V5: Max bars between peaks/bottoms (10 years)
input double IntersectionTolerance = 2.0;  // V5: Tolerance % for line intersection
input int    BarsToCheckAfter = 15;        // V5: Bars to check after pattern for market respect
input color  DoubleTopColor = clrRed;      // Double top color
input color  DoubleBottomColor = clrLime;  // Double bottom color
input int    LineWidth = 3;                // Connecting line width

//--- Global arrays for monthly data
datetime g_monthlyTime[];
double   g_monthlyHigh[];
double   g_monthlyLow[];
int      g_swingHighs[];
int      g_swingLows[];
double   g_swingHighProminence[];
double   g_swingLowProminence[];
int      g_numSwingHighs;
int      g_numSwingLows;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== Double Top/Bottom Detector V5 Started ===");
   Print("Min prominence: ", MinProminence, "%");
   Print("Horizontal threshold: ", HorizontalThreshold, "%");
   Print("Max slope angle: ", MaxSlopeAngle, " degrees");
   Print("V5: Prominence filter + Line intersection + Market respect checks");
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

   // Find swing points with prominence
   FindSwingPointsWithProminence();

   Print("Found ", g_numSwingHighs, " prominent swing highs and ", g_numSwingLows, " prominent swing lows");

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
// V5: Calculate prominence of a swing point
double CalculateProminence(int idx, bool isHigh)
{
   double centerPrice = isHigh ? g_monthlyHigh[idx] : g_monthlyLow[idx];

   int lookback = 15;
   int startIdx = MathMax(0, idx - lookback);
   int endIdx = MathMin(LookbackBars - 1, idx + lookback);

   double minInRange = centerPrice;
   double maxInRange = centerPrice;

   for(int i = startIdx; i <= endIdx; i++)
   {
      if(i == idx) continue;

      if(isHigh)
      {
         if(g_monthlyHigh[i] > maxInRange) maxInRange = g_monthlyHigh[i];
         if(g_monthlyLow[i] < minInRange) minInRange = g_monthlyLow[i];
      }
      else
      {
         if(g_monthlyLow[i] < minInRange) minInRange = g_monthlyLow[i];
         if(g_monthlyHigh[i] > maxInRange) maxInRange = g_monthlyHigh[i];
      }
   }

   double prominence;
   if(isHigh)
      prominence = (centerPrice - minInRange) / centerPrice * 100.0;
   else
      prominence = (maxInRange - centerPrice) / centerPrice * 100.0;

   return prominence;
}

//+------------------------------------------------------------------+
// V5: Find swing points and filter by prominence
void FindSwingPointsWithProminence()
{
   ArrayResize(g_swingHighs, 0);
   ArrayResize(g_swingLows, 0);
   ArrayResize(g_swingHighProminence, 0);
   ArrayResize(g_swingLowProminence, 0);
   g_numSwingHighs = 0;
   g_numSwingLows = 0;

   // Find swing highs
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
         double prominence = CalculateProminence(i, true);

         if(prominence >= MinProminence)
         {
            ArrayResize(g_swingHighs, g_numSwingHighs + 1);
            ArrayResize(g_swingHighProminence, g_numSwingHighs + 1);
            g_swingHighs[g_numSwingHighs] = i;
            g_swingHighProminence[g_numSwingHighs] = prominence;
            g_numSwingHighs++;
         }
      }
   }

   // Find swing lows
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
         double prominence = CalculateProminence(i, false);

         if(prominence >= MinProminence)
         {
            ArrayResize(g_swingLows, g_numSwingLows + 1);
            ArrayResize(g_swingLowProminence, g_numSwingLows + 1);
            g_swingLows[g_numSwingLows] = i;
            g_swingLowProminence[g_numSwingLows] = prominence;
            g_numSwingLows++;
         }
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

   double angleRadians = MathArctan(priceDiffPercent / barDistance);
   double angleDegrees = angleRadians * 180.0 / M_PI;

   return angleDegrees;
}

//+------------------------------------------------------------------+
// V5: Check if line intersects chart (cuts through price action)
bool LineIntersectsChart(int firstIdx, int secondIdx, double linePrice, bool isTop)
{
   double toleranceBuffer = linePrice * IntersectionTolerance / 100.0;

   for(int k = firstIdx + 1; k < secondIdx; k++)
   {
      if(isTop)
      {
         if(g_monthlyHigh[k] > (linePrice + toleranceBuffer))
            return true;
      }
      else
      {
         if(g_monthlyLow[k] < (linePrice - toleranceBuffer))
            return true;
      }
   }

   return false;
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

         int barDistance = secondIdx - firstIdx;
         if(barDistance < MinBarsApart || barDistance > MaxBarsApart)
            continue;

         double firstHigh = g_monthlyHigh[firstIdx];
         double secondHigh = g_monthlyHigh[secondIdx];

         double avgHigh = (firstHigh + secondHigh) / 2.0;
         double heightDiff = MathAbs(firstHigh - secondHigh) / avgHigh * 100.0;

         if(heightDiff > HorizontalThreshold)
            continue;

         double slopeAngle = CalculateSlopeAngle(firstHigh, secondHigh, barDistance);
         if(slopeAngle > MaxSlopeAngle)
            continue;

         // V5: Check if line intersects chart
         if(LineIntersectsChart(firstIdx, secondIdx, avgHigh, true))
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

         // V5: Check if market respected the level (price should NOT go higher after)
         int barsToCheck = MathMin(BarsToCheckAfter, LookbackBars - secondIdx - 1);
         if(barsToCheck >= 10)
         {
            double maxHighAfter = g_monthlyHigh[secondIdx + 1];
            for(int k = secondIdx + 2; k <= secondIdx + barsToCheck; k++)
            {
               if(g_monthlyHigh[k] > maxHighAfter)
                  maxHighAfter = g_monthlyHigh[k];
            }

            if(maxHighAfter > secondHigh)
               continue; // Market went higher - not respected
         }

         // Valid Double Top found - Draw it!
         string patternID = IntegerToString(count);

         DrawHorizontalLine(g_monthlyTime[firstIdx], firstHigh,
                          g_monthlyTime[secondIdx], secondHigh,
                          "DT_LINE_" + patternID, DoubleTopColor);

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

         int barDistance = secondIdx - firstIdx;
         if(barDistance < MinBarsApart || barDistance > MaxBarsApart)
            continue;

         double firstLow = g_monthlyLow[firstIdx];
         double secondLow = g_monthlyLow[secondIdx];

         double avgLow = (firstLow + secondLow) / 2.0;
         double heightDiff = MathAbs(firstLow - secondLow) / avgLow * 100.0;

         if(heightDiff > HorizontalThreshold)
            continue;

         double slopeAngle = CalculateSlopeAngle(firstLow, secondLow, barDistance);
         if(slopeAngle > MaxSlopeAngle)
            continue;

         // V5: Check if line intersects chart
         if(LineIntersectsChart(firstIdx, secondIdx, avgLow, false))
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

         // V5: Check if market respected the level (price should NOT go lower after)
         int barsToCheck = MathMin(BarsToCheckAfter, LookbackBars - secondIdx - 1);
         if(barsToCheck >= 10)
         {
            double minLowAfter = g_monthlyLow[secondIdx + 1];
            for(int k = secondIdx + 2; k <= secondIdx + barsToCheck; k++)
            {
               if(g_monthlyLow[k] < minLowAfter)
                  minLowAfter = g_monthlyLow[k];
            }

            if(minLowAfter < secondLow)
               continue; // Market went lower - not respected
         }

         // Valid Double Bottom found - Draw it!
         string patternID = IntegerToString(count);

         DrawHorizontalLine(g_monthlyTime[firstIdx], firstLow,
                          g_monthlyTime[secondIdx], secondLow,
                          "DB_LINE_" + patternID, DoubleBottomColor);

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
