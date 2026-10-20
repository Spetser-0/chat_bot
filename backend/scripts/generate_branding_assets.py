import os
from PIL import Image, ImageDraw, ImageFont

PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public"))
os.makedirs(PUBLIC_DIR, exist_ok=True)

# SVG Content
# Modern, sleek geometric S-curve with amber spark tip and foundational knowledge node/arc
SPETSER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100%" height="100%">
  <!-- Spetser AI Brand Icon: Stylized 'S' with Wisdom Node base and Amber Spark apex -->
  <!-- Base Knowledge Node / Neural Foundation -->
  <circle cx="34" cy="74" r="7" fill="#01696D" />
  
  <!-- Flowing Stylized 'S' Body -->
  <path d="M 34 74
           C 42 74, 70 76, 70 58
           C 70 44, 30 46, 30 32
           C 30 18, 56 16, 64 24"
        fill="none"
        stroke="#01696D"
        stroke-width="12"
        stroke-linecap="round"
        stroke-linejoin="round" />
  
  <!-- Radiance Spark / Wisdom Flame Tip in Amber (#F59E0B) -->
  <path d="M 68 8
           C 68 15, 71 18, 78 18
           C 71 18, 68 21, 68 28
           C 68 21, 65 18, 58 18
           C 65 18, 68 15, 68 8 Z"
        fill="#F59E0B" />
  <circle cx="68" cy="18" r="2.5" fill="#F59E0B" />
</svg>
"""

# Write SVG files
svg_path = os.path.join(PUBLIC_DIR, "spetser-icon.svg")
with open(svg_path, "w", encoding="utf-8") as f:
    f.write(SPETSER_SVG)

favicon_svg_path = os.path.join(PUBLIC_DIR, "favicon.svg")
with open(favicon_svg_path, "w", encoding="utf-8") as f:
    f.write(SPETSER_SVG)

print(f"Generated {svg_path} and {favicon_svg_path}")

def render_spetser_icon(size: int) -> Image.Image:
    # Render at 4x for high-quality antialiasing then downscale
    supersample = 4
    canvas_size = size * supersample
    scale = canvas_size / 100.0
    
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    teal = (1, 105, 109, 255)    # #01696D
    amber = (245, 158, 11, 255)  # #F59E0B
    
    # Calculate scaled points for S-curve
    # Base node
    cx, cy, cr = 34 * scale, 74 * scale, 7 * scale
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=teal)
    
    # Smooth cubic Bezier sampling for S-curve stroke
    def cubic_bezier(p0, p1, p2, p3, t):
        omt = 1.0 - t
        return (
            omt**3 * p0[0] + 3 * omt**2 * t * p1[0] + 3 * omt * t**2 * p2[0] + t**3 * p3[0],
            omt**3 * p0[1] + 3 * omt**2 * t * p1[1] + 3 * omt * t**2 * p2[1] + t**3 * p3[1]
        )
    
    points = []
    # Segment 1: from (34, 74) via (42, 74), (70, 76) to (70, 58)
    p0 = (34 * scale, 74 * scale)
    p1 = (42 * scale, 74 * scale)
    p2 = (70 * scale, 76 * scale)
    p3 = (70 * scale, 58 * scale)
    for i in range(50):
        points.append(cubic_bezier(p0, p1, p2, p3, i / 50.0))
        
    # Segment 2: from (70, 58) via (70, 44), (30, 46) to (30, 32)
    p0 = (70 * scale, 58 * scale)
    p1 = (70 * scale, 44 * scale)
    p2 = (30 * scale, 46 * scale)
    p3 = (30 * scale, 32 * scale)
    for i in range(50):
        points.append(cubic_bezier(p0, p1, p2, p3, i / 50.0))
        
    # Segment 3: from (30, 32) via (30, 18), (56, 16) to (64 * scale, 24 * scale)
    p0 = (30 * scale, 32 * scale)
    p1 = (30 * scale, 18 * scale)
    p2 = (56 * scale, 16 * scale)
    p3 = (64 * scale, 24 * scale)
    for i in range(51):
        points.append(cubic_bezier(p0, p1, p2, p3, i / 50.0))
        
    # Draw thick stroke along points
    stroke_w = 12 * scale
    radius = stroke_w / 2.0
    for pt in points:
        draw.ellipse([pt[0] - radius, pt[1] - radius, pt[0] + radius, pt[1] + radius], fill=teal)
        
    # Draw Amber 4-point Spark at (68, 18)
    sp_cx, sp_cy = 68 * scale, 18 * scale
    sp_r_long = 10 * scale
    sp_r_short = 2.5 * scale
    
    # 4-pointed star / spark geometry
    spark_pts = [
        (sp_cx, sp_cy - sp_r_long),
        (sp_cx + sp_r_short, sp_cy - sp_r_short),
        (sp_cx + sp_r_long, sp_cy),
        (sp_cx + sp_r_short, sp_cy + sp_r_short),
        (sp_cx, sp_cy + sp_r_long),
        (sp_cx - sp_r_short, sp_cy + sp_r_short),
        (sp_cx - sp_r_long, sp_cy),
        (sp_cx - sp_r_short, sp_cy - sp_r_short)
    ]
    draw.polygon(spark_pts, fill=amber)
    draw.ellipse([sp_cx - sp_r_short, sp_cy - sp_r_short, sp_cx + sp_r_short, sp_cy + sp_r_short], fill=amber)
    
    # Resample down to target size with Lanczos filter for crisp rendering
    resampled = img.resize((size, size), Image.Resampling.LANCZOS)
    return resampled

# Generate all required PNG sizes
png_specs = [
    ("spetser-512.png", 512),
    ("spetser-192.png", 192),
    ("spetser-apple.png", 180),
    ("spetser-32.png", 32),
    ("spetser-16.png", 16),
]

for filename, sz in png_specs:
    im = render_spetser_icon(sz)
    out_path = os.path.join(PUBLIC_DIR, filename)
    im.save(out_path, "PNG")
    print(f"Generated {out_path} ({sz}x{sz})")

# Generate Favicon ICO containing 16x16 and 32x32
ico_img = render_spetser_icon(32)
ico_16 = render_spetser_icon(16)
ico_path = os.path.join(PUBLIC_DIR, "favicon.ico")
ico_img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32)])
print(f"Generated {ico_path} (ICO with 16x16 and 32x32)")

# Generate Open Graph image (1200x630)
def generate_og_image():
    width, height = 1200, 630
    og = Image.new("RGBA", (width, height), (249, 248, 244, 255)) # #F9F8F4 parchment bg
    draw = ImageDraw.Draw(og)
    
    # Render large brand icon (260x260)
    brand_icon = render_spetser_icon(260)
    icon_x = 100
    icon_y = (height - 260) // 2
    og.paste(brand_icon, (icon_x, icon_y), brand_icon)
    
    # Decorative subtle accent line
    teal = (1, 105, 109, 255)
    amber = (245, 158, 11, 255)
    draw.rectangle([400, 295, 1100, 299], fill=teal)
    draw.rectangle([400, 295, 550, 299], fill=amber)
    
    # Save OG image
    og_path = os.path.join(PUBLIC_DIR, "spetser-og.png")
    og.save(og_path, "PNG")
    print(f"Generated {og_path} (1200x630)")

generate_og_image()
