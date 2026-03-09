//+------------------------------------------------------------------+
//|                                                    KeyLevels.mq5 |
//|                              Key Support/Resistance Levels       |
//|                                                                  |
//| Finds TOP 3 key levels from MONTHLY data                         |
//| Based on touches and rejections                                  |
//| Displays on ALL timeframes                                       |
//+------------------------------------------------------------------+
#property copyright "Boss Oke Forex Bot"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input int    NumKeyLevels = 3;          // Number of key levels to show
input int    SwingOrder = 3;            // Swing detection order
input double TolerancePct = 0.002;      // Touch tolerance (0.2%)
input color  SupportColor = clrDodgerBlue;   // Support level color
input color  ResistanceColor = clrCrimson;   // Resistance level color
input int    LineWidth = 2;             // Level line width
input ENUM_LINE_STYLE LineStyle = STYLE_SOLID; // Line style
input bool   ShowLabels = true;         // Show level labels

//--- Global variables
string levelPrefix = "KeyLevel_";
string labelPrefix = "KeyLabel_";

//--- Structure for key levels
struct KeyLevel
{
   double price;
   int touches;
   int rejections;
   int strength;
   string type;  // "support" or "resistance"
};

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== Key Levels Indicator Initialized ===");
   Print("Calculating from MONTHLY data");
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
   DeleteAllLevels();

   // Get MONTHLY data
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

   // Find key levels
   KeyLevel keyLevels[];
   if(FindTopKeyLevels(monthlyHigh, monthlyLow, monthlyClose, monthlyBars, keyLevels))
   {
      // Draw levels
      DrawKeyLevels(keyLevels);
   }
   else
   {
      Print("ERROR: Could not find key levels");
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
//| Find top key levels from monthly data                            |
//+------------------------------------------------------------------+
bool FindTopKeyLevels(const double &mHigh[], const double &mLow[],
                      const double &mClose[], int total, KeyLevel &levels[])
{
   Print("Finding key levels...");

   // Step 1: Find all pivot points
   double pivots[];
   FindAllPivots(mHigh, mLow, total, SwingOrder, pivots);

   if(ArraySize(pivots) < 5)
   {
      Print("Not enough pivots found");
      return false;
   }

   Print("Found ", ArraySize(pivots), " pivot points");

   // Step 2: Cluster similar price levels
   double clusteredLevels[];
   ClusterPriceLevels(pivots, 15, clusteredLevels);

   Print("Clustered into ", ArraySize(clusteredLevels), " potential levels");

   // Step 3: Count touches and rejections for each level
   ArrayResize(levels, ArraySize(clusteredLevels));

   for(int i = 0; i < ArraySize(clusteredLevels); i++)
   {
      levels[i].price = clusteredLevels[i];

      CountTouchesAndRejections(mHigh, mLow, mClose, total,
                                clusteredLevels[i], TolerancePct,
                                levels[i].touches, levels[i].rejections);

      levels[i].strength = (levels[i].touches * 2) + (levels[i].rejections * 3);
   }

   // Step 4: Sort by strength
   SortLevelsByStrength(levels);

   // Step 5: Keep only top N levels
   int numLevels = MathMin(NumKeyLevels, ArraySize(levels));
   ArrayResize(levels, numLevels);

   // Step 6: Classify as support or resistance
   double currentPrice = mClose[total - 1];

   for(int i = 0; i < numLevels; i++)
   {
      if(levels[i].price < currentPrice)
         levels[i].type = "support";
      else
         levels[i].type = "resistance";

      Print("Level ", i+1, ": ", DoubleToString(levels[i].price, 5),
            " (", levels[i].type, ") - Touches: ", levels[i].touches,
            " Rejections: ", levels[i].rejections,
            " Strength: ", levels[i].strength);
   }

   return true;
}

//+------------------------------------------------------------------+
//| Find all pivot highs and lows                                    |
//+------------------------------------------------------------------+
void FindAllPivots(const double &high[], const double &low[], int total,
                   int order, double &pivots[])
{
   ArrayResize(pivots, 0);

   // Find swing highs
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
         int size = ArraySize(pivots);
         ArrayResize(pivots, size + 1);
         pivots[size] = high[i];
      }
   }

   // Find swing lows
   for(int i = order; i < total - order - 1; i++)
   {
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
         int size = ArraySize(pivots);
         ArrayResize(pivots, size + 1);
         pivots[size] = low[i];
      }
   }
}

