"""
Generates complete professional branding suite for AgriMind:
1. High-resolution app icon artwork (512x512)
2. Branded logo with typography (800x400)
3. Android launcher icons across all mipmap density buckets (mdpi, hdpi, xhdpi, xxhdpi, xxxhdpi)
4. Adaptive launcher vector drawables (ic_launcher.xml, ic_launcher_background.xml, ic_launcher_foreground.xml)
5. In-app vector logo drawable (ic_agrimind_logo.xml)
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(WORKSPACE, "android", "app", "src", "main", "res")
DOCS_ASSETS = os.path.join(WORKSPACE, "docs", "assets")
os.makedirs(DOCS_ASSETS, exist_ok=True)

# Color Palette
FOREST_DARK = (27, 94, 32)      # #1B5E20
LEAF_GREEN = (46, 125, 50)      # #2E7D32
BRIGHT_GREEN = (76, 175, 80)    # #4CAF50
MINT_LIGHT = (200, 230, 201)    # #C8E6C9
BG_MINT = (232, 245, 233)       # #E8F5E9
ACCENT_GOLD = (255, 179, 0)     # #FFB300
TOMATO_RED = (229, 57, 53)      # #E53935
WHITE = (255, 255, 255)

def draw_agrimind_icon(size=512, is_round=False, with_bg=True):
    """Draws the AgriMind icon: vibrant leaf with tech circuit veins and tomato seed core."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = size / 512.0

    if with_bg:
        if is_round:
            draw.ellipse([0, 0, size - 1, size - 1], fill=FOREST_DARK)
            # Subtle inner ring
            draw.ellipse([12 * scale, 12 * scale, size - 13 * scale, size - 13 * scale], outline=LEAF_GREEN, width=int(4 * scale))
        else:
            # Rounded rect background
            radius = int(80 * scale)
            draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=FOREST_DARK)
            draw.rounded_rectangle([10 * scale, 10 * scale, size - 11 * scale, size - 11 * scale], radius=radius - 6, outline=LEAF_GREEN, width=int(4 * scale))

    # Center coordinates for leaf
    cx, cy = size / 2, size / 2 - 10 * scale

    # 1. Main agricultural leaf contour
    # Left leaf lobe
    left_leaf = [
        (cx, cy + 120 * scale),
        (cx - 70 * scale, cy + 90 * scale),
        (cx - 130 * scale, cy + 20 * scale),
        (cx - 140 * scale, cy - 60 * scale),
        (cx - 90 * scale, cy - 130 * scale),
        (cx, cy - 160 * scale),
    ]
    # Right leaf lobe
    right_leaf = [
        (cx, cy - 160 * scale),
        (cx + 90 * scale, cy - 130 * scale),
        (cx + 140 * scale, cy - 60 * scale),
        (cx + 130 * scale, cy + 20 * scale),
        (cx + 70 * scale, cy + 90 * scale),
        (cx, cy + 120 * scale),
    ]
    leaf_poly = left_leaf + right_leaf
    draw.polygon(leaf_poly, fill=BRIGHT_GREEN)

    # 2. Left side darker shade for 3D depth
    left_half = left_leaf + [(cx, cy - 160 * scale), (cx, cy + 120 * scale)]
    draw.polygon(left_half, fill=LEAF_GREEN)

    # 3. Central stem (vein)
    draw.line([(cx, cy - 140 * scale), (cx, cy + 130 * scale)], fill=WHITE, width=int(6 * scale))

    # 4. Tech / AI Circuit Veins (subtle nodes & angles)
    # Lateral circuit branches (Left)
    branches = [
        # (start_y, angle, length, has_node)
        (cy - 70 * scale, -35, 70 * scale),
        (cy - 20 * scale, -40, 85 * scale),
        (cy + 35 * scale, -45, 75 * scale),
        (cy + 80 * scale, -50, 50 * scale),
    ]
    for sy, ang, length in branches:
        rad = math.radians(ang)
        ex = cx + length * math.cos(rad)
        ey = sy + length * math.sin(rad)
        # Main branch line
        draw.line([(cx, sy), (ex, ey)], fill=WHITE, width=int(3.5 * scale))
        # Neural node at end
        node_r = 5.5 * scale
        draw.ellipse([ex - node_r, ey - node_r, ex + node_r, ey + node_r], fill=ACCENT_GOLD, outline=WHITE, width=int(1.5 * scale))

        # Secondary sub-branches
        sub_len = 25 * scale
        sub_rad = math.radians(ang - 25)
        sub_ex = ex + sub_len * math.cos(sub_rad)
        sub_ey = ey + sub_len * math.sin(sub_rad)
        draw.line([(ex, ey), (sub_ex, sub_ey)], fill=MINT_LIGHT, width=int(2 * scale))
        draw.ellipse([sub_ex - 3.5 * scale, sub_ey - 3.5 * scale, sub_ex + 3.5 * scale, sub_ey + 3.5 * scale], fill=WHITE)

    # Lateral circuit branches (Right)
    branches_right = [
        (cy - 70 * scale, 35, 70 * scale),
        (cy - 20 * scale, 40, 85 * scale),
        (cy + 35 * scale, 45, 75 * scale),
        (cy + 80 * scale, 50, 50 * scale),
    ]
    for sy, ang, length in branches_right:
        rad = math.radians(180 - ang)
        ex = cx - length * math.cos(rad)
        ey = sy + length * math.sin(rad)
        draw.line([(cx, sy), (ex, ey)], fill=WHITE, width=int(3.5 * scale))
        node_r = 5.5 * scale
        draw.ellipse([ex - node_r, ey - node_r, ex + node_r, ey + node_r], fill=ACCENT_GOLD, outline=WHITE, width=int(1.5 * scale))

        # Secondary sub-branches
        sub_len = 25 * scale
        sub_rad = math.radians(180 - ang + 25)
        sub_ex = ex - sub_len * math.cos(sub_rad)
        sub_ey = ey + sub_len * math.sin(sub_rad)
        draw.line([(ex, ey), (sub_ex, sub_ey)], fill=MINT_LIGHT, width=int(2 * scale))
        draw.ellipse([sub_ex - 3.5 * scale, sub_ey - 3.5 * scale, sub_ex + 3.5 * scale, sub_ey + 3.5 * scale], fill=WHITE)

    # 5. Tomato seed motif at base
    base_y = cy + 135 * scale
    draw.ellipse([cx - 24 * scale, base_y - 20 * scale, cx + 24 * scale, base_y + 20 * scale], fill=TOMATO_RED, outline=WHITE, width=int(2.5 * scale))
    # Small calyx star
    calyx_pts = [
        (cx, base_y - 25 * scale),
        (cx + 8 * scale, base_y - 18 * scale),
        (cx + 18 * scale, base_y - 22 * scale),
        (cx + 10 * scale, base_y - 14 * scale),
        (cx + 12 * scale, base_y - 6 * scale),
        (cx, base_y - 10 * scale),
        (cx - 12 * scale, base_y - 6 * scale),
        (cx - 10 * scale, base_y - 14 * scale),
        (cx - 18 * scale, base_y - 22 * scale),
        (cx - 8 * scale, base_y - 18 * scale),
    ]
    draw.polygon(calyx_pts, fill=LEAF_GREEN)

    # 6. Top apex neural node
    apex_y = cy - 160 * scale
    draw.ellipse([cx - 8 * scale, apex_y - 8 * scale, cx + 8 * scale, apex_y + 8 * scale], fill=ACCENT_GOLD, outline=WHITE, width=int(2 * scale))

    return img

