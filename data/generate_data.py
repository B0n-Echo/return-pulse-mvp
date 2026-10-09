"""
Generate synthetic, realistic-shaped data for Return Pulse (Dhaga & Co.).

Everything here is FAKE. It is shaped like the data Dhaga & Co. described during discovery, so the pipeline can be tested on messy, Hinglish, real-looking input.

Run:   python3 generate_data.py
Makes: sql/01_schema.sql, sql/02_data.sql, csv/*.csv

The seed is fixed, so every teammate who runs it gets exactly the same data.
"""
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).resolve().parent
(OUT / "sql").mkdir(exist_ok=True)
(OUT / "csv").mkdir(exist_ok=True)

START = date(2024, 10, 1)      # two full years, so year-over-year trends work
END = date(2026, 9, 27)
N_CUSTOMERS = 6000
N_ORDERS = 24000               # scaled down from ~48,000/week; see README
N_REVIEWS = 6000

# --------------------------------------------------------------------------
# Vendors (about forty, mostly Tiruppur and Jaipur: from client discovery)
# --------------------------------------------------------------------------
VENDOR_NAMES = [
    "Sutradhar Textiles", "Kesari Fabrics", "Noyyal Knits", "Pink City Prints", "Amber Weaves",
    "Tirupur Cotton Co", "Rangrez Studio", "Kaveri Garments", "Hawa Mahal Hand Block", "Shree Ganesh Knitwear",
    "Bandhej House", "Neel Indigo Works", "Sanganer Prints", "Kongu Apparels", "Marudhar Crafts",
    "Velan Exports", "Chunri Collective", "Avinashi Knits", "Jharokha Designs", "Palladam Fashions",
    "Leheriya Lane", "Kangeyam Textiles", "Gulabi Threads", "Dharapuram Mills", "Bagru Block Co",
    "Udumalai Garments", "Moti Mahal Fabrics", "Perundurai Knits", "Sitapura Apparel", "Kumaran Clothing",
    "Mandawa Weaves", "Vellakoil Textiles", "Ajrakh Stories", "Karur Home & Wear", "Pratap Nagar Prints",
    "Erode Cotton House", "Johari Bazaar Garments", "Somanur Weaving", "Malviya Nagar Mills", "Kaniyur Knits",
]
VENDORS = []
for i, name in enumerate(VENDOR_NAMES, start=1):
    city = "Tiruppur" if i % 2 else "Jaipur"
    if i in (13, 27):
        city = "Surat"
    if i == 33:
        city = "Ludhiana"
    VENDORS.append({
        "vendor_id": f"V{i:02d}",
        "vendor_name": name,
        "vendor_city": city,
        "size_chart_version": random.choice(["v1", "v2", "v2", "vendor-own", "vendor-own", "unknown"]),
        "lead_time_days_note": random.choice(["10-12 days", "2 weeks approx", "ask Ramesh", "", "15 days", "7-10d"]),
    })

# Planted patterns, so the dashboard has real signals to find and results can be checked
HOT_FIT_VENDOR = "V07"      # kurtis and dresses run small, and it gets worse in the second year
HOT_COLOUR_VENDOR = "V12"   # photos do not match the real colour
HOT_QUALITY_VENDOR = "V21"  # thin fabric, poor stitching
NE_CITIES = {"Guwahati", "Agartala", "Shillong", "Imphal"}  # damaged in transit, late

