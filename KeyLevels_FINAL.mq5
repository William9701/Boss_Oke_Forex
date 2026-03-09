//+------------------------------------------------------------------+
//|                                               KeyLevels_FINAL.mq5 |
//|                         Key Reversal Level Detection - FINAL     |
//|                                    Monthly Data - All Timeframes  |
//|                                                                   |
//| Algorithm based on EURUSD manual level analysis:                 |
//| - Zone height: 1.5-2% of price                                   |
//| - Min 5 touches, 55%+ reversal rate                              |
//| - Distributed across price range (top, middle, middle, bottom)   |
//| - Bonus scoring for zones near historical extremes               |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot - FINAL"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    LookbackBars = 300;          // Monthly bars to analyze
input int    NumLevels = 4;               // Number of key levels (3-4)
input int    MinTouches = 5;              // Minimum touches required
input double MinReversalRate = 55.0;      // Minimum reversal rate %
input double ExtremeBonus = 100.0;        // Bonus score for extremes
input color  Level1Color = clrRed;
input color  Level2Color = clrBlue;
input color  Level3Color = clrGreen;
input color  Level4Color = clrOrange;
input int    ZoneTransparency = 60;       // Zone transparency (0-100)
input bool   ShowLabels = true;
input bool   ShowMidLine = true;

//--- Zone structure
struct Zone
{
   double   bottom;
   double   top;
   double   mid;
   int      touches;
   int      reversals;
   double   reversal_rate;
   double   score;
   bool     near_extreme;
};

//--- Global arrays
datetime g_monthlyTime[];
double   g_monthlyHigh[];
double   g_monthlyLow[];
double   g_monthlyClose[];
Zone     g_keyLevels[];
int      g_numLevels;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== Key Levels FINAL Initialized ===");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, "KEYLEVEL_");
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

   // Clear old objects
   ObjectsDeleteAll(0, "KEYLEVEL_");

   // Load monthly data
   if(!LoadMonthlyData())
      return(rates_total);

   // Detect key levels
   DetectKeyLevels();

   // Draw levels
   DrawKeyLevels();

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
   if(CopyClose(symbol, PERIOD_MN1, 0, LookbackBars, g_monthlyClose) < LookbackBars)
      return false;

   ArraySetAsSeries(g_monthlyTime, true);
   ArraySetAsSeries(g_monthlyHigh, true);
   ArraySetAsSeries(g_monthlyLow, true);
   ArraySetAsSeries(g_monthlyClose, true);

   return true;
}

//+------------------------------------------------------------------+
void DetectKeyLevels()
{
   // Find price range
   double priceMin = g_monthlyLow[ArrayMinimum(g_monthlyLow)];
   double priceMax = g_monthlyHigh[ArrayMaximum(g_monthlyHigh)];

   // Get major highs and lows for extreme detection
   double majorHighs[];
   double majorLows[];
   ArrayResize(majorHighs, 15);
   ArrayResize(majorLows, 15);

   ArrayCopy(majorHighs, g_monthlyHigh, 0, 0, 15);
   ArrayCopy(majorLows, g_monthlyLow, 0, 0, 15);
   ArraySort(majorHighs);
   ArraySort(majorLows);

   // Test potential zones
   Zone allZones[];
   int numZones = 0;

   // Zone heights: 1.5%, 1.7%, 1.9%, 2.0%
   double zoneHeights[] = {0.015, 0.017, 0.019, 0.020};

   for(int h = 0; h < 4; h++)
   {
      double zoneHeightPct = zoneHeights[h];
      double step = priceMin * 0.002; // 0.2% steps
      double current = priceMin;

      while(current < priceMax)
      {
         double zoneBottom = current;
         double zoneTop = current * (1 + zoneHeightPct);
         double zoneMid = (zoneTop + zoneBottom) / 2;

         Zone zone;
         if(TestZone(zoneBottom, zoneTop, zone))
         {
            // Check minimum criteria
            if(zone.touches >= MinTouches && zone.reversal_rate >= MinReversalRate)
            {
               // Check if near extreme
               bool nearHigh = IsNearExtreme(zoneMid, majorHighs);
               bool nearLow = IsNearExtreme(zoneMid, majorLows);

               // Score the zone
               zone.score = zone.touches * 5 + zone.reversals * 10 + zone.reversal_rate / 10;

               // Bonus for extremes
               if(nearHigh || nearLow)
               {
                  zone.score += ExtremeBonus;
                  zone.near_extreme = true;
               }
               else
                  zone.near_extreme = false;

               // Add to candidates
               ArrayResize(allZones, numZones + 1);
               allZones[numZones] = zone;
               numZones++;
            }
         }

         current += step;
      }
   }

   Print("Found ", numZones, " candidate zones");

   if(numZones == 0)
   {
      g_numLevels = 0;
      return;
   }

   // Sort by score
   SortZonesByScore(allZones, numZones);

   // Distribute across price range
   DistributeLevels(allZones, numZones, priceMin, priceMax);
}

