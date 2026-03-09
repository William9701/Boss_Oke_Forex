import matplotlib.pyplot as plt
import numpy as np

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# ============= BEARISH HEAD AND SHOULDERS =============
# Create price data for head and shoulders pattern
x = np.linspace(0, 10, 100)

# Define key points for bearish H&S
left_shoulder_x = 2.0
left_shoulder_y = 110
valley1_x = 2.5
valley1_y = 95
head_x = 5.0
head_y = 120
valley2_x = 7.5
valley2_y = 97
right_shoulder_x = 8.5
right_shoulder_y = 108
breakdown_x = 9.2
breakdown_y = 90

# Create smooth price curve
price = np.zeros_like(x)
for i, xi in enumerate(x):
    if xi < left_shoulder_x:
        price[i] = 100 + 10 * np.sin((xi / left_shoulder_x) * np.pi)
    elif xi < valley1_x:
        t = (xi - left_shoulder_x) / (valley1_x - left_shoulder_x)
        price[i] = left_shoulder_y + (valley1_y - left_shoulder_y) * t
    elif xi < head_x:
        t = (xi - valley1_x) / (head_x - valley1_x)
        price[i] = valley1_y + (head_y - valley1_y) * t
    elif xi < valley2_x:
        t = (xi - head_x) / (valley2_x - head_x)
        price[i] = head_y + (valley2_y - head_y) * t
    elif xi < right_shoulder_x:
        t = (xi - valley2_x) / (right_shoulder_x - valley2_x)
        price[i] = valley2_y + (right_shoulder_y - valley2_y) * t
    else:
        t = (xi - right_shoulder_x) / (10 - right_shoulder_x)
        price[i] = right_shoulder_y + (breakdown_y - right_shoulder_y) * t

# Plot price line
ax1.plot(x, price, 'b-', linewidth=2, label='Price')

# Mark key points
ax1.scatter([left_shoulder_x], [left_shoulder_y], color='red', s=300, zorder=5, marker='v')
ax1.scatter([head_x], [head_y], color='red', s=400, zorder=5, marker='v')
ax1.scatter([right_shoulder_x], [right_shoulder_y], color='red', s=300, zorder=5, marker='v')
ax1.scatter([valley1_x, valley2_x], [valley1_y, valley2_y], color='blue', s=200, zorder=5, marker='o')

# Draw structure lines (L-H-R)
ax1.plot([left_shoulder_x, head_x], [left_shoulder_y, head_y], 'r-', linewidth=3, alpha=0.6, label='Structure Lines')
ax1.plot([head_x, right_shoulder_x], [head_y, right_shoulder_y], 'r-', linewidth=3, alpha=0.6)

# Draw NECKLINE (the key feature)
neckline_extend_x = 10
ax1.plot([valley1_x, valley2_x, neckline_extend_x],
         [valley1_y, valley2_y, valley2_y],
         'g--', linewidth=4, label='NECKLINE', alpha=0.8)

# Add labels
ax1.text(left_shoulder_x, left_shoulder_y + 5, 'LEFT\nSHOULDER', ha='center', fontsize=12, fontweight='bold')
ax1.text(head_x, head_y + 5, 'HEAD', ha='center', fontsize=14, fontweight='bold', color='red')
ax1.text(right_shoulder_x, right_shoulder_y + 5, 'RIGHT\nSHOULDER', ha='center', fontsize=12, fontweight='bold')
ax1.text(valley1_x, valley1_y - 8, 'Valley 1', ha='center', fontsize=10, color='blue')
ax1.text(valley2_x, valley2_y - 8, 'Valley 2', ha='center', fontsize=10, color='blue')
ax1.text(9.5, valley2_y + 3, 'NECKLINE\n(Support)', ha='center', fontsize=11,
         fontweight='bold', color='green', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

# Add breakdown arrow
ax1.annotate('Breakdown\nConfirms Pattern', xy=(breakdown_x, breakdown_y),
             xytext=(breakdown_x - 0.5, breakdown_y - 10),
             arrowprops=dict(arrowstyle='->', color='red', lw=3),
             fontsize=11, fontweight='bold', color='red')

ax1.set_title('BEARISH HEAD AND SHOULDERS PATTERN\nNeckline = Support line connecting the two valleys',
              fontsize=14, fontweight='bold')
ax1.set_ylabel('Price', fontsize=12)
ax1.set_ylim(80, 130)
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=11)
ax1.set_xlim(0, 10)