# --------------------------------------------------------------------------
# Catalogue: messy colour (about ninety spellings) and free-text fabric
# --------------------------------------------------------------------------
COLOUR_VARIANTS = {
    "maroon": ["Maroon", "maroon", "MAROON", "Maroon Red", "mrn", "Wine", "wine red", "Burgundy", "burgandy", "Dark Maroon"],
    "navy": ["Navy", "navy blue", "NAVY", "Navy Blue", "nvy", "Dark Blue", "dk blue", "Midnight Blue", "Ink Blue"],
    "pink": ["Pink", "pink", "Baby Pink", "baby pink", "Rani Pink", "rani", "Light Pink", "Blush", "Peach Pink", "PINK"],
    "yellow": ["Yellow", "yellow", "Mustard", "mustard yellow", "Haldi", "haldi yellow", "Lemon", "YLW", "Ochre"],
    "green": ["Green", "green", "Bottle Green", "bottle grn", "Olive", "olive green", "Mint", "mint green", "Mehendi Green", "Sea Green"],
    "white": ["White", "white", "Off White", "off-white", "OffWhite", "Cream", "cream", "Ivory", "WHT"],
    "black": ["Black", "black", "BLACK", "Jet Black", "blk", "Charcoal Black"],
    "red": ["Red", "red", "Cherry Red", "Brick Red", "Rust", "rust", "Coral", "Tomato Red"],
    "blue": ["Blue", "blue", "Sky Blue", "sky", "Powder Blue", "Teal", "teal blue", "Turquoise", "Royal Blue", "Indigo"],
    "grey": ["Grey", "Gray", "grey melange", "Grey Melange", "Ash", "Silver Grey", "Slate"],
    "multi": ["Multi", "multicolour", "Multi Color", "multi-colour", "Printed", "printed multi", "As per image"],
}
FABRICS = [
    "100% cotton", "Cotton", "cotton", "Pure Cotton", "cotton blend", "Cotton Blend (60/40)", "soft cotton feel",
    "Rayon", "rayon", "Viscose Rayon", "rayon slub", "Polyester", "poly crepe", "Georgette", "georgette",
    "Crepe", "Chanderi (art silk)", "Modal", "Linen look", "linen blend", "Khadi cotton", "Hosiery cotton",
    "cotton lycra", "Denim", "Twill cotton", "Muslin", "mul cotton", "Cambric cotton", "",
]
CATALOGUE_PLAN = [
    # (department, subcategory, share, price_low, price_high, size_scheme)
    ("Womenswear", "Kurti", 0.20, 499, 1299, "adult"),
    ("Womenswear", "Kurta Set", 0.10, 899, 1499, "adult"),
    ("Womenswear", "Dress", 0.12, 599, 1399, "adult"),
    ("Womenswear", "Top", 0.10, 399, 899, "adult"),
    ("Womenswear", "Palazzo", 0.05, 399, 799, "adult"),
    ("Womenswear", "Co-ord Set", 0.03, 899, 1499, "adult"),
    ("Kidswear", "Frock", 0.10, 399, 999, "kids"),
    ("Kidswear", "Kids T-shirt", 0.07, 399, 699, "kids"),
    ("Kidswear", "School Shirt", 0.06, 399, 699, "kids"),
    ("Kidswear", "Kids Shorts", 0.04, 399, 599, "kids"),
    ("Kidswear", "Kids Ethnic Set", 0.03, 699, 1299, "kids"),
    ("Menswear", "Men's T-shirt", 0.05, 399, 799, "adult"),
    ("Menswear", "Men's Shirt", 0.03, 599, 1199, "adult"),
    ("Menswear", "Track Pants", 0.02, 499, 899, "adult"),
]
ADULT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
ADULT_WEIGHTS = [4, 18, 30, 26, 15, 7]
KIDS_SIZES = ["1-2Y", "2-3Y", "3-4Y", "4-5Y", "5-6Y", "6-7Y", "7-8Y", "9-10Y", "11-12Y"]
KIDS_WEIGHTS = [8, 12, 13, 13, 12, 11, 10, 11, 10]
NAME_WORDS = {
    "Kurti": ["Floral A-line Kurti", "Block Print Straight Kurti", "Anarkali Kurti", "Office Wear Kurti", "Chikankari Kurti", "Mirror Work Kurti"],
    "Kurta Set": ["Kurta Palazzo Set", "Festive Kurta Set", "Mehndi Function Kurta Set", "Sharara Set", "Dupatta Kurta Set"],
    "Dress": ["Tiered Maxi Dress", "Shirt Dress", "Wrap Dress", "Fit and Flare Dress", "Ruffle Midi Dress"],
    "Top": ["Peplum Top", "Puff Sleeve Top", "Basic Crop Top", "Tie-up Top", "Office Top"],
    "Palazzo": ["Flared Palazzo", "Printed Palazzo", "Solid Palazzo"],
    "Co-ord Set": ["Printed Co-ord Set", "Linen Look Co-ord", "Lounge Co-ord Set"],
    "Frock": ["Party Frock", "Birthday Frock", "Cotton Frock", "Tutu Frock", "Smocked Frock"],
    "Kids T-shirt": ["Graphic Tee", "Superhero Tee", "Basic Round Neck Tee"],
    "School Shirt": ["School Shirt Half Sleeve", "School Shirt Full Sleeve"],
    "Kids Shorts": ["Cotton Shorts", "Denim Shorts", "Jogger Shorts"],
    "Kids Ethnic Set": ["Kurta Pyjama Set", "Lehenga Choli", "Dhoti Kurta Set"],
    "Men's T-shirt": ["Round Neck Tee", "Polo T-shirt", "Oversized Tee"],
    "Men's Shirt": ["Casual Check Shirt", "Linen Look Shirt", "Printed Shirt"],
    "Track Pants": ["Jogger Track Pants", "Cotton Track Pants"],
}

