# Gemini AI Pattern Detector - Setup Guide

## What This Does
Uses Google's Gemini Vision AI to analyze your forex chart images and detect Head & Shoulders patterns with:
- Pattern type identification (Inverse or Bearish H&S)
- Confidence scores (0-100%)
- Exact shoulder/head locations
- Neckline analysis
- Trading recommendations (entry, target, stop loss)

## Setup Instructions

### 1. Install Required Package
```bash
pip install google-generativeai pillow
```

### 2. Get Your Gemini API Key
- Go to: https://makersuite.google.com/app/apikey
- Or: https://aistudio.google.com/app/apikey
- Click "Create API Key"
- Copy your key

### 3. Configure the Script
Open `test_gemini_detector.py` and replace:
```python
API_KEY = "YOUR_GEMINI_API_KEY_HERE"
```
With your actual key:
```python
API_KEY = "AIzaSyC_your_actual_key_here"
```

### 4. Run the Detector
```bash
cd "C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector"
python test_gemini_detector.py
```

## What It Analyzes
- All your V17 chart images (EURUSD, GBPUSD, USDJPY, etc.)
- Identifies Head & Shoulders patterns using AI vision
- Provides confidence scores and trading setups
- Saves results to `gemini_analysis_results.json`

## Output Example
```json
{
  "symbol": "EURUSD",
  "patterns": 1,
  "details": {
    "patterns_found": [
      {
        "type": "Inverse H&S",
        "confidence": 85,
        "left_shoulder": {"date": "2020-05", "price": 1.0500},
        "head": {"date": "2020-08", "price": 1.0200},
        "right_shoulder": {"date": "2020-11", "price": 1.0480},
        "neckline": {"slope": "upward", "price_range": "1.0600-1.0650"},
        "quality_notes": "Excellent symmetry, clear structure",
        "trading_setup": {
          "entry": "1.0670",
          "target": "1.1200",
          "stop": "1.0450"
        }
      }
    ]
  }
}
```

## Advantages of Using Gemini AI

### ✅ Pros:
1. **Visual Pattern Recognition** - Sees charts like a human trader
2. **Context Awareness** - Understands market structure, not just rules
3. **Flexible** - Can detect pattern variations your algorithm might miss
4. **Explains Reasoning** - Tells you WHY it detected the pattern
5. **Trading Recommendations** - Provides entry/exit levels

### ⚠️ Cons:
1. **API Costs** - Each analysis costs ~$0.001-0.01 (very cheap but not free)
2. **Requires Internet** - Can't work offline
3. **Rate Limits** - Free tier: 60 requests/minute
4. **Less Precise** - Gives approximate locations vs exact bar indices

## Best Practice: Hybrid Approach

### Strategy:
1. **V17 Algorithm** - Fast, precise, free, detects patterns algorithmically
2. **Gemini AI** - Validates patterns, provides confidence scores, catches edge cases

### Workflow:
```
1. Run V17 → Detect patterns algorithmically
2. Run Gemini → Validate with AI vision
3. Keep patterns where BOTH agree (high confidence)
4. Review patterns where they disagree
5. Trade only highest-confidence setups
```

## Usage in Your Code

### Simple Analysis:
```python
from gemini_pattern_detector import GeminiPatternDetector

detector = GeminiPatternDetector("YOUR_API_KEY")
result = detector.analyze_chart(
    image_path="path/to/chart.png",
    symbol="EURUSD"
)

if result['total_patterns'] > 0:
    pattern = result['patterns_found'][0]
    confidence = pattern['confidence']

    if confidence > 80:
        print(f"High-quality pattern detected: {confidence}%")
        # Use trading setup
```

### Batch Analysis:
```python
charts = {
    "EURUSD": "v17_pairs/EURUSD_v17_detection.png",
    "GBPUSD": "v17_pairs/GBPUSD_v17_detection.png",
    # ... more pairs
}

results = detector.analyze_multiple_charts(charts)
```

## Cost Estimate
- Gemini Pro Vision: ~$0.00125 per image (under 1000 images/month)
- Analyzing 10 charts: ~$0.0125 (1.25 cents)
- Monthly cost for daily analysis: ~$4-8

## API Rate Limits
- **Free Tier**: 60 requests/minute, 1500/day
- **Paid Tier**: Higher limits

## Troubleshooting

### Error: "API Key Invalid"
- Check your API key is correct
- Ensure you enabled Gemini API in Google AI Studio

### Error: "Rate Limit Exceeded"
- Wait 60 seconds between batches
- Upgrade to paid tier if needed

### Error: "Image Too Large"
- Resize charts to < 4MB
- Use PIL to compress: `img.save('chart.png', optimize=True, quality=85)`

### JSON Parsing Error
- Gemini sometimes returns text instead of JSON
- Check `raw_response` field in result
- Add retry logic

## Next Steps
1. Install package: `pip install google-generativeai`
2. Get API key from Google AI Studio
3. Update `test_gemini_detector.py` with your key
4. Run: `python test_gemini_detector.py`
5. Review `gemini_analysis_results.json`
6. Compare with your V17 algorithmic detections

## Questions?
- Gemini API Docs: https://ai.google.dev/tutorials/python_quickstart
- Google AI Studio: https://aistudio.google.com/