//+------------------------------------------------------------------+
bool TestZone(double bottom, double top, Zone &zone)
{
   zone.bottom = bottom;
   zone.top = top;
   zone.mid = (bottom + top) / 2;
   zone.touches = 0;
   zone.reversals = 0;

   int i = 0;
   while(i < LookbackBars - 1)
   {
      double barHigh = g_monthlyHigh[i];
      double barLow = g_monthlyLow[i];

      // Did price touch zone?
      if(barLow <= top && barHigh >= bottom)
      {
         zone.touches++;

         // Check for reversal
         if(i > 0 && i < LookbackBars - 3)
         {
            double prevClose = g_monthlyClose[i + 1]; // Series is reversed
            bool fromAbove = prevClose > zone.mid;

            bool reversed = false;

            if(fromAbove)
            {
               // Should bounce UP (support)
               for(int j = 1; j < MathMin(4, i); j++)
               {
                  if(g_monthlyClose[i - j] > top)
                  {
                     reversed = true;
                     break;
                  }
               }
            }
            else
            {
               // Should bounce DOWN (resistance)
               for(int j = 1; j < MathMin(4, i); j++)
               {
                  if(g_monthlyClose[i - j] < bottom)
                  {
                     reversed = true;
                     break;
                  }
               }
            }

            if(reversed)
               zone.reversals++;
         }

         i += 3; // Skip next 2 bars
      }
      else
      {
         i++;
      }
   }

   if(zone.touches > 0)
      zone.reversal_rate = (double)zone.reversals / zone.touches * 100.0;
   else
      zone.reversal_rate = 0;

   return zone.touches >= MinTouches;
}

