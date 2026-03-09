//+------------------------------------------------------------------+
//|                                    HeadShouldersDetector_v3.mq5  |
//|                                                                  |
//|  Detects Head & Shoulders and Inverse Head & Shoulders patterns |
//|  V3: With NECKLINE detection and drawing - Major patterns        |
//+------------------------------------------------------------------+
#property copyright "Head & Shoulders Pattern Detector V3"
#property link      ""
#property version   "3.00"
#property indicator_chart_window
#property indicator_plots 0

//--- Input Parameters - V3 FOR MAJOR STRUCTURAL PATTERNS
input int    LookbackBars = 240;                  // Number of bars to analyze (20 years)
input int    SwingOrder = 5;                      // Swing point order
input double MinProminenceShoulders = 8.0;        // V3: Min prominence % for shoulders
input double MinProminenceHead = 10.0;            // V3: Min prominence % for head
input double HeadToShoulderRatio = 1.10;          // V3: Head must be 10% more extreme
input double ShoulderSymmetryTolerance = 30.0;    // V3: Max % diff between shoulders
input double NecklineTolerance = 15.0;            // V3: Max % diff for neckline points
input int    MinBarsApart = 5;                    // Min bars between points
input int    MaxBarsApart = 150;                  // V3: Max bars for full pattern

input color  HSColor = clrRed;                    // Bearish H&S color
input color  InvHSColor = clrGreen;               // Inverse H&S color (bullish)
input color  NecklineColor = clrRed;              // Neckline color
input int    LineWidth = 3;                       // Structure line width
input int    NecklineWidth = 4;                   // Neckline width
input int    LabelFontSize = 10;                  // Label font size

//--- Global arrays for monthly timeframe data
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
   Print("=== Head & Shoulders Detector V3 Started ===");
   Print("V3: With NECKLINE detection for major structural patterns");
   Print("Min prominence: Shoulders ", MinProminenceShoulders, "%, Head ", MinProminenceHead, "%");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, "HS_");
   ObjectsDeleteAll(0, "IHS_");
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
   ObjectsDeleteAll(0, "HS_");
   ObjectsDeleteAll(0, "IHS_");

   // Load monthly data
   if(!LoadMonthlyData())
      return(rates_total);

   // Find swing points with prominence
   FindSwingPointsWithProminence();

   Print("Found ", g_numSwingHighs, " prominent swing highs and ", g_numSwingLows, " prominent swing lows");

   // Detect patterns
   int hsCount = DetectBearishHeadAndShoulders();
   int ihsCount = DetectInverseHeadAndShoulders();

   Print("Detected: ", hsCount, " Bearish H&S, ", ihsCount, " Inverse H&S");

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

   int lookback = 20;
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
         if(prominence >= MinProminenceShoulders)
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
         if(prominence >= MinProminenceShoulders)
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
int DetectInverseHeadAndShoulders()
{
   int patternCount = 0;

   for(int i = 0; i < g_numSwingLows; i++)
   {
      for(int j = i + 1; j < g_numSwingLows; j++)
      {
         for(int k = j + 1; k < g_numSwingLows; k++)
         {
            int lsIdx = g_swingLows[i];
            int hIdx = g_swingLows[j];
            int rsIdx = g_swingLows[k];

            double lsLow = g_monthlyLow[lsIdx];
            double hLow = g_monthlyLow[hIdx];
            double rsLow = g_monthlyLow[rsIdx];

            double hProm = g_swingLowProminence[j];

            // Check bar spacing
            int barsLStoH = hIdx - lsIdx;
            int barsHtoRS = rsIdx - hIdx;

            if(barsLStoH < MinBarsApart || barsHtoRS < MinBarsApart)
               continue;

            if((rsIdx - lsIdx) > MaxBarsApart)
               continue;

            // Head must be significantly lower than both shoulders
            if(hLow >= lsLow * (1.0 - (HeadToShoulderRatio - 1.0)))
               continue;
            if(hLow >= rsLow * (1.0 - (HeadToShoulderRatio - 1.0)))
               continue;

            // Head must have high prominence
            if(hProm < MinProminenceHead)
               continue;

            // Shoulders should be roughly at similar level
            double shoulderDiff = MathAbs(lsLow - rsLow) / ((lsLow + rsLow) / 2.0) * 100.0;
            if(shoulderDiff > ShoulderSymmetryTolerance)
               continue;

            // Find neckline peaks (resistance)
            int peak1Idx = lsIdx;
            double peak1High = g_monthlyHigh[lsIdx];
            for(int idx = lsIdx; idx <= hIdx; idx++)
            {
               if(g_monthlyHigh[idx] > peak1High)
               {
                  peak1High = g_monthlyHigh[idx];
                  peak1Idx = idx;
               }
            }

            int peak2Idx = hIdx;
            double peak2High = g_monthlyHigh[hIdx];
            for(int idx = hIdx; idx <= rsIdx; idx++)
            {
               if(g_monthlyHigh[idx] > peak2High)
               {
                  peak2High = g_monthlyHigh[idx];
                  peak2Idx = idx;
               }
            }

            // Neckline peaks should be roughly at similar level
            double necklineDiff = MathAbs(peak1High - peak2High) / ((peak1High + peak2High) / 2.0) * 100.0;
            if(necklineDiff > NecklineTolerance)
               continue;

            // Valid inverse H&S - draw it
            DrawInverseHS(lsIdx, hIdx, rsIdx, lsLow, hLow, rsLow, peak1Idx, peak2Idx, peak1High, peak2High);
            patternCount++;
         }
      }
   }

   return patternCount;
}

