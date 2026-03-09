//+------------------------------------------------------------------+
//|                                   DoubleTopBottomDetector_v6.mq5 |
//|                         Professional Double Top/Bottom Detection |
//|                                   Monthly Data - All Timeframes  |
//|                                                                  |
//| V6 Changes:                                                      |
//| - Separate thresholds for tops and bottoms                       |
//| - Tops: 7% prominence, 3.5% horizontal, 2.8° angle               |
//| - Bottoms: 5% prominence, 12% horizontal, 4.5° angle             |
//| - Minimum 15 bars apart (avoid recent minor patterns)            |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot"
#property link      ""
#property version   "6.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters - V6 SEPARATE THRESHOLDS
input int    LookbackBars = 240;                  // Lookback period (20 years)
input int    SwingOrder = 5;                      // Swing point order
input double MinProminenceTops = 7.0;             // V6: Min % prominence for tops
input double MinProminenceBottoms = 5.0;          // V6: Min % prominence for bottoms
input double HorizontalThresholdTops = 3.5;       // V6: Max % price diff for tops
input double HorizontalThresholdBottoms = 12.0;   // V6: Max % price diff for bottoms
input double MaxSlopeAngleTops = 2.8;             // V6: Max slope angle for tops
input double MaxSlopeAngleBottoms = 4.5;          // V6: Max slope angle for bottoms
input double MinValleyDrop = 5.0;                 // Min % valley/peak between patterns
input int    MinBarsApart = 15;                   // V6: Min bars apart (avoid recent patterns)
input int    MaxBarsApart = 120;                  // Max bars between peaks/bottoms (10 years)
input double IntersectionTolerance = 2.0;         // Tolerance % for line intersection
input int    BarsToCheckAfter = 15;               // Bars to check after pattern for market respect
input color  DoubleTopColor = clrRed;             // Double top color
input color  DoubleBottomColor = clrLime;         // Double bottom color
input int    LineWidth = 3;                       // Connecting line width

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
   Print("=== Double Top/Bottom Detector V6 Started ===");
   Print("V6: SEPARATE THRESHOLDS FOR TOPS AND BOTTOMS");
   Print("  Tops:    Prominence ", MinProminenceTops, "%, Horizontal ", HorizontalThresholdTops, "%, Angle ", MaxSlopeAngleTops, "°");
   Print("  Bottoms: Prominence ", MinProminenceBottoms, "%, Horizontal ", HorizontalThresholdBottoms, "%, Angle ", MaxSlopeAngleBottoms, "°");
   Print("  Min bars apart: ", MinBarsApart);
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
   ArraySetAsSeries(g_monthlyTime, true);
   ArraySetAsSeries(g_monthlyHigh, true);
   ArraySetAsSeries(g_monthlyLow, true);

   int copied = CopyTime(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyTime);
   if(copied <= 0) return false;

   copied = CopyHigh(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyHigh);
   if(copied <= 0) return false;

   copied = CopyLow(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyLow);
   if(copied <= 0) return false;

   return true;
}

//+------------------------------------------------------------------+
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
      for(int j = 1; j <= SwingOrder; j++)
      {
         if(g_monthlyHigh[i] <= g_monthlyHigh[i-j] || g_monthlyHigh[i] <= g_monthlyHigh[i+j])
         {
            isSwingHigh = false;
            break;
         }
      }

      if(isSwingHigh)
      {
         double prominence = CalculateProminence(i, true);
         if(prominence >= MinProminenceTops)
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
      for(int j = 1; j <= SwingOrder; j++)
      {
         if(g_monthlyLow[i] >= g_monthlyLow[i-j] || g_monthlyLow[i] >= g_monthlyLow[i+j])
         {
            isSwingLow = false;
            break;
         }
      }

      if(isSwingLow)
      {
         double prominence = CalculateProminence(i, false);
         if(prominence >= MinProminenceBottoms)
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
   if(barDistance == 0) return 0.0;

   double avgPrice = (price1 + price2) / 2.0;
   double priceDiffPercent = MathAbs(price2 - price1) / avgPrice * 100.0;

   double angleRadians = MathArctan(priceDiffPercent / barDistance);
   double angleDegrees = angleRadians * 180.0 / M_PI;

   return angleDegrees;
}

//+------------------------------------------------------------------+
int DetectDoubleTops()
{
   int patternCount = 0;

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

         // V6: Use TOPS horizontal threshold
         double avgHigh = (firstHigh + secondHigh) / 2.0;
         double heightDiff = MathAbs(firstHigh - secondHigh) / avgHigh * 100.0;

         if(heightDiff > HorizontalThresholdTops)
            continue;

         // V6: Use TOPS angle threshold
         double slopeAngle = CalculateSlopeAngle(firstHigh, secondHigh, barDistance);
         if(slopeAngle > MaxSlopeAngleTops)
            continue;

         // Line intersection check
         double toleranceBuffer = avgHigh * IntersectionTolerance / 100.0;
         bool lineCutsThrough = false;
         for(int k = firstIdx + 1; k < secondIdx; k++)
         {
            if(g_monthlyHigh[k] > (avgHigh + toleranceBuffer))
            {
               lineCutsThrough = true;
               break;
            }
         }

         if(lineCutsThrough)
            continue;

         // Valley check
         double valleyLow = g_monthlyLow[firstIdx];
         for(int k = firstIdx; k <= secondIdx; k++)
         {
            if(g_monthlyLow[k] < valleyLow)
               valleyLow = g_monthlyLow[k];
         }

         double valleyDrop = (avgHigh - valleyLow) / avgHigh * 100.0;
         if(valleyDrop < MinValleyDrop)
            continue;

         // Market respect check
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
               continue;
         }

         // Valid double top - draw it
         DrawPattern(firstIdx, secondIdx, firstHigh, secondHigh, true);
         patternCount++;
      }
   }

   return patternCount;
}