N_SKUS = 600
PRODUCTS = []
sku_no = 1
for dept, sub, share, plo, phi, scheme in CATALOGUE_PLAN:
    for _ in range(round(N_SKUS * share)):
        colour_family = random.choice(list(COLOUR_VARIANTS))
        vendor = random.choice(VENDORS)["vendor_id"]
        launch = START - timedelta(days=60) + timedelta(days=random.randint(0, (END - START).days - 30))
        price = int(random.triangular(plo, phi, plo + (phi - plo) * 0.3) // 50 * 50 + 49)
        PRODUCTS.append({
            "sku": f"DH-{sub[:3].upper().replace(' ', '').replace(chr(39), '')}-{sku_no:05d}",
            "product_name": random.choice(NAME_WORDS[sub]),
            "department": dept,
            "subcategory": sub,
            "vendor_id": vendor,
            "colour_raw": random.choice(COLOUR_VARIANTS[colour_family]),
            "fabric_raw": random.choice(FABRICS),
            "price_inr": max(399, min(1499, price)),
            "size_scheme": scheme,
            "launch_date": launch,
        })
        sku_no += 1
# Make sure each hot vendor owns enough kurtis/dresses to show up as hotspots
for p in PRODUCTS:
    if p["subcategory"] in ("Kurti", "Dress") and random.random() < 0.18:
        p["vendor_id"] = HOT_FIT_VENDOR
    elif p["department"] == "Womenswear" and random.random() < 0.06:
        p["vendor_id"] = HOT_COLOUR_VENDOR
    elif random.random() < 0.04:
        p["vendor_id"] = HOT_QUALITY_VENDOR
PRODUCT_BY_SKU = {p["sku"]: p for p in PRODUCTS}

# --------------------------------------------------------------------------
# Customers and cities (64% tier-2/3: from client discovery)
# --------------------------------------------------------------------------
CITIES = [
    # city, state, tier, pincode prefix, weight
    ("Bengaluru", "Karnataka", 1, "560", 6), ("Mumbai", "Maharashtra", 1, "400", 6), ("Delhi", "Delhi", 1, "110", 7),
    ("Hyderabad", "Telangana", 1, "500", 6), ("Chennai", "Tamil Nadu", 1, "600", 4), ("Pune", "Maharashtra", 1, "411", 4),
    ("Kolkata", "West Bengal", 1, "700", 3),
    ("Lucknow", "Uttar Pradesh", 2, "226", 6), ("Jaipur", "Rajasthan", 2, "302", 5), ("Indore", "Madhya Pradesh", 2, "452", 5),
    ("Patna", "Bihar", 2, "800", 5), ("Bhopal", "Madhya Pradesh", 2, "462", 4), ("Nagpur", "Maharashtra", 2, "440", 3),
    ("Surat", "Gujarat", 2, "395", 3), ("Kanpur", "Uttar Pradesh", 2, "208", 4), ("Coimbatore", "Tamil Nadu", 2, "641", 3),
    ("Ludhiana", "Punjab", 2, "141", 3), ("Raipur", "Chhattisgarh", 2, "492", 3), ("Ranchi", "Jharkhand", 2, "834", 3),
    ("Guwahati", "Assam", 2, "781", 4), ("Dehradun", "Uttarakhand", 2, "248", 2),
    ("Varanasi", "Uttar Pradesh", 3, "221", 3), ("Gorakhpur", "Uttar Pradesh", 3, "273", 3), ("Siliguri", "West Bengal", 3, "734", 2),
    ("Agartala", "Tripura", 3, "799", 2), ("Shillong", "Meghalaya", 3, "793", 2), ("Imphal", "Manipur", 3, "795", 1),
    ("Muzaffarpur", "Bihar", 3, "842", 2), ("Bilaspur", "Chhattisgarh", 3, "495", 2), ("Ujjain", "Madhya Pradesh", 3, "456", 2),
    ("Hubballi", "Karnataka", 3, "580", 2), ("Bhilwara", "Rajasthan", 3, "311", 2), ("Bareilly", "Uttar Pradesh", 3, "243", 2),
]
FIRST = ["Priya", "Anjali", "Pooja", "Neha", "Sneha", "Kavya", "Ritika", "Aisha", "Fatima", "Meena", "Divya", "Shalini",
         "Ruchi", "Simran", "Nisha", "Payal", "Swati", "Komal", "Rani", "Sana", "Lakshmi", "Deepa", "Rahul", "Amit",
         "Rohit", "Vikram", "Arjun", "Imran", "Suresh", "Karan"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Khan", "Patel", "Reddy", "Nair", "Das", "Mishra", "Pandey",
        "Kumari", "Iyer", "Joshi", "Ansari", "Chauhan", "Rao", "Saikia", "Devi"]
CUSTOMERS = []
for i in range(1, N_CUSTOMERS + 1):
    city, state, tier, pin, _ = random.choices(CITIES, weights=[c[4] for c in CITIES])[0]
    female = random.random() < 0.78
    first = random.choice(FIRST[:24] if female else FIRST[22:])
    CUSTOMERS.append({
        "customer_id": f"C{i:05d}",
        "customer_name": f"{first} {random.choice(LAST)}",
        "gender": "F" if female else "M",
        "age": random.randint(18, 34) if random.random() < 0.9 else random.randint(35, 48),
        "city": city, "state": state, "city_tier": tier,
        "pincode": pin + f"{random.randint(1, 99):03d}",
        "signup_date": START - timedelta(days=random.randint(0, 900)),
    })

# --------------------------------------------------------------------------
# Orders and order items (61% COD, 26% of COD becomes RTO: from client discovery)
# --------------------------------------------------------------------------
def rand_day():
    # slightly more orders in the second year and around Diwali / wedding season
    while True:
        d = START + timedelta(days=random.randint(0, (END - START).days))
        w = 1.0 + (0.25 if d >= date(2025, 10, 1) else 0) + (0.5 if d.month in (10, 11) else 0)
        if random.random() < w / 1.75:
            return d

ORDERS, ITEMS = [], []
item_no = 1
for i in range(1, N_ORDERS + 1):
    cust = random.choice(CUSTOMERS)
    od = rand_day()
    cod = random.random() < 0.61
    n_items = random.choices([1, 2, 3], weights=[86, 12, 2])[0]
    live = [p for p in random.sample(PRODUCTS, 40) if p["launch_date"] <= od] or [random.choice(PRODUCTS)]
    lines = []
    for p in random.sample(live, min(n_items, len(live))):
        if p["size_scheme"] == "adult":
            size = random.choices(ADULT_SIZES, weights=ADULT_WEIGHTS)[0]
        else:
            size = random.choices(KIDS_SIZES, weights=KIDS_WEIGHTS)[0]
        lines.append((p, size))
    total = sum(p["price_inr"] for p, _ in lines)

    r = random.random()
    ne = cust["city"] in NE_CITIES
    if cod and r < (0.26 + (0.06 if cust["city_tier"] == 3 else 0)):
        status = "RTO"
    elif r > 0.985:
        status = "CANCELLED"
    else:
        status = "DELIVERED"
    days_to_deliver = random.randint(4, 7) + (random.randint(3, 6) if ne else 0)
    delivered = od + timedelta(days=days_to_deliver) if status == "DELIVERED" else None
    if delivered and delivered > END:
        status, delivered = "IN_TRANSIT", None
    order_id = f"O{i:06d}"
    ORDERS.append({
        "order_id": order_id, "customer_id": cust["customer_id"], "order_date": od,
        "payment_mode": "COD" if cod else random.choice(["UPI", "UPI", "UPI", "CARD", "WALLET"]),
        "order_status": status, "delivered_date": delivered,
        "courier": random.choice(["Delhivery", "Shiprocket", "Ekart"]),
        "ship_city": cust["city"], "ship_state": cust["state"], "ship_pincode": cust["pincode"],
        "city_tier": cust["city_tier"], "order_total_inr": total,
    })
    for p, size in lines:
        ITEMS.append({
            "order_item_id": f"OI{item_no:07d}", "order_id": order_id, "sku": p["sku"],
            "size": size, "quantity": 1, "unit_price_inr": p["price_inr"],
        })
        item_no += 1
ORDER_BY_ID = {o["order_id"]: o for o in ORDERS}

# --------------------------------------------------------------------------
# Return comments: Hinglish, typos, vague, mixed (from client discovery)
# --------------------------------------------------------------------------
TEXTS = {
    "too_small": [
        "size chota hai", "size M bahut tight hai, L lena padega", "bahut tight h shoulders pe", "too small, chest pe fit nahi hua",
        "fitting bahut tight hai yaar", "chhota aa gaya, size chart galat hai", "Size small aaya, mera regular M h",
        "length bhi kam hai aur tight bhi", "sleeves tight hai arms me", "waist pe nahi aaya", "ordered L but feels like S",
        "size chart pe 38 likha tha but 36 jaisa hai", "beti ke liye liya tha chhota pad gaya", "kurti bahut fit hai, breathe nahi kar pa rahi",
        "tight hai", "size se chota h", "smaller than usual size", "XL bhi tight hai kya size h ye",
    ],
    "too_large": [
        "size bada hai", "bahut loose hai", "too big, ekdum dheela", "M mangaya tha bada aaya", "length bahut zyada hai",
        "loose fitting, mere size ka nahi lagta", "bacche ke liye bahut bada hai", "size chart se bada nikla",
        "shoulders gir rahe hain itna loose", "too loose at waist", "oversized lag raha hai jabki regular fit likha tha",
    ],
    "colour_mismatch": [
        "colour alag hai photo se", "photo me maroon dikha, aaya brown", "rang bilkul alag hai", "color is different from image",
        "pink mangaya tha peach aaya", "image me bright tha real me dull hai", "colour fade sa hai photo jaisa nahi",
        "ye wala shade nahi tha website pe", "mustard bola tha ye to green yellow hai", "colour mismatch", "rang halka hai bahut",
    ],
    "quality": [
        "kapda bahut patla hai", "quality achhi nahi hai", "fabric cheap lag raha hai", "see through hai kapda",
        "stitching kharab hai, dhaage nikal rahe", "ek wash me rang chala gaya", "fabric rough hai skin pe chubhta hai",
        "quality bilkul bekar", "material not as described, ye cotton nahi lagta", "print utar raha hai", "very thin cloth",
        "pehli dhulai me shrink ho gaya",
    ],
    "damaged": [
        "phata hua aaya", "packet khula tha aur kapde pe daag hai", "hole hai sleeve pe", "stain mila delivery pe",
        "damaged piece received", "button toota hua tha", "zip kaam nahi kar rahi", "packet geela tha kapda kharab",
        "silai khuli hui thi aate hi",
    ],
    "wrong_item": [
        "galat product aaya", "maine kurti mangayi thi top aaya", "wrong size bheja, M order kiya tha XL aaya",
        "different design aaya", "wrong item received", "ye mera order nahi hai", "doosra colour bhej diya",
    ],
    "changed_mind": [
        "pasand nahi aaya", "mind change ho gaya", "ab zarurat nahi hai", "dusri jagah sasta mil gaya",
        "function cancel ho gaya", "gift tha, unko pasand nahi aaya", "dont need it anymore", "accidentally order ho gaya",
        "mummy ko pasand nahi aaya",
    ],
    "delivery_late": [
        "bahut late aaya, function nikal gaya", "delivery me 12 din lag gaye", "late delivery, mehndi ke baad aaya",
        "time pe nahi aaya to ab kya karu", "order bahut der se mila",
    ],
    "unclear": [
        "acha nahi laga", "not good", "theek nahi hai", "bekar", "no", "return", "...", "pls return", "ok", "nahi chahiye bas",
        "😞", "not as expected", "issue hai", "same as before",
    ],
}
MIXED = [  # two reasons in one comment; first reason is the main one
    ("too_small", "quality", "size chota hai aur kapda bhi patla"),
    ("colour_mismatch", "quality", "colour alag hai aur quality bhi average"),
    ("too_large", "colour_mismatch", "bada hai and colour bhi photo jaisa nahi"),
    ("quality", "too_small", "fabric achha nahi, fitting bhi tight"),
    ("damaged", "delivery_late", "late aaya aur packet bhi phata hua"),
]
DEVANAGARI = {
    "too_small": ["साइज़ छोटा है", "बहुत टाइट है"],
    "quality": ["कपड़ा बहुत पतला है"],
    "colour_mismatch": ["रंग फोटो से अलग है"],
    "unclear": ["अच्छा नहीं लगा"],
}
FILLERS_PRE = ["", "", "", "hi ", "sir ", "mam ", "pls ", "bhaiya ", "hello, "]
FILLERS_POST = ["", "", "", " pls return", " refund chahiye", " exchange nahi chahiye", " 🙏", " !!", " very disappointed", " jaldi pickup karo"]

def typo(s):
    if len(s) < 6 or random.random() > 0.25:
        return s
    i = random.randint(1, len(s) - 2)
    op = random.random()
    if op < 0.4:
        return s[:i] + s[i + 1:]
    if op < 0.8:
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + s[i] + s[i:]

# "Didn't like it" is a real reason (changed mind), not a vague one.
# Relabelled here rather than moved between lists, so every other row stays identical.
RELABEL_AS_CHANGED_MIND = {"acha nahi laga", "अच्छा नहीं लगा"}
LAST_BASE = None


def make_comment(reason):
    global LAST_BASE
    if reason in DEVANAGARI and random.random() < 0.05:
        base = random.choice(DEVANAGARI[reason])
    else:
        base = random.choice(TEXTS[reason])
    LAST_BASE = base
    text = random.choice(FILLERS_PRE) + typo(base) + random.choice(FILLERS_POST)
    r = random.random()
    if r < 0.12:
        text = text.upper()
    elif r < 0.3:
        text = text.lower()
    return text.strip()

DROPDOWN = {
    "too_small": "Size too small", "too_large": "Size too large", "colour_mismatch": "Colour different from image",
    "quality": "Quality not as expected", "damaged": "Product damaged", "wrong_item": "Wrong item received",
}

def pick_reason(item, order):
    p = PRODUCT_BY_SKU[item["sku"]]
    w = {"too_small": 24, "too_large": 13, "colour_mismatch": 11, "quality": 13, "damaged": 7,
         "wrong_item": 5, "changed_mind": 10, "delivery_late": 4, "unclear": 9}
    second_year = order["order_date"] >= date(2025, 10, 1)
    if p["vendor_id"] == HOT_FIT_VENDOR and p["subcategory"] in ("Kurti", "Dress"):
        w["too_small"] *= 3.0 if not second_year else 6.0
        if item["size"] in ("M", "L"):
            w["too_small"] *= 1.6
    if p["vendor_id"] == HOT_COLOUR_VENDOR:
        w["colour_mismatch"] *= 5
    if p["vendor_id"] == HOT_QUALITY_VENDOR:
        w["quality"] *= 4
    if order["ship_city"] in NE_CITIES:
        w["damaged"] *= 3
        w["delivery_late"] *= 4
    if p["department"] == "Kidswear":
        w["too_large"] *= 1.4
    if order["order_date"].month in (10, 11):
        w["delivery_late"] *= 1.8
    keys = list(w)
    return random.choices(keys, weights=[w[k] for k in keys])[0]

RETURNS, TRUTH = [], []
ret_no = 1
items_by_order = {}
for it in ITEMS:
    items_by_order.setdefault(it["order_id"], []).append(it)
for o in ORDERS:
    if o["order_status"] != "DELIVERED":
        continue
    its = items_by_order[o["order_id"]]
    # about 31% of delivered orders have a return (Dhaga: 31% overall)
    base = 0.31
    if any(PRODUCT_BY_SKU[i["sku"]]["vendor_id"] == HOT_FIT_VENDOR for i in its):
        base += 0.12 if o["order_date"] >= date(2025, 10, 1) else 0.05
    if any(PRODUCT_BY_SKU[i["sku"]]["vendor_id"] in (HOT_COLOUR_VENDOR, HOT_QUALITY_VENDOR) for i in its):
        base += 0.08
    if random.random() >= base:
        continue
    for it in random.sample(its, 1 if len(its) == 1 or random.random() < 0.8 else len(its)):
        reason = pick_reason(it, o)
        rdate = o["delivered_date"] + timedelta(days=random.randint(1, 7))
        if rdate > END:
            continue
        mixed = None
        if random.random() < 0.06:
            mixed = random.choice([m for m in MIXED])
            reason = mixed[0]
        # Dropdown or "Other": target about 44% "Other" overall
        no_dropdown = reason in ("changed_mind", "delivery_late", "unclear")
        use_other = no_dropdown or random.random() < 0.255 or mixed is not None
        if use_other:
            dropdown = "Other"
            if mixed:
                text = mixed[2]
            elif random.random() < 0.04:
                text = random.choice(["", " ", ".", "na", "-"])
                reason = "unclear"
            else:
                text = make_comment(reason)
                if LAST_BASE in RELABEL_AS_CHANGED_MIND:
                    reason = "changed_mind"
        else:
            dropdown = DROPDOWN[reason]
            text = ""
        rid = f"RT{ret_no:06d}"
        RETURNS.append({
            "return_id": rid, "order_id": o["order_id"], "order_item_id": it["order_item_id"], "sku": it["sku"],
            "return_date": rdate, "raised_via": random.choices(["APP", "WHATSAPP"], weights=[70, 30])[0],
            "reason_dropdown": dropdown, "other_text": text,
            "return_status": random.choices(["REFUNDED", "INSPECTED", "PICKUP_SCHEDULED"], weights=[85, 10, 5])[0]
            if rdate < END - timedelta(days=10) else "PICKUP_SCHEDULED",
        })
        TRUTH.append({"return_id": rid, "true_issue": reason,
                      "true_secondary_issue": mixed[1] if mixed else "", "is_mixed": bool(mixed)})
        ret_no += 1

# --------------------------------------------------------------------------
# Reviews (stars + free text, same voice as returns)
# --------------------------------------------------------------------------
POS = ["bahut achha hai", "perfect fit", "value for money", "colour same as photo", "kapda achha hai", "loved it",
       "beti ko bahut pasand aaya", "office ke liye perfect", "comfortable hai", "nice quality for the price", "mast hai 👍"]
REVIEWS = []
delivered_items = [(it, ORDER_BY_ID[it["order_id"]]) for it in ITEMS if ORDER_BY_ID[it["order_id"]]["order_status"] == "DELIVERED"]
for i in range(1, N_REVIEWS + 1):
    it, o = random.choice(delivered_items)
    p = PRODUCT_BY_SKU[it["sku"]]
    neg_bias = 0.35 + (0.3 if p["vendor_id"] in (HOT_FIT_VENDOR, HOT_COLOUR_VENDOR, HOT_QUALITY_VENDOR) else 0)
    if random.random() < neg_bias:
        reason = pick_reason(it, o)
        if reason in ("changed_mind", "delivery_late"):
            reason = "quality"
        rating = random.choice([1, 1, 2, 2, 3])
        text = make_comment(reason)
    else:
        reason = "positive"
        rating = random.choice([4, 4, 5, 5, 5])
        text = random.choice(POS) if random.random() < 0.85 else ""
    rd = o["delivered_date"] + timedelta(days=random.randint(2, 20))
    if rd > END:
        rd = END
    REVIEWS.append({
        "review_id": f"RV{i:06d}", "sku": it["sku"], "customer_id": o["customer_id"], "order_id": o["order_id"],
        "rating": rating, "review_text": text, "review_date": rd, "_true": reason,
    })

# --------------------------------------------------------------------------
# Write CSV + SQL
# --------------------------------------------------------------------------
TABLES = [
    ("vendors", VENDORS, ["vendor_id", "vendor_name", "vendor_city", "size_chart_version", "lead_time_days_note"]),
    ("products", PRODUCTS, ["sku", "product_name", "department", "subcategory", "vendor_id", "colour_raw", "fabric_raw",
                            "price_inr", "size_scheme", "launch_date"]),
    ("customers", CUSTOMERS, ["customer_id", "customer_name", "gender", "age", "city", "state", "city_tier", "pincode", "signup_date"]),
    ("orders", ORDERS, ["order_id", "customer_id", "order_date", "payment_mode", "order_status", "delivered_date", "courier",
                        "ship_city", "ship_state", "ship_pincode", "city_tier", "order_total_inr"]),
    ("order_items", ITEMS, ["order_item_id", "order_id", "sku", "size", "quantity", "unit_price_inr"]),
    ("returns", RETURNS, ["return_id", "order_id", "order_item_id", "sku", "return_date", "raised_via", "reason_dropdown",
                          "other_text", "return_status"]),
    ("reviews", REVIEWS, ["review_id", "sku", "customer_id", "order_id", "rating", "review_text", "review_date"]),
    ("eval_return_labels", TRUTH, ["return_id", "true_issue", "true_secondary_issue", "is_mixed"]),
]

def sql_val(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (date, datetime)):
        return f"'{v.isoformat()}'"
    return "'" + str(v).replace("'", "''") + "'"

for name, rows, cols in TABLES:
    with open(OUT / "csv" / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r[c] is None else (r[c].isoformat() if isinstance(r[c], date) else r[c]) for c in cols])

