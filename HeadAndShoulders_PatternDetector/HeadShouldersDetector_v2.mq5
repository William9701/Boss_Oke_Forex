//+------------------------------------------------------------------+
//|                                    HeadShouldersDetector_v2.mq5  |
//|                                                                  |
//|  Detects Head & Shoulders and Inverse Head & Shoulders patterns |
//|  V2: Removed neckline - only structure lines L-H-R              |
//+------------------------------------------------------------------+
#property copyright "Head & Shoulders Pattern Detector V2"
#property link      ""
#property version   "2.00"
#property indicator_chart_window
#property indicator_plots 0

//--- Input Parameters
input int    LookbackBars = 240;              // Number of bars to analyze
input int    SwingOrder = 5;                  // Swing point order (5 bars each side)
input double ShoulderSimilarity = 3.5;        // Max % difference between shoulders
input double MinHeadHeight = 3.0;             // Min % head height above shoulders
input double MaxNecklineAngle = 15.0;         // Max neckline angle in degrees
input int    MinBarsApart = 3;                // Min bars between swing points
input int    MaxBarsApart = 50;               // Max bars between swing points

input color  HSColor = clrRed;                // Head & Shoulders color
input color  InvHSColor = clrBlue;            // Inverse H&S color
input int    LineWidth = 2;                   // Line width
input int    LabelFontSize = 10;              // Label font size

//--- Global arrays for monthly timeframe data
datetime g_monthlyTime[];
double   g_monthlyHigh[];
double   g_monthlyLow[];
double   g_monthlyOpen[];
double   g_monthlyClose[];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
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
   // Delete old objects
   DeleteAllObjects();

   // Load monthly data
   int monthlyBars = LoadMonthlyData();
   if(monthlyBars < 10)
   {
      Print("Not enough monthly data loaded");
      return(0);
   }

   // Detect patterns
   DetectHeadAndShoulders();
   DetectInverseHeadAndShoulders();

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Load monthly timeframe data                                      |
//+------------------------------------------------------------------+
int LoadMonthlyData()
{
   ArrayFree(g_monthlyTime);
   ArrayFree(g_monthlyHigh);
   ArrayFree(g_monthlyLow);
   ArrayFree(g_monthlyOpen);
   ArrayFree(g_monthlyClose);

   int copied = CopyTime(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyTime);
   if(copied <= 0)
   {
      Print("Failed to copy monthly time data");
      return 0;
   }

   CopyHigh(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyHigh);
   CopyLow(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyLow);
   CopyOpen(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyOpen);
   CopyClose(_Symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyClose);

   return copied;
}