//+------------------------------------------------------------------+
int DetectDoubleBottoms()
{
   int patternCount = 0;

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

         // V6: Use BOTTOMS horizontal threshold (more lenient)
         double avgLow = (firstLow + secondLow) / 2.0;
         double heightDiff = MathAbs(firstLow - secondLow) / avgLow * 100.0;

         if(heightDiff > HorizontalThresholdBottoms)
            continue;

         // V6: Use BOTTOMS angle threshold (more lenient)
         double slopeAngle = CalculateSlopeAngle(firstLow, secondLow, barDistance);
         if(slopeAngle > MaxSlopeAngleBottoms)
            continue;

         // Line intersection check
         double toleranceBuffer = avgLow * IntersectionTolerance / 100.0;
         bool lineCutsThrough = false;
         for(int k = firstIdx + 1; k < secondIdx; k++)
         {
            if(g_monthlyLow[k] < (avgLow - toleranceBuffer))
            {
               lineCutsThrough = true;
               break;
            }
         }

         if(lineCutsThrough)
            continue;

         // Peak check
         double peakHigh = g_monthlyHigh[firstIdx];
         for(int k = firstIdx; k <= secondIdx; k++)
         {
            if(g_monthlyHigh[k] > peakHigh)
               peakHigh = g_monthlyHigh[k];
         }

         double peakRise = (peakHigh - avgLow) / avgLow * 100.0;
         if(peakRise < MinValleyDrop)
            continue;

         // Market respect check
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
               continue;
         }

         // Valid double bottom - draw it
         DrawPattern(firstIdx, secondIdx, firstLow, secondLow, false);
         patternCount++;
      }
   }

   return patternCount;
}

//+------------------------------------------------------------------+
void DrawPattern(int firstIdx, int secondIdx, double firstPrice, double secondPrice, bool isTop)
{
   string patternID = (isTop ? "DT_" : "DB_") + TimeToString(g_monthlyTime[firstIdx]);
   color lineColor = isTop ? DoubleTopColor : DoubleBottomColor;

   // Draw horizontal line
   string lineName = patternID + "_LINE";
   ObjectCreate(0, lineName, OBJ_TREND, 0,
                g_monthlyTime[firstIdx], firstPrice,
                g_monthlyTime[secondIdx], secondPrice);
   ObjectSetInteger(0, lineName, OBJPROP_COLOR, lineColor);
   ObjectSetInteger(0, lineName, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, lineName, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, lineName, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, lineName, OBJPROP_BACK, false);

   // Draw markers
   string marker1 = patternID + "_M1";
   ObjectCreate(0, marker1, isTop ? OBJ_ARROW_DOWN : OBJ_ARROW_UP, 0,
                g_monthlyTime[firstIdx], firstPrice);
   ObjectSetInteger(0, marker1, OBJPROP_COLOR, lineColor);
   ObjectSetInteger(0, marker1, OBJPROP_WIDTH, 3);

   string marker2 = patternID + "_M2";
   ObjectCreate(0, marker2, isTop ? OBJ_ARROW_DOWN : OBJ_ARROW_UP, 0,
                g_monthlyTime[secondIdx], secondPrice);
   ObjectSetInteger(0, marker2, OBJPROP_COLOR, lineColor);
   ObjectSetInteger(0, marker2, OBJPROP_WIDTH, 3);

   // Draw text label
   datetime midTime = g_monthlyTime[firstIdx] + (g_monthlyTime[secondIdx] - g_monthlyTime[firstIdx]) / 2;
   double midPrice = (firstPrice + secondPrice) / 2.0;

   string labelName = patternID + "_LABEL";
   ObjectCreate(0, labelName, OBJ_TEXT, 0, midTime, midPrice);
   ObjectSetString(0, labelName, OBJPROP_TEXT, isTop ? "DOUBLE TOP" : "DOUBLE BOTTOM");
   ObjectSetInteger(0, labelName, OBJPROP_COLOR, lineColor);
   ObjectSetInteger(0, labelName, OBJPROP_FONTSIZE, 10);
   ObjectSetInteger(0, labelName, OBJPROP_ANCHOR, isTop ? ANCHOR_BOTTOM : ANCHOR_TOP);
}
//+------------------------------------------------------------------+