def draw_branded_banner(width=800, height=360):
    """Draws a wide brand banner with logo emblem, brand name, and tagline."""
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Soft gradient background
    draw.rectangle([0, 0, width, height], fill=BG_MINT)
    # Decorative subtle accent line at top
    draw.rectangle([0, 0, width, 8], fill=FOREST_DARK)

    # Draw icon on left
    icon_size = 220
    icon_img = draw_agrimind_icon(size=icon_size, is_round=False, with_bg=True)
    img.paste(icon_img, (40, (height - icon_size) // 2), icon_img)

    # Text rendering
    tx = 290
    # AgriMind Brand Title
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 64)
        subtitle_font = ImageFont.truetype("arial.ttf", 22)
        tagline_font = ImageFont.truetype("ariali.ttf", 19)
    except IOError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()

    draw.text((tx, 90), "Agri", fill=FOREST_DARK, font=title_font)
    # Measure 'Agri' width approximately
    agri_w = draw.textlength("Agri", font=title_font) if hasattr(draw, "textlength") else 140
    draw.text((tx + agri_w, 90), "Mind", fill=BRIGHT_GREEN, font=title_font)

    # Subtitle
    draw.text((tx, 175), "AI CROP HEALTH DECISION SUPPORT", fill=LEAF_GREEN, font=subtitle_font)

    # Tagline
    draw.text((tx, 220), "Smart Insights. Healthy Crops. Prosperous Farmers.", fill=(60, 60, 60), font=tagline_font)

    # Institutional watermark
    draw.text((tx, 265), "Jammu & Kashmir Farmer Decision Support System • COM71116-21", fill=(120, 120, 120), font=tagline_font)

    return img

def generate_all_assets():
    print("Generating AgriMind Professional Branding Suite...")

    # 1. Master Icon Artworks
    master_square = draw_agrimind_icon(size=512, is_round=False, with_bg=True)
    master_square.save(os.path.join(DOCS_ASSETS, "agrimind_logo.png"))
    print(f"Saved: {os.path.join(DOCS_ASSETS, 'agrimind_logo.png')} (512x512)")

    master_round = draw_agrimind_icon(size=512, is_round=True, with_bg=True)
    master_round.save(os.path.join(DOCS_ASSETS, "agrimind_logo_round.png"))

    # 2. Master Branded Banner
    banner = draw_branded_banner(width=800, height=360)
    banner.save(os.path.join(DOCS_ASSETS, "agrimind_banner.png"))
    print(f"Saved: {os.path.join(DOCS_ASSETS, 'agrimind_banner.png')} (800x360)")

    # 3. Android Mipmap Density Buckets
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, dim in densities.items():
        dir_path = os.path.join(RES_DIR, folder)
        os.makedirs(dir_path, exist_ok=True)

        # Square Icon
        sq_icon = draw_agrimind_icon(size=dim, is_round=False, with_bg=True)
        sq_path = os.path.join(dir_path, "ic_launcher.png")
        sq_icon.save(sq_path)

        # Round Icon
        rd_icon = draw_agrimind_icon(size=dim, is_round=True, with_bg=True)
        rd_path = os.path.join(dir_path, "ic_launcher_round.png")
        rd_icon.save(rd_path)

        print(f"Saved: {folder} ({dim}x{dim}) -> ic_launcher.png & ic_launcher_round.png")

    # 4. Drawable directory and Vector Drawables
    drawable_dir = os.path.join(RES_DIR, "drawable")
    os.makedirs(drawable_dir, exist_ok=True)

    # In-App Logo Image (high res PNG in drawable)
    inapp_logo = draw_agrimind_icon(size=300, is_round=False, with_bg=True)
    inapp_logo.save(os.path.join(drawable_dir, "agrimind_logo.png"))
    print(f"Saved: {os.path.join(drawable_dir, 'agrimind_logo.png')}")

    # Vector Background for Adaptive Icon
    bg_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#1B5E20"
        android:pathData="M0,0h108v108h-108z" />
    <path
        android:strokeColor="#2E7D32"
        android:strokeWidth="1.5"
        android:pathData="M14,14h80v80h-80z" />
</vector>
"""
    with open(os.path.join(drawable_dir, "ic_launcher_background.xml"), "w", encoding="utf-8") as f:
        f.write(bg_xml)

    # Vector Foreground for Adaptive Icon
    fg_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- Main Leaf Body (Right Half) -->
    <path
        android:fillColor="#4CAF50"
        android:pathData="M54,18 C70,24 80,38 78,54 C76,68 66,80 54,86 C54,18 54,18 54,18 Z" />
    <!-- Main Leaf Body (Left Half - Shaded) -->
    <path
        android:fillColor="#2E7D32"
        android:pathData="M54,18 C38,24 28,38 30,54 C32,68 42,80 54,86 C54,18 54,18 54,18 Z" />
    <!-- Center Stem / Tech Backbone -->
    <path
        android:strokeColor="#FFFFFF"
        android:strokeWidth="2.2"
        android:strokeLineCap="round"
        android:pathData="M54,20 L54,86" />
    <!-- Lateral Circuit Veins Left -->
    <path
        android:strokeColor="#FFFFFF"
        android:strokeWidth="1.4"
        android:strokeLineCap="round"
        android:pathData="M54,36 L40,30 M54,48 L36,44 M54,60 L38,58 M54,72 L44,72" />
    <!-- Lateral Circuit Veins Right -->
    <path
        android:strokeColor="#FFFFFF"
        android:strokeWidth="1.4"
        android:strokeLineCap="round"
        android:pathData="M54,36 L68,30 M54,48 L72,44 M54,60 L70,58 M54,72 L64,72" />
    <!-- Neural Circuit Nodes -->
    <path
        android:fillColor="#FFB300"
        android:pathData="M38,30a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M34,44a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M36,58a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M73,30a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M77,44a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <path
        android:fillColor="#FFB300"
        android:pathData="M75,58a2.5,2.5 0,1 1,-5 0a2.5,2.5 0,1 1,5 0" />
    <!-- Tomato Seed Base Motif -->
    <path
        android:fillColor="#E53935"
        android:pathData="M54,82 C58,82 61,85 61,89 C61,93 54,97 54,97 C54,97 47,93 47,89 C47,85 50,82 54,82 Z" />
    <!-- Apex Node -->
    <path
        android:fillColor="#FFB300"
        android:pathData="M57,18a3,3 0,1 1,-6 0a3,3 0,1 1,6 0" />
</vector>
"""
    with open(os.path.join(drawable_dir, "ic_launcher_foreground.xml"), "w", encoding="utf-8") as f:
        f.write(fg_xml)

    # 5. Mipmap Adaptive Icon XML definitions (API 26+)
    anydpi_dir = os.path.join(RES_DIR, "mipmap-anydpi-v26")
    os.makedirs(anydpi_dir, exist_ok=True)

    adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""
    with open(os.path.join(anydpi_dir, "ic_launcher.xml"), "w", encoding="utf-8") as f:
        f.write(adaptive_xml)
    with open(os.path.join(anydpi_dir, "ic_launcher_round.xml"), "w", encoding="utf-8") as f:
        f.write(adaptive_xml)

    print("Brand assets successfully generated!")

if __name__ == "__main__":
    generate_all_assets()