//+------------------------------------------------------------------+
int DetectBearishHeadAndShoulders()
{
   int patternCount = 0;

   for(int i = 0; i < g_numSwingHighs; i++)
   {
      for(int j = i + 1; j < g_numSwingHighs; j++)
      {
         for(int k = j + 1; k < g_numSwingHighs; k++)
         {
            int lsIdx = g_swingHighs[i];
            int hIdx = g_swingHighs[j];
            int rsIdx = g_swingHighs[k];

            double lsHigh = g_monthlyHigh[lsIdx];
            double hHigh = g_monthlyHigh[hIdx];
            double rsHigh = g_monthlyHigh[rsIdx];

            double hProm = g_swingHighProminence[j];

            // Check bar spacing
            int barsLStoH = hIdx - lsIdx;
            int barsHtoRS = rsIdx - hIdx;

            if(barsLStoH < MinBarsApart || barsHtoRS < MinBarsApart)
               continue;

            if((rsIdx - lsIdx) > MaxBarsApart)
               continue;

            // Head must be significantly higher than both shoulders
            if(hHigh <= lsHigh * HeadToShoulderRatio)
               continue;
            if(hHigh <= rsHigh * HeadToShoulderRatio)
               continue;

            // Head must have high prominence
            if(hProm < MinProminenceHead)
               continue;

            // Shoulders should be roughly at similar level
            double shoulderDiff = MathAbs(lsHigh - rsHigh) / ((lsHigh + rsHigh) / 2.0) * 100.0;
            if(shoulderDiff > ShoulderSymmetryTolerance)
               continue;

            // Find neckline valleys (support)
            int valley1Idx = lsIdx;
            double valley1Low = g_monthlyLow[lsIdx];
            for(int idx = lsIdx; idx <= hIdx; idx++)
            {
               if(g_monthlyLow[idx] < valley1Low)
               {
                  valley1Low = g_monthlyLow[idx];
                  valley1Idx = idx;
               }
            }

            int valley2Idx = hIdx;
            double valley2Low = g_monthlyLow[hIdx];
            for(int idx = hIdx; idx <= rsIdx; idx++)
            {
               if(g_monthlyLow[idx] < valley2Low)
               {
                  valley2Low = g_monthlyLow[idx];
                  valley2Idx = idx;
               }
            }

            // Neckline valleys should be roughly at similar level
            double necklineDiff = MathAbs(valley1Low - valley2Low) / ((valley1Low + valley2Low) / 2.0) * 100.0;
            if(necklineDiff > NecklineTolerance)
               continue;

            // Valid bearish H&S - draw it
            DrawBearishHS(lsIdx, hIdx, rsIdx, lsHigh, hHigh, rsHigh, valley1Idx, valley2Idx, valley1Low, valley2Low);
            patternCount++;
         }
      }
   }

   return patternCount;
}

