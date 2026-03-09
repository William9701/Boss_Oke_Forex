import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import os

def visualize_gemini_patterns(json_path, v17_folder, output_folder):
    """
    Overlay Gemini AI pattern detections on V17 chart images
    """
    # Load Gemini analysis results
    with open(json_path, 'r') as f:
        results = json.load(f)

    # Create output folder if doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    print("\n" + "="*80)
    print("VISUALIZING GEMINI AI PATTERN DETECTIONS")
    print("="*80)

    for result in results:
        symbol = result['symbol']
        patterns_count = result['patterns']

        if patterns_count == 0:
            print(f"\n[SKIP] {symbol}: No patterns detected")
            continue

        print(f"\n[PROCESSING] {symbol}: {patterns_count} pattern(s)")

        # Load original V17 chart
        v17_image_path = os.path.join(v17_folder, f"{symbol}_v17_detection.png")
        if not os.path.exists(v17_image_path):
            print(f"  [ERROR] V17 chart not found: {v17_image_path}")
            continue

        # Create figure with the V17 chart as background
        img = Image.open(v17_image_path)
        fig, ax = plt.subplots(figsize=(16, 10))
        ax.imshow(img, aspect='auto', extent=[0, 1, 0, 1])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Add Gemini AI watermark
        ax.text(0.98, 0.98, 'AI Analysis: Gemini 2.5 Flash',
                transform=ax.transAxes,
                fontsize=12, fontweight='bold',
                color='white',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='purple', alpha=0.7),
                ha='right', va='top')

        # Get patterns from details
        patterns_found = result['details']['patterns_found']

        # Add pattern annotations
        y_position = 0.92
        for i, pattern in enumerate(patterns_found, 1):
            pattern_type = pattern['type']
            confidence = pattern['confidence']

            # Color based on pattern type
            if 'Inverse' in pattern_type or 'INVERSE' in pattern_type:
                color = 'lime'
                pattern_symbol = '▲'
            else:
                color = 'red'
                pattern_symbol = '▼'

            # Pattern header
            header_text = f"{pattern_symbol} Pattern {i}: {pattern_type} | Confidence: {confidence}%"
            ax.text(0.02, y_position, header_text,
                   transform=ax.transAxes,
                   fontsize=11, fontweight='bold',
                   color='white',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor=color, alpha=0.8),
                   ha='left', va='top')

            y_position -= 0.05

            # Left Shoulder
            ls = pattern['left_shoulder']
            ax.text(0.02, y_position,
                   f"  L.Shoulder: {ls['date']} @ {ls['price']}",
                   transform=ax.transAxes,
                   fontsize=9, color='white',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.6),
                   ha='left', va='top')

            y_position -= 0.03

            # Head
            head = pattern['head']
            ax.text(0.02, y_position,
                   f"  Head: {head['date']} @ {head['price']}",
                   transform=ax.transAxes,
                   fontsize=9, color='yellow', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.6),
                   ha='left', va='top')

            y_position -= 0.03

            # Right Shoulder
            rs = pattern['right_shoulder']
            ax.text(0.02, y_position,
                   f"  R.Shoulder: {rs['date']} @ {rs['price']}",
                   transform=ax.transAxes,
                   fontsize=9, color='white',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.6),
                   ha='left', va='top')

            y_position -= 0.03

            # Neckline
            neckline = pattern['neckline']
            ax.text(0.02, y_position,
                   f"  Neckline: {neckline['slope']} | {neckline['price_range']}",
                   transform=ax.transAxes,
                   fontsize=9, color='cyan',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.6),
                   ha='left', va='top')

            y_position -= 0.04

            # Trading Setup
            setup = pattern['trading_setup']
            ax.text(0.02, y_position,
                   f"  Entry: {setup['entry']} | Target: {setup['target']} | Stop: {setup['stop']}",
                   transform=ax.transAxes,
                   fontsize=9, color='lightgreen', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='darkgreen', alpha=0.7),
                   ha='left', va='top')

            y_position -= 0.06

        # Add chart analysis summary on right side
        chart_analysis = result['details']['chart_analysis']

        # Wrap text for better readability
        max_chars_per_line = 70
        words = chart_analysis.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(' '.join(current_line))

        # Take first 5 lines for summary
        summary_text = '\n'.join(lines[:5])
        if len(lines) > 5:
            summary_text += "..."

        ax.text(0.98, 0.50, 'AI CHART ANALYSIS:\n' + summary_text,
               transform=ax.transAxes,
               fontsize=8, color='white',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='blue', alpha=0.6),
               ha='right', va='top',
               wrap=True)

        # Save annotated image
        output_path = os.path.join(output_folder, f"{symbol}_gemini_annotated.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"  [OK] Saved: {output_path}")

    print("\n" + "="*80)
    print("GEMINI VISUALIZATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    json_path = r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\gemini_analysis_results.json"
    v17_folder = r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\v17_pairs"
    output_folder = r"C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\gemini_annotated"

    visualize_gemini_patterns(json_path, v17_folder, output_folder)