//+------------------------------------------------------------------+
//| Detect Head & Shoulders patterns                                 |
//+------------------------------------------------------------------+
void DetectHeadAndShoulders()
{
   int totalBars = ArraySize(g_monthlyHigh);
   if(totalBars < SwingOrder * 2 + 3)
      return;

   // Find swing highs
   int swingHighs[];
   ArrayResize(swingHighs, 0);

   for(int i = SwingOrder; i < totalBars - SwingOrder; i++)
   {
      if(IsSwingHigh(i))
      {
         int size = ArraySize(swingHighs);
         ArrayResize(swingHighs, size + 1);
         swingHighs[size] = i;
      }
   }

   int numSwingHighs = ArraySize(swingHighs);
   if(numSwingHighs < 3)
      return;

   // Check for H&S patterns (3 consecutive swing highs)
   int patternCount = 0;
   for(int i = 0; i < numSwingHighs - 2; i++)
   {
      int lsIdx = swingHighs[i];
      int hIdx = swingHighs[i + 1];
      int rsIdx = swingHighs[i + 2];

      double lsHigh = g_monthlyHigh[lsIdx];
      double hHigh = g_monthlyHigh[hIdx];
      double rsHigh = g_monthlyHigh[rsIdx];

      // Check bar spacing
      int bars1 = hIdx - lsIdx;
      int bars2 = rsIdx - hIdx;
      if(bars1 < MinBarsApart || bars1 > MaxBarsApart ||
         bars2 < MinBarsApart || bars2 > MaxBarsApart)
         continue;

      // Head must be highest
      if(hHigh <= lsHigh || hHigh <= rsHigh)
         continue;

      // Check head height above shoulders
      double headVsLS = (hHigh - lsHigh) / lsHigh * 100.0;
      double headVsRS = (hHigh - rsHigh) / rsHigh * 100.0;
      if(headVsLS < MinHeadHeight || headVsRS < MinHeadHeight)
         continue;

      // Check shoulder similarity
      double shoulderDiff = MathAbs(lsHigh - rsHigh) / lsHigh * 100.0;
      if(shoulderDiff > ShoulderSimilarity)
         continue;

      // Find neckline points (lows between peaks)
      double neckLeft = FindLowestBetween(lsIdx, hIdx);
      double neckRight = FindLowestBetween(hIdx, rsIdx);

      if(neckLeft <= 0 || neckRight <= 0)
         continue;

      // Check neckline angle
      int neckBars = rsIdx - lsIdx;
      double neckPriceDiff = MathAbs(neckRight - neckLeft) / neckLeft * 100.0;
      double neckAngleRad = MathArctan(neckPriceDiff / neckBars);
      double neckAngleDeg = neckAngleRad * 180.0 / M_PI;

      if(neckAngleDeg > MaxNecklineAngle)
         continue;

      // Valid H&S pattern found - draw it
      string patternID = "HS_" + IntegerToString(patternCount);

      // V2: Draw only structure lines (LS -> H -> RS), NO neckline
      DrawTrendLine(g_monthlyTime[lsIdx], lsHigh, g_monthlyTime[hIdx], hHigh,
                    "HS_LINE1_" + patternID, HSColor, STYLE_SOLID);
      DrawTrendLine(g_monthlyTime[hIdx], hHigh, g_monthlyTime[rsIdx], rsHigh,
                    "HS_LINE2_" + patternID, HSColor, STYLE_SOLID);

      // Draw labels
      DrawCircleLabel(g_monthlyTime[lsIdx], lsHigh, "HS_L_" + patternID, "L", HSColor);
      DrawCircleLabel(g_monthlyTime[hIdx], hHigh, "HS_H_" + patternID, "H", HSColor);
      DrawCircleLabel(g_monthlyTime[rsIdx], rsHigh, "HS_R_" + patternID, "R", HSColor);

      // Draw pattern name
      datetime midTime = g_monthlyTime[hIdx];
      double midPrice = hHigh + (hHigh * 0.02);
      DrawLabel(midTime, midPrice, "HS_LABEL_" + patternID, "HEAD & SHOULDERS", HSColor, true);

      patternCount++;
   }
}

//+------------------------------------------------------------------+
//| Detect Inverse Head & Shoulders patterns                         |
//+------------------------------------------------------------------+
void DetectInverseHeadAndShoulders()
{
   int totalBars = ArraySize(g_monthlyLow);
   if(totalBars < SwingOrder * 2 + 3)
      return;

   // Find swing lows
   int swingLows[];
   ArrayResize(swingLows, 0);

   for(int i = SwingOrder; i < totalBars - SwingOrder; i++)
   {
      if(IsSwingLow(i))
      {
         int size = ArraySize(swingLows);
         ArrayResize(swingLows, size + 1);
         swingLows[size] = i;
      }
   }

   int numSwingLows = ArraySize(swingLows);
   if(numSwingLows < 3)
      return;

   // Check for Inverse H&S patterns (3 consecutive swing lows)
   int patternCount = 0;
   for(int i = 0; i < numSwingLows - 2; i++)
   {
      int lsIdx = swingLows[i];
      int hIdx = swingLows[i + 1];
      int rsIdx = swingLows[i + 2];

      double lsLow = g_monthlyLow[lsIdx];
      double hLow = g_monthlyLow[hIdx];
      double rsLow = g_monthlyLow[rsIdx];

      // Check bar spacing
      int bars1 = hIdx - lsIdx;
      int bars2 = rsIdx - hIdx;
      if(bars1 < MinBarsApart || bars1 > MaxBarsApart ||
         bars2 < MinBarsApart || bars2 > MaxBarsApart)
         continue;

      // Head must be lowest
      if(hLow >= lsLow || hLow >= rsLow)
         continue;

      // Check head depth below shoulders
      double headVsLS = (lsLow - hLow) / hLow * 100.0;
      double headVsRS = (rsLow - hLow) / hLow * 100.0;
      if(headVsLS < MinHeadHeight || headVsRS < MinHeadHeight)
         continue;

      // Check shoulder similarity
      double shoulderDiff = MathAbs(lsLow - rsLow) / lsLow * 100.0;
      if(shoulderDiff > ShoulderSimilarity)
         continue;

      // Find neckline points (highs between troughs)
      double neckLeft = FindHighestBetween(lsIdx, hIdx);
      double neckRight = FindHighestBetween(hIdx, rsIdx);

      if(neckLeft <= 0 || neckRight <= 0)
         continue;

      // Check neckline angle
      int neckBars = rsIdx - lsIdx;
      double neckPriceDiff = MathAbs(neckRight - neckLeft) / neckLeft * 100.0;
      double neckAngleRad = MathArctan(neckPriceDiff / neckBars);
      double neckAngleDeg = neckAngleRad * 180.0 / M_PI;

      if(neckAngleDeg > MaxNecklineAngle)
         continue;

      // Valid Inverse H&S pattern found - draw it
      string patternID = "IHS_" + IntegerToString(patternCount);

      // V2: Draw only structure lines (LS -> H -> RS), NO neckline
      DrawTrendLine(g_monthlyTime[lsIdx], lsLow, g_monthlyTime[hIdx], hLow,
                    "IHS_LINE1_" + patternID, InvHSColor, STYLE_SOLID);
      DrawTrendLine(g_monthlyTime[hIdx], hLow, g_monthlyTime[rsIdx], rsLow,
                    "IHS_LINE2_" + patternID, InvHSColor, STYLE_SOLID);

      // Draw labels
      DrawCircleLabel(g_monthlyTime[lsIdx], lsLow, "IHS_L_" + patternID, "L", InvHSColor);
      DrawCircleLabel(g_monthlyTime[hIdx], hLow, "IHS_H_" + patternID, "H", InvHSColor);
      DrawCircleLabel(g_monthlyTime[rsIdx], rsLow, "IHS_R_" + patternID, "R", InvHSColor);

      // Draw pattern name
      datetime midTime = g_monthlyTime[hIdx];
      double midPrice = hLow - (hLow * 0.02);
      DrawLabel(midTime, midPrice, "IHS_LABEL_" + patternID, "INV HEAD & SHOULDERS", InvHSColor, true);

      patternCount++;
   }
}

