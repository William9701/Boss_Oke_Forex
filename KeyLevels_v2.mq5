//+------------------------------------------------------------------+
//|                                                 KeyLevels_v2.mq5 |
//|                       Key Levels - V2 (Distributed)              |
//|                                                                  |
//| V2 CHANGES:                                                      |
//| - Levels distributed across ENTIRE price range                   |
//| - Divides range into zones                                       |
//| - Finds strongest level in each zone                             |
//| - No more clustered levels                                       |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot V2"
#property link      ""
#property version   "2.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    NumKeyLevels = 3;          // Number of key levels
input double TolerancePct = 0.003;      // Touch tolerance (0.3%)
input color  SupportColor = clrDodgerBlue;   // Support level color
input color  ResistanceColor = clrCrimson;   // Resistance level color
input int    LineWidth = 2;             // Level line width
input ENUM_LINE_STYLE LineStyle = STYLE_SOLID;
input bool   ShowLabels = true;         // Show level labels

//--- Global variables
string levelPrefix = "KeyLevel_V2_";
string labelPrefix = "KeyLabel_V2_";

//--- Structure for key levels
struct KeyLevel
{
   double price;
   int touches;
   int rejections;
   int strength;
   string type;
};

//+------------------------------------------------------------------+
//| Indicator initialization                                         |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== Key Levels V2 Initialized ===");
   Print("Finding levels distributed across entire price range");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Indicator calculation                                            |
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

   DeleteAllLevels();

   // Get MONTHLY data
   Print("Fetching MONTHLY data...");

   double mHigh[], mLow[], mClose[];
   int monthlyBars = CopyHigh(_Symbol, PERIOD_MN1, 0, 120, mHigh);
   CopyLow(_Symbol, PERIOD_MN1, 0, 120, mLow);
   CopyClose(_Symbol, PERIOD_MN1, 0, 120, mClose);

   if(monthlyBars < 50)
   {
      Print("ERROR: Not enough monthly data");
      return(rates_total);
   }

   Print("Loaded ", monthlyBars, " monthly bars");

   // Find distributed key levels
   KeyLevel keyLevels[];
   if(FindDistributedKeyLevels(mHigh, mLow, mClose, monthlyBars, keyLevels))
   {
      DrawKeyLevels(keyLevels);
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Find key levels distributed across price range                   |
//+------------------------------------------------------------------+
bool FindDistributedKeyLevels(const double &mHigh[], const double &mLow[],
                               const double &mClose[], int total, KeyLevel &levels[])
{
   Print("Finding distributed key levels...");

   // Find price range
   double priceMin = mLow[ArrayMinimum(mLow, 0, total)];
   double priceMax = mHigh[ArrayMaximum(mHigh, 0, total)];
   double priceRange = priceMax - priceMin;

   Print("Price range: ", DoubleToString(priceMin, 5), " to ", DoubleToString(priceMax, 5));
   Print("Range: ", DoubleToString(priceRange, 5));

   // Create test levels (round numbers)
   double testLevels[];
   GenerateTestLevels(priceMin, priceMax, testLevels);

   Print("Testing ", ArraySize(testLevels), " potential levels...");

   // Calculate strength for each level
   int validCount = 0;
   KeyLevel allLevels[];
   ArrayResize(allLevels, ArraySize(testLevels));

   for(int i = 0; i < ArraySize(testLevels); i++)
   {
      int touches, rejections;
      CountTouchesAtLevel(mHigh, mLow, mClose, total, testLevels[i],
                         TolerancePct, touches, rejections);

      if(touches >= 2)
      {
         allLevels[validCount].price = testLevels[i];
         allLevels[validCount].touches = touches;
         allLevels[validCount].rejections = rejections;
         allLevels[validCount].strength = (touches * 2) + (rejections * 4);
         validCount++;
      }
   }

   ArrayResize(allLevels, validCount);
   Print("Found ", validCount, " levels with 2+ touches");

   if(validCount < NumKeyLevels)
   {
      Print("Not enough valid levels");
      return false;
   }

   // Divide into zones and find strongest in each zone
   ArrayResize(levels, 0);

   double zoneSize = priceRange / NumKeyLevels;

   for(int zone = 0; zone < NumKeyLevels; zone++)
   {
      double zoneMin = priceMin + (zone * zoneSize);
      double zoneMax = priceMin + ((zone + 1) * zoneSize);

      // Find strongest level in this zone
      int bestIdx = -1;
      int bestStrength = 0;

      for(int i = 0; i < validCount; i++)
      {
         if(allLevels[i].price >= zoneMin && allLevels[i].price < zoneMax)
         {
            if(allLevels[i].strength > bestStrength)
            {
               bestStrength = allLevels[i].strength;
               bestIdx = i;
            }
         }
      }

      if(bestIdx >= 0)
      {
         int size = ArraySize(levels);
         ArrayResize(levels, size + 1);
         levels[size] = allLevels[bestIdx];

         Print("Zone ", zone+1, ": ", DoubleToString(levels[size].price, 5),
               " (T:", levels[size].touches, " R:", levels[size].rejections, ")");
      }
   }

   // Classify as support or resistance
   double currentPrice = mClose[total - 1];

   for(int i = 0; i < ArraySize(levels); i++)
   {
      if(levels[i].price < currentPrice)
         levels[i].type = "support";
      else
         levels[i].type = "resistance";
   }

   return (ArraySize(levels) > 0);
}

//+------------------------------------------------------------------+
//| Generate test levels (round numbers and intervals)               |
//+------------------------------------------------------------------+
void GenerateTestLevels(double priceMin, double priceMax, double &testLevels[])
{
   ArrayResize(testLevels, 0);

   // Test different step sizes
   double steps[] = {0.001, 0.005, 0.01, 0.05};

   for(int s = 0; s < ArraySize(steps); s++)
   {
      double step = steps[s];
      double level = priceMin;

      while(level <= priceMax)
      {
         // Add level if not already exists
         bool exists = false;
         for(int i = 0; i < ArraySize(testLevels); i++)
         {
            if(MathAbs(testLevels[i] - level) < 0.00001)
            {
               exists = true;
               break;
            }
         }

         if(!exists)
         {
            int size = ArraySize(testLevels);
            ArrayResize(testLevels, size + 1);
            testLevels[size] = level;
         }

         level += step;
      }
   }

   // Sort levels
   ArraySort(testLevels);
}

//+------------------------------------------------------------------+
//| Count touches and rejections at a level                          |
//+------------------------------------------------------------------+
void CountTouchesAtLevel(const double &high[], const double &low[],
                         const double &close[], int total,
                         double levelPrice, double tolerancePct,
                         int &touches, int &rejections)
{
   touches = 0;
   rejections = 0;

   double tolerance = levelPrice * tolerancePct;

   for(int i = 0; i < total; i++)
   {
      // Check if price touched the level
      bool touchHigh = MathAbs(high[i] - levelPrice) <= tolerance;
      bool touchLow = MathAbs(low[i] - levelPrice) <= tolerance;

      if(touchHigh || touchLow)
      {
         touches++;

         // Check for rejection
         if(levelPrice >= low[i] && levelPrice <= high[i])
         {
            double closeDistance = MathAbs(close[i] - levelPrice);
            double candleRange = high[i] - low[i];

            if(candleRange > 0 && closeDistance > candleRange * 0.4)
            {
               rejections++;
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Draw key levels on chart                                         |
//+------------------------------------------------------------------+
void DrawKeyLevels(const KeyLevel &levels[])
{
   int supportCount = 1;
   int resistanceCount = 1;

   for(int i = 0; i < ArraySize(levels); i++)
   {
      string levelName = levelPrefix + IntegerToString(i);
      string labelName = labelPrefix + IntegerToString(i);

      double price = levels[i].price;
      color clr = (levels[i].type == "support") ? SupportColor : ResistanceColor;

      string label;
      if(levels[i].type == "support")
      {
         label = "S" + IntegerToString(supportCount);
         supportCount++;
      }
      else
      {
         label = "R" + IntegerToString(resistanceCount);
         resistanceCount++;
      }

      // Draw horizontal line
      ObjectCreate(0, levelName, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, levelName, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, levelName, OBJPROP_STYLE, LineStyle);
      ObjectSetInteger(0, levelName, OBJPROP_WIDTH, LineWidth);
      ObjectSetInteger(0, levelName, OBJPROP_BACK, true);
      ObjectSetInteger(0, levelName, OBJPROP_SELECTABLE, true);

      string desc = label + ": " + DoubleToString(price, 5) +
                   " | T:" + IntegerToString(levels[i].touches) +
                   " R:" + IntegerToString(levels[i].rejections);

      ObjectSetString(0, levelName, OBJPROP_TEXT, desc);

      // Draw label
      if(ShowLabels)
      {
         ObjectCreate(0, labelName, OBJ_TEXT, 0, TimeCurrent(), price);
         ObjectSetString(0, labelName, OBJPROP_TEXT, " " + desc);
         ObjectSetInteger(0, labelName, OBJPROP_COLOR, clr);
         ObjectSetInteger(0, labelName, OBJPROP_FONTSIZE, 9);
         ObjectSetString(0, labelName, OBJPROP_FONT, "Arial Bold");
         ObjectSetInteger(0, labelName, OBJPROP_ANCHOR, ANCHOR_LEFT);
         ObjectSetInteger(0, labelName, OBJPROP_SELECTABLE, false);
      }

      Print("Drew ", label, " at ", DoubleToString(price, 5));
   }
}

//+------------------------------------------------------------------+
//| Delete all level objects                                         |
//+------------------------------------------------------------------+
void DeleteAllLevels()
{
   for(int i = 0; i < 20; i++)
   {
      ObjectDelete(0, levelPrefix + IntegerToString(i));
      ObjectDelete(0, labelPrefix + IntegerToString(i));
   }
}

//+------------------------------------------------------------------+
//| Deinitialize                                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   DeleteAllLevels();
   Print("Key Levels V2 Removed");
}
//+------------------------------------------------------------------+