# ============= INVERSE (BULLISH) HEAD AND SHOULDERS =============
# Create price data for inverse pattern
price2 = np.zeros_like(x)
left_shoulder_y2 = 90
peak1_y2 = 105
head_y2 = 80
peak2_y2 = 103
right_shoulder_y2 = 92
breakout_y2 = 110

for i, xi in enumerate(x):
    if xi < left_shoulder_x:
        price2[i] = 100 - 10 * np.sin((xi / left_shoulder_x) * np.pi)
    elif xi < valley1_x:
        t = (xi - left_shoulder_x) / (valley1_x - left_shoulder_x)
        price2[i] = left_shoulder_y2 + (peak1_y2 - left_shoulder_y2) * t
    elif xi < head_x:
        t = (xi - valley1_x) / (head_x - valley1_x)
        price2[i] = peak1_y2 + (head_y2 - peak1_y2) * t
    elif xi < valley2_x:
        t = (xi - head_x) / (valley2_x - head_x)
        price2[i] = head_y2 + (peak2_y2 - head_y2) * t
    elif xi < right_shoulder_x:
        t = (xi - valley2_x) / (right_shoulder_x - valley2_x)
        price2[i] = peak2_y2 + (right_shoulder_y2 - peak2_y2) * t
    else:
        t = (xi - right_shoulder_x) / (10 - right_shoulder_x)
        price2[i] = right_shoulder_y2 + (breakout_y2 - right_shoulder_y2) * t

# Plot price line
ax2.plot(x, price2, 'b-', linewidth=2, label='Price')

# Mark key points
ax2.scatter([left_shoulder_x], [left_shoulder_y2], color='lime', s=300, zorder=5, marker='^')
ax2.scatter([head_x], [head_y2], color='lime', s=400, zorder=5, marker='^')
ax2.scatter([right_shoulder_x], [right_shoulder_y2], color='lime', s=300, zorder=5, marker='^')
ax2.scatter([valley1_x, valley2_x], [peak1_y2, peak2_y2], color='red', s=200, zorder=5, marker='o')

# Draw structure lines (L-H-R)
ax2.plot([left_shoulder_x, head_x], [left_shoulder_y2, head_y2], 'g-', linewidth=3, alpha=0.6, label='Structure Lines')
ax2.plot([head_x, right_shoulder_x], [head_y2, right_shoulder_y2], 'g-', linewidth=3, alpha=0.6)

# Draw NECKLINE (resistance)
ax2.plot([valley1_x, valley2_x, neckline_extend_x],
         [peak1_y2, peak2_y2, peak2_y2],
         'r--', linewidth=4, label='NECKLINE', alpha=0.8)

# Add labels
ax2.text(left_shoulder_x, left_shoulder_y2 - 5, 'LEFT\nSHOULDER', ha='center', fontsize=12, fontweight='bold')
ax2.text(head_x, head_y2 - 5, 'HEAD', ha='center', fontsize=14, fontweight='bold', color='green')
ax2.text(right_shoulder_x, right_shoulder_y2 - 5, 'RIGHT\nSHOULDER', ha='center', fontsize=12, fontweight='bold')
ax2.text(valley1_x, peak1_y2 + 8, 'Peak 1', ha='center', fontsize=10, color='red')
ax2.text(valley2_x, peak2_y2 + 8, 'Peak 2', ha='center', fontsize=10, color='red')
ax2.text(9.5, peak2_y2 - 3, 'NECKLINE\n(Resistance)', ha='center', fontsize=11,
         fontweight='bold', color='red', bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))

# Add breakout arrow
ax2.annotate('Breakout\nConfirms Pattern', xy=(breakdown_x, breakout_y2),
             xytext=(breakdown_x - 0.5, breakout_y2 + 10),
             arrowprops=dict(arrowstyle='->', color='green', lw=3),
             fontsize=11, fontweight='bold', color='green')

ax2.set_title('INVERSE (BULLISH) HEAD AND SHOULDERS PATTERN\nNeckline = Resistance line connecting the two peaks',
              fontsize=14, fontweight='bold')
ax2.set_xlabel('Time', fontsize=12)
ax2.set_ylabel('Price', fontsize=12)
ax2.set_ylim(70, 120)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper left', fontsize=11)
ax2.set_xlim(0, 10)

plt.tight_layout()
plt.savefig(r'C:\Users\ASUS\Desktop\Boss_Oke_Forex\HeadAndShoulders_PatternDetector\head_shoulders_neckline_diagram.png',
            dpi=150, bbox_inches='tight')
print("Diagram saved to: C:\\Users\\ASUS\\Desktop\\Boss_Oke_Forex\\HeadAndShoulders_PatternDetector\\head_shoulders_neckline_diagram.png")
plt.close()