//+------------------------------------------------------------------+
//| Check if index is a swing high                                   |
//+------------------------------------------------------------------+
bool IsSwingHigh(int idx)
{
   double centerHigh = g_monthlyHigh[idx];

   for(int i = 1; i <= SwingOrder; i++)
   {
      if(g_monthlyHigh[idx - i] >= centerHigh || g_monthlyHigh[idx + i] >= centerHigh)
         return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Check if index is a swing low                                    |
//+------------------------------------------------------------------+
bool IsSwingLow(int idx)
{
   double centerLow = g_monthlyLow[idx];

   for(int i = 1; i <= SwingOrder; i++)
   {
      if(g_monthlyLow[idx - i] <= centerLow || g_monthlyLow[idx + i] <= centerLow)
         return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Find lowest point between two indices                            |
//+------------------------------------------------------------------+
double FindLowestBetween(int startIdx, int endIdx)
{
   double lowest = DBL_MAX;
   for(int i = startIdx + 1; i < endIdx; i++)
   {
      if(g_monthlyLow[i] < lowest)
         lowest = g_monthlyLow[i];
   }
   return (lowest == DBL_MAX) ? 0 : lowest;
}

//+------------------------------------------------------------------+
//| Find highest point between two indices                           |
//+------------------------------------------------------------------+
double FindHighestBetween(int startIdx, int endIdx)
{
   double highest = -DBL_MAX;
   for(int i = startIdx + 1; i < endIdx; i++)
   {
      if(g_monthlyHigh[i] > highest)
         highest = g_monthlyHigh[i];
   }
   return (highest == -DBL_MAX) ? 0 : highest;
}

//+------------------------------------------------------------------+
//| Draw trend line                                                   |
//+------------------------------------------------------------------+
void DrawTrendLine(datetime time1, double price1, datetime time2, double price2,
                   string name, color clr, ENUM_LINE_STYLE style)
{
   ObjectCreate(0, name, OBJ_TREND, 0, time1, price1, time2, price2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, LineWidth);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Draw circle label at point                                       |
//+------------------------------------------------------------------+
void DrawCircleLabel(datetime time, double price, string name, string text, color clr)
{
   ObjectCreate(0, name, OBJ_TEXT, 0, time, price);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, LabelFontSize + 2);
   ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Draw text label                                                   |
//+------------------------------------------------------------------+
void DrawLabel(datetime time, double price, string name, string text, color clr, bool bold)
{
   ObjectCreate(0, name, OBJ_TEXT, 0, time, price);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, LabelFontSize);
   ObjectSetString(0, name, OBJPROP_FONT, bold ? "Arial Bold" : "Arial");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_CENTER);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
}

//+------------------------------------------------------------------+
//| Delete all indicator objects                                     |
//+------------------------------------------------------------------+
void DeleteAllObjects()
{
   int total = ObjectsTotal(0);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i);
      if(StringFind(name, "HS_") == 0 || StringFind(name, "IHS_") == 0)
      {
         ObjectDelete(0, name);
      }
   }
}

//+------------------------------------------------------------------+