//+------------------------------------------------------------------+
void DrawInverseHS(int lsIdx, int hIdx, int rsIdx,
                   double lsLow, double hLow, double rsLow,
                   int peak1Idx, int peak2Idx,
                   double peak1High, double peak2High)
{
   string patternID = "IHS_" + TimeToString(g_monthlyTime[lsIdx]);

   // Draw structure lines (L->H->R)
   string line1 = patternID + "_LINE1";
   ObjectCreate(0, line1, OBJ_TREND, 0,
                g_monthlyTime[lsIdx], lsLow,
                g_monthlyTime[hIdx], hLow);
   ObjectSetInteger(0, line1, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, line1, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, line1, OBJPROP_RAY_RIGHT, false);

   string line2 = patternID + "_LINE2";
   ObjectCreate(0, line2, OBJ_TREND, 0,
                g_monthlyTime[hIdx], hLow,
                g_monthlyTime[rsIdx], rsLow);
   ObjectSetInteger(0, line2, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, line2, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, line2, OBJPROP_RAY_RIGHT, false);

   // V3: Draw NECKLINE (resistance)
   datetime necklineExtend = g_monthlyTime[rsIdx] - (datetime)(365*24*60*60*2);  // Extend 2 years right
   string neckline = patternID + "_NECKLINE";
   ObjectCreate(0, neckline, OBJ_TREND, 0,
                g_monthlyTime[peak1Idx], peak1High,
                g_monthlyTime[peak2Idx], peak2High);
   ObjectSetInteger(0, neckline, OBJPROP_COLOR, NecklineColor);
   ObjectSetInteger(0, neckline, OBJPROP_WIDTH, NecklineWidth);
   ObjectSetInteger(0, neckline, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, neckline, OBJPROP_RAY_RIGHT, true);

   // Draw markers
   string m1 = patternID + "_M1";
   ObjectCreate(0, m1, OBJ_ARROW_UP, 0, g_monthlyTime[lsIdx], lsLow);
   ObjectSetInteger(0, m1, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, m1, OBJPROP_WIDTH, 3);

   string m2 = patternID + "_M2";
   ObjectCreate(0, m2, OBJ_ARROW_UP, 0, g_monthlyTime[hIdx], hLow);
   ObjectSetInteger(0, m2, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, m2, OBJPROP_WIDTH, 4);

   string m3 = patternID + "_M3";
   ObjectCreate(0, m3, OBJ_ARROW_UP, 0, g_monthlyTime[rsIdx], rsLow);
   ObjectSetInteger(0, m3, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, m3, OBJPROP_WIDTH, 3);

   // Draw label
   datetime midTime = g_monthlyTime[hIdx];
   double midPrice = hLow;

   string label = patternID + "_LABEL";
   ObjectCreate(0, label, OBJ_TEXT, 0, midTime, midPrice);
   ObjectSetString(0, label, OBJPROP_TEXT, "INVERSE H&S");
   ObjectSetInteger(0, label, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, label, OBJPROP_FONTSIZE, LabelFontSize);
   ObjectSetInteger(0, label, OBJPROP_ANCHOR, ANCHOR_TOP);
}

//+------------------------------------------------------------------+
void DrawBearishHS(int lsIdx, int hIdx, int rsIdx,
                   double lsHigh, double hHigh, double rsHigh,
                   int valley1Idx, int valley2Idx,
                   double valley1Low, double valley2Low)
{
   string patternID = "HS_" + TimeToString(g_monthlyTime[lsIdx]);

   // Draw structure lines (L->H->R)
   string line1 = patternID + "_LINE1";
   ObjectCreate(0, line1, OBJ_TREND, 0,
                g_monthlyTime[lsIdx], lsHigh,
                g_monthlyTime[hIdx], hHigh);
   ObjectSetInteger(0, line1, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, line1, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, line1, OBJPROP_RAY_RIGHT, false);

   string line2 = patternID + "_LINE2";
   ObjectCreate(0, line2, OBJ_TREND, 0,
                g_monthlyTime[hIdx], hHigh,
                g_monthlyTime[rsIdx], rsHigh);
   ObjectSetInteger(0, line2, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, line2, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, line2, OBJPROP_RAY_RIGHT, false);

   // V3: Draw NECKLINE (support)
   datetime necklineExtend = g_monthlyTime[rsIdx] - (datetime)(365*24*60*60*2);
   string neckline = patternID + "_NECKLINE";
   ObjectCreate(0, neckline, OBJ_TREND, 0,
                g_monthlyTime[valley1Idx], valley1Low,
                g_monthlyTime[valley2Idx], valley2Low);
   ObjectSetInteger(0, neckline, OBJPROP_COLOR, InvHSColor);
   ObjectSetInteger(0, neckline, OBJPROP_WIDTH, NecklineWidth);
   ObjectSetInteger(0, neckline, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, neckline, OBJPROP_RAY_RIGHT, true);

   // Draw markers
   string m1 = patternID + "_M1";
   ObjectCreate(0, m1, OBJ_ARROW_DOWN, 0, g_monthlyTime[lsIdx], lsHigh);
   ObjectSetInteger(0, m1, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, m1, OBJPROP_WIDTH, 3);

   string m2 = patternID + "_M2";
   ObjectCreate(0, m2, OBJ_ARROW_DOWN, 0, g_monthlyTime[hIdx], hHigh);
   ObjectSetInteger(0, m2, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, m2, OBJPROP_WIDTH, 4);

   string m3 = patternID + "_M3";
   ObjectCreate(0, m3, OBJ_ARROW_DOWN, 0, g_monthlyTime[rsIdx], rsHigh);
   ObjectSetInteger(0, m3, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, m3, OBJPROP_WIDTH, 3);

   // Draw label
   datetime midTime = g_monthlyTime[hIdx];
   double midPrice = hHigh;

   string label = patternID + "_LABEL";
   ObjectCreate(0, label, OBJ_TEXT, 0, midTime, midPrice);
   ObjectSetString(0, label, OBJPROP_TEXT, "BEARISH H&S");
   ObjectSetInteger(0, label, OBJPROP_COLOR, HSColor);
   ObjectSetInteger(0, label, OBJPROP_FONTSIZE, LabelFontSize);
   ObjectSetInteger(0, label, OBJPROP_ANCHOR, ANCHOR_BOTTOM);
}
//+------------------------------------------------------------------+