//+------------------------------------------------------------------+
bool IsNearExtreme(double zoneMid, const double &extremes[])
{
   for(int i = 0; i < 15; i++)
   {
      double distance = MathAbs(extremes[i] - zoneMid) / zoneMid;
      if(distance < 0.02) // Within 2%
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
void SortZonesByScore(Zone &zones[], int count)
{
   for(int i = 0; i < count - 1; i++)
   {
      for(int j = i + 1; j < count; j++)
      {
         if(zones[j].score > zones[i].score)
         {
            Zone temp = zones[i];
            zones[i] = zones[j];
            zones[j] = temp;
         }
      }
   }
}

//+------------------------------------------------------------------+
void DistributeLevels(const Zone &allZones[], int numZones, double priceMin, double priceMax)
{
   ArrayResize(g_keyLevels, 0);
   g_numLevels = 0;

   double priceRange = priceMax - priceMin;
   double sectionSize = priceRange / NumLevels;

   for(int section = 0; section < NumLevels; section++)
   {
      double sectionMin = priceMin + (section * sectionSize);
      double sectionMax = priceMin + ((section + 1) * sectionSize);

      // Find best zone in this section
      double bestScore = 0;
      int bestIdx = -1;

      for(int i = 0; i < numZones; i++)
      {
         if(allZones[i].mid >= sectionMin && allZones[i].mid <= sectionMax)
         {
            if(allZones[i].score > bestScore)
            {
               bestScore = allZones[i].score;
               bestIdx = i;
            }
         }
      }

      if(bestIdx >= 0)
      {
         ArrayResize(g_keyLevels, g_numLevels + 1);
         g_keyLevels[g_numLevels] = allZones[bestIdx];
         g_numLevels++;
      }
   }

   // Sort by price (high to low)
   for(int i = 0; i < g_numLevels - 1; i++)
   {
      for(int j = i + 1; j < g_numLevels; j++)
      {
         if(g_keyLevels[j].mid > g_keyLevels[i].mid)
         {
            Zone temp = g_keyLevels[i];
            g_keyLevels[i] = g_keyLevels[j];
            g_keyLevels[j] = temp;
         }
      }
   }

   Print("Selected ", g_numLevels, " key levels");
}

//+------------------------------------------------------------------+
void DrawKeyLevels()
{
   color colors[] = {Level1Color, Level2Color, Level3Color, Level4Color};

   for(int i = 0; i < g_numLevels; i++)
   {
      Zone zone = g_keyLevels[i];
      color clr = colors[i % 4];

      // Create zone rectangle
      string rectName = "KEYLEVEL_ZONE_" + IntegerToString(i);
      ObjectDelete(0, rectName);

      if(ObjectCreate(0, rectName, OBJ_RECTANGLE, 0,
         g_monthlyTime[LookbackBars-1], zone.bottom,
         g_monthlyTime[0], zone.top))
      {
         ObjectSetInteger(0, rectName, OBJPROP_COLOR, clr);
         ObjectSetInteger(0, rectName, OBJPROP_FILL, true);
         ObjectSetInteger(0, rectName, OBJPROP_WIDTH, 1);
         ObjectSetInteger(0, rectName, OBJPROP_BACK, true);
         ObjectSetInteger(0, rectName, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, rectName, OBJPROP_HIDDEN, true);
      }

      // Mid line
      if(ShowMidLine)
      {
         string lineName = "KEYLEVEL_MID_" + IntegerToString(i);
         ObjectDelete(0, lineName);

         if(ObjectCreate(0, lineName, OBJ_HLINE, 0, 0, zone.mid))
         {
            ObjectSetInteger(0, lineName, OBJPROP_COLOR, clr);
            ObjectSetInteger(0, lineName, OBJPROP_STYLE, STYLE_DASH);
            ObjectSetInteger(0, lineName, OBJPROP_WIDTH, 2);
            ObjectSetInteger(0, lineName, OBJPROP_BACK, false);
            ObjectSetInteger(0, lineName, OBJPROP_SELECTABLE, false);
            ObjectSetInteger(0, lineName, OBJPROP_HIDDEN, true);
         }
      }

      // Label
      if(ShowLabels)
      {
         string labelName = "KEYLEVEL_LABEL_" + IntegerToString(i);
         ObjectDelete(0, labelName);

         string extremeMarker = zone.near_extreme ? "!" : "";
         string labelText = StringFormat("L%d%s: %.5f | %dT %.0f%%",
            i + 1, extremeMarker, zone.mid, zone.touches, zone.reversal_rate);

         if(ObjectCreate(0, labelName, OBJ_TEXT, 0, g_monthlyTime[5], zone.mid))
         {
            ObjectSetString(0, labelName, OBJPROP_TEXT, labelText);
            ObjectSetInteger(0, labelName, OBJPROP_COLOR, clr);
            ObjectSetInteger(0, labelName, OBJPROP_FONTSIZE, 10);
            ObjectSetString(0, labelName, OBJPROP_FONT, "Arial Bold");
            ObjectSetInteger(0, labelName, OBJPROP_BACK, false);
            ObjectSetInteger(0, labelName, OBJPROP_SELECTABLE, false);
            ObjectSetInteger(0, labelName, OBJPROP_HIDDEN, true);
         }
      }
   }

   Print("Drew ", g_numLevels, " key levels on chart");
}
//+------------------------------------------------------------------+
