"""
scripts/create_dataset.py

Generates products.xlsx with 80 realistic kids'-clothing records.

Dataset is designed so every demo query finds at least one correct match:
  - "white dress for 7-8 girl for birthday"  → Floral Party Frock (white, 7-8, Girl)
  - "lion print dress"                        → Lion Printed Frock (lion, Dress)
  - "lion print tshirt for boy under 500"     → Lion Print Tee (399, Boy)
  - "same but under 500"                      → tests SQL price_max constraint
  - "something cozy for cold weather"         → vector: fleece/woollen/snug
  - "Babyhug jackets for 5-6 year boys"       → SQL: brand=Babyhug, age=5-6, Boy

Run:
    python scripts/create_dataset.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from app.config.settings import settings

# Columns: (category, product_name, description, price, size, colour, kids_age, gender, brand, stock)

PRODUCTS = [

    # ── DRESSES / FROCKS ──────────────────────────────────────────────────────
    # Core demo: "white birthday dress for 7-8 girl"
    ("Dress", "Floral Party Frock",
     "Girls white frilly frock with lace trim, perfect for birthday parties and festive occasions",
     899, "7-8Y", "White", "7-8", "Girl", "Babyhug", True),

    ("Dress", "Princess Ball Gown",
     "Elegant white princess gown with glitter tulle, ideal for special birthday celebrations",
     1299, "7-8Y", "White", "7-8", "Girl", "Hopscotch", True),

    ("Dress", "White Eyelet Cotton Dress",
     "Simple white eyelet cotton dress, breathable and cool for summer afternoons",
     549, "9-10Y", "White", "9-10", "Girl", "FirstCry", True),

    ("Dress", "Ivory Smocked Frock",
     "Soft ivory cotton smocked dress for toddlers, comfortable and breathable",
     749, "3-4Y", "White", "3-4", "Girl", "Babyhug", True),

    ("Dress", "Luxury Lace Gown",
     "Girls ivory white lace party gown with pearl buttons, ultra premium occasion wear",
     2499, "7-8Y", "White", "7-8", "Girl", "Hopscotch", True),

    # Core demo: "lion print dress" — has explicit lion imagery
    ("Dress", "Lion Printed Frock",
     "Girls yellow cotton frock with a bold lion face print on the front, fun animal-themed party dress",
     699, "5-6Y", "Yellow", "5-6", "Girl", "FirstCry", True),

    ("Dress", "Jungle Safari Frock",
     "Girls green dress with tiger, lion, and giraffe jungle animal prints, wild and playful",
     799, "7-8Y", "Green", "7-8", "Girl", "Babyhug", True),

    ("Dress", "Red Velvet Party Dress",
     "Deep red velvet frock with gold embroidery, perfect for festive parties and weddings",
     1199, "5-6Y", "Red", "5-6", "Girl", "Hopscotch", True),

    ("Dress", "Pink Tutu Party Frock",
     "Hot pink tutu frock with sequin bodice, designed for birthday parties and dance events",
     899, "3-4Y", "Pink", "3-4", "Girl", "Hopscotch", True),

    ("Dress", "Sequin Celebration Frock",
     "Girls fuchsia frock with all-over sequins and bow detail, made for joyful festive occasions",
     1099, "7-8Y", "Pink", "7-8", "Girl", "Hopscotch", True),

    ("Dress", "Peach Ruffle Dress",
     "Light peach tiered ruffle dress, great for casual outings and weekend wear",
     599, "5-6Y", "Peach", "5-6", "Girl", "HRX", True),

    ("Dress", "Mint Floral Wrap Dress",
     "Mint green wrap dress with floral pattern, lightweight and easy to wear",
     679, "7-8Y", "Green", "7-8", "Girl", "Babyhug", True),

    ("Dress", "Sunflower Skater Dress",
     "Bright yellow skater dress with sunflower print, fun and breezy summer wear",
     499, "3-4Y", "Yellow", "3-4", "Girl", "Babyhug", True),

    ("Dress", "Navy Pinafore Dress",
     "Classic navy blue cotton pinafore, suitable for school and casual daily wear",
     449, "5-6Y", "Blue", "5-6", "Girl", "FirstCry", True),

    ("Dress", "Gold Shimmer Dress",
     "Girls gold shimmer party dress with puff sleeves, glamorous celebration outfit",
     1199, "9-10Y", "Gold", "9-10", "Girl", "Hopscotch", False),

    # ── T-SHIRTS ──────────────────────────────────────────────────────────────
    # Core demo: "lion print tshirt for boy" and "under 500"
    ("T-Shirt", "Lion Print Tee",
     "Boys cotton tee with a big lion face print on the chest, roarsome everyday look",
     399, "5-6Y", "Yellow", "5-6", "Boy", "Babyhug", True),

    ("T-Shirt", "Wild Cat Graphic Tee",
     "Boys rust-coloured tee with a bold wild cat lion silhouette graphic print, under 500",
     449, "5-6Y", "Rust", "5-6", "Boy", "FirstCry", True),

    ("T-Shirt", "Savannah King Tee",
     "Boys golden tee featuring a majestic lion sitting on a rock, wild-themed animal print",
     599, "5-6Y", "Gold", "5-6", "Boy", "HRX", True),

    ("T-Shirt", "Animal Parade Tee",
     "Unisex white tee with a parade of animals including a lion, elephant, and giraffe",
     799, "5-6Y", "White", "5-6", "Unisex", "Babyhug", True),

    ("T-Shirt", "Jungle Safari Tee",
     "Boys tee featuring a tiger and jungle animals, great for adventure-loving kids",
     349, "3-4Y", "Orange", "3-4", "Boy", "HRX", True),

    ("T-Shirt", "Roaring Dino Tee",
     "Green dinosaur graphic tee, soft cotton, fun print for active boys",
     299, "5-6Y", "Green", "5-6", "Boy", "FirstCry", True),

    ("T-Shirt", "Bear Face Round Neck",
     "Cream round-neck tee with a large cartoon bear face, unisex and comfy",
     449, "7-8Y", "Cream", "7-8", "Unisex", "Babyhug", True),

    ("T-Shirt", "Striped Polo Tee",
     "Classic navy and white striped polo tee, neat and smart for school or outings",
     399, "9-10Y", "Blue", "9-10", "Boy", "HRX", True),

    ("T-Shirt", "Rainbow Unicorn Tee",
     "Girls pale pink tee with a glittery rainbow unicorn print, magical everyday wear",
     349, "5-6Y", "Pink", "5-6", "Girl", "Hopscotch", True),

    ("T-Shirt", "Space Rocket Tee",
     "Dark navy tee with a glowing space rocket and stars print, for young astronomers",
     449, "7-8Y", "Navy", "7-8", "Boy", "Babyhug", True),

    ("T-Shirt", "Elephant Graphic Tee",
     "White tee with a large illustrated elephant, soft fabric, great for casual days",
     299, "3-4Y", "White", "3-4", "Unisex", "FirstCry", True),

    ("T-Shirt", "Fox Print Long Sleeve Tee",
     "Boys long-sleeve tee with a clever fox print, warm enough for cool evenings",
     499, "5-6Y", "Rust", "5-6", "Boy", "Babyhug", True),

    ("T-Shirt", "Red Superhero Cape Tee",
     "Boys red tee with attached detachable cape, every young hero's favourite",
     499, "7-8Y", "Red", "7-8", "Boy", "Babyhug", False),

    ("T-Shirt", "Neon Cactus Tee",
     "Unisex neon green tee with a cactus illustration, trendy and comfortable",
     379, "9-10Y", "Green", "9-10", "Unisex", "HRX", True),

    ("T-Shirt", "Breezy Linen Tee",
     "Unisex soft linen blend tee, naturally cool and breathable for hot summer days",
     349, "9-10Y", "Beige", "9-10", "Unisex", "HRX", True),

    # ── DUNGAREES / OVERALLS ──────────────────────────────────────────────────
    ("Dungaree", "Denim Dungaree",
     "Unisex blue denim dungaree, sturdy and stylish for everyday casual wear",
     749, "7-8Y", "Blue", "7-8", "Unisex", "Babyhug", True),

    ("Dungaree", "Mini Denim Dungaree",
     "Toddler dark blue denim dungaree with star pocket patches, casual daily wear",
     479, "3-4Y", "Blue", "3-4", "Unisex", "Babyhug", True),

    ("Dungaree", "Striped Cotton Dungaree",
     "Red and white striped cotton dungaree, playful and easy to move in",
     599, "3-4Y", "Red", "3-4", "Unisex", "FirstCry", True),

    ("Dungaree", "Olive Cargo Dungaree",
     "Olive green cargo-style dungaree with large pockets, great for outdoor play",
     849, "9-10Y", "Green", "9-10", "Boy", "HRX", True),

    ("Dungaree", "Pink Floral Dungaree",
     "Soft pink dungaree with tiny floral embroidery, sweet look for little girls",
     699, "5-6Y", "Pink", "5-6", "Girl", "Hopscotch", True),

    ("Dungaree", "Light Wash Skinny Dungaree",
     "Light wash denim skinny dungaree, trendy slim fit for older kids",
     899, "9-10Y", "Blue", "9-10", "Girl", "HRX", False),

    # ── SHORTS ────────────────────────────────────────────────────────────────
    ("Shorts", "Printed Bermuda Shorts",
     "Boys cotton bermuda shorts with tropical leaf print, breezy summer essential",
     299, "5-6Y", "Green", "5-6", "Boy", "FirstCry", True),

    ("Shorts", "Solid Knit Shorts",
     "Unisex grey knit shorts with elasticated waist, perfect for sports and play",
     249, "3-4Y", "Grey", "3-4", "Unisex", "HRX", True),

    ("Shorts", "Denim Cut-Off Shorts",
     "Girls light blue denim shorts with frayed hem, casual and cool summer style",
     349, "7-8Y", "Blue", "7-8", "Girl", "Babyhug", True),

    ("Shorts", "Camo Print Shorts",
     "Boys camo-print cotton shorts, rugged look for active outdoor adventures",
     299, "9-10Y", "Khaki", "9-10", "Boy", "HRX", True),

    ("Shorts", "Floral Cycling Shorts",
     "Girls black cycling shorts with colourful floral print, stretchy and comfortable",
     349, "5-6Y", "Black", "5-6", "Girl", "FirstCry", True),

    ("Shorts", "Linen Drawstring Shorts",
     "Boys light beige linen shorts with drawstring waist, relaxed and airy for summer",
     299, "7-8Y", "Beige", "7-8", "Boy", "FirstCry", True),

    # ── TROUSERS / PANTS ──────────────────────────────────────────────────────
    ("Trousers", "Slim Fit Jogger",
     "Unisex soft cotton slim-fit jogger with ribbed cuffs, cozy and relaxed everyday wear",
     449, "7-8Y", "Grey", "7-8", "Unisex", "HRX", True),

    ("Trousers", "Pull-On Chinos",
     "Boys olive pull-on chinos with elasticated waist, smart casual look",
     549, "5-6Y", "Olive", "5-6", "Boy", "Babyhug", True),

    ("Trousers", "Girls Flared Pants",
     "Girls printed flared trousers, retro style with elastic waistband",
     499, "9-10Y", "Purple", "9-10", "Girl", "Hopscotch", True),

    ("Trousers", "Track Pants",
     "Unisex navy blue track pants with white side stripes, ideal for sports and gym",
     399, "5-6Y", "Navy", "5-6", "Unisex", "HRX", True),

    ("Trousers", "Warm Fleece Trousers",
     "Boys cozy fleece-lined trousers for cold weather, snug and warm winter essential",
     649, "7-8Y", "Black", "7-8", "Boy", "FirstCry", True),

    # ── JACKETS / OUTERWEAR ───────────────────────────────────────────────────
    # Core demo: "Babyhug jackets for 5-6 year boys"
    ("Jacket", "Babyhug Quilted Jacket",
     "Boys navy quilted jacket with hood by Babyhug, warm and windproof for cold mornings",
     1099, "5-6Y", "Navy", "5-6", "Boy", "Babyhug", True),

    ("Jacket", "Babyhug Fleece Jacket",
     "Boys soft fleece jacket by Babyhug, lightweight warmth for cool weather, age 5-6",
     849, "5-6Y", "Grey", "5-6", "Boy", "Babyhug", True),

    ("Jacket", "Puffer Jacket",
     "Girls pink quilted puffer jacket with hood, lightweight warmth for cold mornings",
     999, "5-6Y", "Pink", "5-6", "Girl", "HRX", True),

    ("Jacket", "Denim Jacket",
     "Boys classic blue denim jacket, rugged and versatile for layering",
     899, "9-10Y", "Blue", "9-10", "Boy", "Babyhug", True),

    ("Jacket", "Rainbow Windbreaker",
     "Unisex lightweight rainbow-coloured windbreaker, great for outdoor activities",
     749, "7-8Y", "Multicolour", "7-8", "Unisex", "HRX", True),

    ("Jacket", "Sherpa Fleece Jacket",
     "Girls cream sherpa fleece jacket, super soft and warm for winter months",
     1099, "9-10Y", "Cream", "9-10", "Girl", "Hopscotch", True),

    ("Jacket", "Hooded Rain Jacket",
     "Boys olive hooded rain jacket, waterproof and practical for rainy days",
     849, "5-6Y", "Olive", "5-6", "Boy", "FirstCry", True),

    # ── ETHNIC / FESTIVE WEAR ─────────────────────────────────────────────────
    ("Ethnic Wear", "Lehenga Choli Set",
     "Girls bright red lehenga choli with golden embroidery, ideal for festivals and weddings",
     1499, "5-6Y", "Red", "5-6", "Girl", "Hopscotch", True),

    ("Ethnic Wear", "Kurta Pyjama Set",
     "Boys white cotton kurta pyjama with minimal embroidery, suitable for festive occasions",
     799, "7-8Y", "White", "7-8", "Boy", "Babyhug", True),

    ("Ethnic Wear", "Indo-Western Dress",
     "Girls dusty rose Indo-Western layered dress with delicate prints, perfect for parties",
     1099, "9-10Y", "Pink", "9-10", "Girl", "Hopscotch", True),

    ("Ethnic Wear", "Sherwani Set",
     "Boys royal blue sherwani with gold buttons, great for weddings and ceremonies",
     1399, "5-6Y", "Blue", "5-6", "Boy", "FirstCry", True),

    ("Ethnic Wear", "Anarkali Frock",
     "Girls purple Anarkali-style frock with embroidered bodice, festive and elegant",
     1199, "7-8Y", "Purple", "7-8", "Girl", "Hopscotch", False),

    ("Ethnic Wear", "Unisex Festive Dhoti Set",
     "Unisex white cotton dhoti and kurta set with minimal yellow border, traditional wear",
     649, "5-6Y", "White", "5-6", "Unisex", "FirstCry", True),

    # ── SLEEPWEAR / NIGHTWEAR ─────────────────────────────────────────────────
    # Core demo: "something cozy for cold weather" → semantic query
    ("Sleepwear", "Dinosaur Pyjama Set",
     "Boys green dinosaur-print pyjama set, soft cotton, warm and comfortable for bedtime",
     449, "5-6Y", "Green", "5-6", "Boy", "FirstCry", True),

    ("Sleepwear", "Star Print Nightsuit",
     "Girls pink nightsuit with glow-in-the-dark stars, snuggly and soft for sleeping",
     399, "7-8Y", "Pink", "7-8", "Girl", "Babyhug", True),

    ("Sleepwear", "Unisex Onesie",
     "Soft fleece unisex onesie with bear ears hood, snug and warm for cold winter nights",
     599, "3-4Y", "Grey", "3-4", "Unisex", "HRX", True),

    ("Sleepwear", "Striped Pyjama Set",
     "Boys navy and white striped cotton pyjama set, breathable and light for summer nights",
     349, "9-10Y", "Navy", "9-10", "Boy", "FirstCry", True),

    # ── WINTER / SEASONAL ─────────────────────────────────────────────────────
    # Core demo: "cozy cold weather" semantic queries
    ("Winter Wear", "Woollen Sweater",
     "Girls chunky knit woollen sweater in dusty pink, cozy and warm for cold winter days",
     799, "7-8Y", "Pink", "7-8", "Girl", "Hopscotch", True),

    ("Winter Wear", "Boys Hoodie",
     "Boys grey cotton-fleece hoodie with front pocket, warm cozy layering piece for cold weather",
     549, "9-10Y", "Grey", "9-10", "Boy", "HRX", True),

    ("Winter Wear", "Thermal Inner Set",
     "Unisex white thermal inner set, super soft and snug warm base layer for cold weather",
     399, "5-6Y", "White", "5-6", "Unisex", "FirstCry", True),

    ("Winter Wear", "Cable Knit Cardigan",
     "Girls cream cable-knit cardigan with buttons, classic cozy winter layering piece",
     699, "3-4Y", "Cream", "3-4", "Girl", "Babyhug", True),

    ("Winter Wear", "Zip-Up Sweatshirt",
     "Boys navy zip-up sweatshirt with kangaroo pocket, everyday warm essential for winter",
     499, "7-8Y", "Navy", "7-8", "Boy", "HRX", True),

    # ── SWIMWEAR ──────────────────────────────────────────────────────────────
    ("Swimwear", "Shark Print Swim Trunks",
     "Boys blue swim trunks with shark and wave print, quick-dry fabric for pool days",
     399, "5-6Y", "Blue", "5-6", "Boy", "HRX", True),

    ("Swimwear", "Floral Swimsuit",
     "Girls one-piece floral swimsuit with UPF 50 protection, bright and fun for pool",
     549, "7-8Y", "Multicolour", "7-8", "Girl", "Babyhug", True),

    ("Swimwear", "Rash Guard Set",
     "Unisex rash guard and shorts set, sun protection for beach and pool",
     699, "3-4Y", "Orange", "3-4", "Unisex", "HRX", True),

    # ── CO-ORD SETS ───────────────────────────────────────────────────────────
    ("Co-ord Set", "Tie-Dye Co-ord Set",
     "Girls tie-dye top and shorts set in pastel purple, trendy and cool summer outfit",
     649, "9-10Y", "Purple", "9-10", "Girl", "Hopscotch", True),

    ("Co-ord Set", "Dino Print Co-ord Set",
     "Boys bright green dino-print shirt and shorts co-ord set, fun casual wear",
     599, "5-6Y", "Green", "5-6", "Boy", "Babyhug", True),

    ("Co-ord Set", "Sports Co-ord Set",
     "Unisex navy sports tee and track shorts set, breathable for exercise and play",
     549, "7-8Y", "Navy", "7-8", "Unisex", "HRX", True),
]


def create_products_xlsx() -> None:
    columns = [
        "category", "product_name", "description", "price",
        "size", "colour", "kids_age", "gender", "brand", "stock",
    ]

    rows = []
    for i, row in enumerate(PRODUCTS, start=1):
        rows.append({"id": i, **dict(zip(columns, row))})

    df = pd.DataFrame(rows)

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.products_xlsx
    df.to_excel(output_path, index=False)

    print(f"Created {output_path}")
    print(f"  Total products : {len(df)}")
    print(f"  Categories     : {sorted(df['category'].unique())}")
    print(f"  Genders        : {df['gender'].value_counts().to_dict()}")
    print(f"  Brands         : {sorted(df['brand'].unique())}")
    print(f"  In stock       : {df['stock'].sum()} / {len(df)}")
    print(f"  Price range    : ₹{df['price'].min()} – ₹{df['price'].max()}")
    print(f"  Age ranges     : {sorted(df['kids_age'].unique())}")
    print()
    print("Demo query coverage:")
    lion_dress = df[df['product_name'].str.contains('Lion|lion|Wild Cat|Animal Parade', regex=True) & (df['category'] == 'Dress')]
    print(f"  Lion print dresses       : {len(lion_dress)} → {lion_dress['product_name'].tolist()}")
    white_78_dress = df[(df['colour'] == 'White') & (df['kids_age'] == '7-8') & (df['category'] == 'Dress')]
    print(f"  White dresses age 7-8   : {len(white_78_dress)} → {white_78_dress['product_name'].tolist()}")
    babyhug_56_boy = df[(df['brand'] == 'Babyhug') & (df['kids_age'] == '5-6') & (df['gender'].isin(['Boy'])) & (df['category'] == 'Jacket')]
    print(f"  Babyhug jackets 5-6 boy : {len(babyhug_56_boy)} → {babyhug_56_boy['product_name'].tolist()}")
    lion_under500 = df[df['product_name'].str.contains('Lion|Wild Cat', regex=True) & (df['price'] < 500)]
    print(f"  Lion tees under ₹500    : {len(lion_under500)} → {lion_under500[['product_name','price']].to_dict('records')}")


if __name__ == "__main__":
    create_products_xlsx()