with open(OUT / "sql" / "02_data.sql", "w", encoding="utf-8") as f:
    f.write("-- Return Pulse: SYNTHETIC data. Generated by generate_data.py (seed 42).\n")
    f.write("-- Run 01_schema.sql first.\nBEGIN;\n")
    for name, rows, cols in TABLES:
        f.write(f"\n-- {name}: {len(rows)} rows\n")
        for start in range(0, len(rows), 500):
            chunk = rows[start:start + 500]
            f.write(f"INSERT INTO {name} ({', '.join(cols)}) VALUES\n")
            f.write(",\n".join("(" + ", ".join(sql_val(r[c]) for c in cols) + ")" for r in chunk))
            f.write(";\n")
    f.write("\nCOMMIT;\n")

other = sum(1 for r in RETURNS if r["reason_dropdown"] == "Other")
delivered = sum(1 for o in ORDERS if o["order_status"] == "DELIVERED")
cod = [o for o in ORDERS if o["payment_mode"] == "COD"]
print(f"vendors {len(VENDORS)}, products {len(PRODUCTS)}, customers {len(CUSTOMERS)}, orders {len(ORDERS)}, "
      f"items {len(ITEMS)}, returns {len(RETURNS)}, reviews {len(REVIEWS)}")
print(f"COD share {len(cod)/len(ORDERS):.0%} | COD RTO {sum(o['order_status']=='RTO' for o in cod)/len(cod):.0%} | "
      f"orders with a return {len({r['order_id'] for r in RETURNS})/delivered:.0%} of delivered | "
      f"'Other' {other/len(RETURNS):.0%} of returns")
print(f"Avg order value Rs {sum(o['order_total_inr'] for o in ORDERS)/len(ORDERS):.0f} | "
      f"distinct colour spellings {len({p['colour_raw'] for p in PRODUCTS})}")