//+------------------------------------------------------------------+
//| Cluster similar price levels (simple averaging)                  |
//+------------------------------------------------------------------+
void ClusterPriceLevels(const double &prices[], int numClusters, double &levels[])
{
   int totalPrices = ArraySize(prices);

   if(totalPrices < numClusters)
      numClusters = MathMax(3, totalPrices / 2);

   // Sort prices
   double sortedPrices[];
   ArrayResize(sortedPrices, totalPrices);
   ArrayCopy(sortedPrices, prices);
   ArraySort(sortedPrices);

   // Simple clustering: divide into groups and average
   ArrayResize(levels, numClusters);

   int pricesPerCluster = totalPrices / numClusters;

   for(int i = 0; i < numClusters; i++)
   {
      int startIdx = i * pricesPerCluster;
      int endIdx = (i == numClusters - 1) ? totalPrices : (i + 1) * pricesPerCluster;

      double sum = 0;
      int count = 0;

      for(int j = startIdx; j < endIdx; j++)
      {
         sum += sortedPrices[j];
         count++;
      }

      levels[i] = (count > 0) ? sum / count : sortedPrices[startIdx];
   }
}

//+------------------------------------------------------------------+
//| Count touches and rejections at a level                          |
//+------------------------------------------------------------------+
void CountTouchesAndRejections(const double &high[], const double &low[],
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
      if(low[i] <= levelPrice + tolerance && high[i] >= levelPrice - tolerance)
      {
         touches++;

         // Check for rejection
         if(low[i] <= levelPrice && levelPrice <= high[i])
         {
            double closeDistance = MathAbs(close[i] - levelPrice);
            double candleRange = high[i] - low[i];

            if(candleRange > 0 && closeDistance > candleRange * 0.3)
            {
               rejections++;
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Sort levels by strength (bubble sort)                            |
//+------------------------------------------------------------------+
void SortLevelsByStrength(KeyLevel &levels[])
{
   int n = ArraySize(levels);

   for(int i = 0; i < n - 1; i++)
   {
      for(int j = 0; j < n - i - 1; j++)
      {
         if(levels[j].strength < levels[j + 1].strength)
         {
            // Swap
            KeyLevel temp = levels[j];
            levels[j] = levels[j + 1];
            levels[j + 1] = temp;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Draw key levels on chart                                         |
//+------------------------------------------------------------------+
void DrawKeyLevels(const KeyLevel &levels[])
{
   for(int i = 0; i < ArraySize(levels); i++)
   {
      string levelName = levelPrefix + IntegerToString(i);
      string labelName = labelPrefix + IntegerToString(i);

      double price = levels[i].price;
      color clr = (levels[i].type == "support") ? SupportColor : ResistanceColor;
      string label = (levels[i].type == "support") ? "S" : "R";
      label += IntegerToString(i + 1);

      // Draw horizontal line
      ObjectCreate(0, levelName, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, levelName, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, levelName, OBJPROP_STYLE, LineStyle);
      ObjectSetInteger(0, levelName, OBJPROP_WIDTH, LineWidth);
      ObjectSetInteger(0, levelName, OBJPROP_BACK, true);
      ObjectSetInteger(0, levelName, OBJPROP_SELECTABLE, true);
      ObjectSetInteger(0, levelName, OBJPROP_SELECTED, false);

      string desc = label + ": " + DoubleToString(price, 5) +
                   " (T:" + IntegerToString(levels[i].touches) +
                   " R:" + IntegerToString(levels[i].rejections) + ")";

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
   }

   Print("Drew ", ArraySize(levels), " key levels on chart");
}

//+------------------------------------------------------------------+
//| Delete all level objects                                         |
//+------------------------------------------------------------------+
void DeleteAllLevels()
{
   for(int i = 0; i < 20; i++)  // Max 20 levels
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
   Print("Key Levels Indicator Removed");
}
//+------------------------------------------------------------------+
