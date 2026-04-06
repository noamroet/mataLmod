"""
Application-wide constants.

FIELDS is the controlled vocabulary for program.field.
INSTITUTIONS is the seed data for the 7 v1 universities.
"""

from app.core.enums import InstitutionType

# ── Field taxonomy ────────────────────────────────────────────────────────────

FIELDS: list[str] = [
    "computer_science",        # מדעי המחשב והנדסת תוכנה
    "electrical_engineering",  # הנדסת חשמל ואלקטרוניקה
    "mechanical_engineering",  # הנדסה מכנית ותעשייתית
    "civil_engineering",       # הנדסה אזרחית וסביבתית
    "biomedical",              # הנדסה ביו-רפואית ומדעי החיים
    "mathematics",             # מתמטיקה וסטטיסטיקה
    "physics_chemistry",       # פיזיקה וכימיה
    "medicine",                # רפואה ובריאות
    "law",                     # משפטים
    "business",                # מינהל עסקים וכלכלה
    "psychology",              # פסיכולוגיה ומדעי החברה
    "education",               # חינוך והוראה
    "humanities",              # מדעי הרוח
    "arts_design",             # אמנות, עיצוב ואדריכלות
    "communication",           # תקשורת ומדיה
    "agriculture",             # חקלאות ומדעי המזון
    "other",                   # אחר / בין-תחומי
]

# ── Degree types ──────────────────────────────────────────────────────────────

DEGREE_TYPES: list[str] = ["BA", "BSc", "BEd", "BArch", "BFA", "LLB"]

# ── V1 institution seed data ──────────────────────────────────────────────────
# Keys match the PK used in the DB (institutions.id).

INSTITUTIONS: dict[str, dict] = {
    "TAU": {
        "name_he": "אוניברסיטת תל אביב",
        "name_en": "Tel Aviv University",
        "type": InstitutionType.university,
        "location": "תל אביב",
        "city": "Tel Aviv",
        "website_url": "https://www.tau.ac.il",
        "is_active": True,
    },
    "HUJI": {
        "name_he": "האוניברסיטה העברית בירושלים",
        "name_en": "Hebrew University of Jerusalem",
        "type": InstitutionType.university,
        "location": "ירושלים",
        "city": "Jerusalem",
        "website_url": "https://www.huji.ac.il",
        "is_active": True,
    },
    "TECHNION": {
        "name_he": "הטכניון — מכון טכנולוגי לישראל",
        "name_en": "Technion — Israel Institute of Technology",
        "type": InstitutionType.university,
        "location": "חיפה",
        "city": "Haifa",
        "website_url": "https://www.technion.ac.il",
        "is_active": True,
    },
    "BGU": {
        "name_he": "אוניברסיטת בן-גוריון בנגב",
        "name_en": "Ben-Gurion University of the Negev",
        "type": InstitutionType.university,
        "location": "באר שבע",
        "city": "Be'er Sheva",
        "website_url": "https://www.bgu.ac.il",
        "is_active": True,
    },
    "BIU": {
        "name_he": "אוניברסיטת בר-אילן",
        "name_en": "Bar-Ilan University",
        "type": InstitutionType.university,
        "location": "רמת גן",
        "city": "Ramat Gan",
        "website_url": "https://www.biu.ac.il",
        "is_active": True,
    },
    "HAIFA": {
        "name_he": "אוניברסיטת חיפה",
        "name_en": "University of Haifa",
        "type": InstitutionType.university,
        "location": "חיפה",
        "city": "Haifa",
        "website_url": "https://www.haifa.ac.il",
        "is_active": True,
    },
    "ARIEL": {
        "name_he": "אוניברסיטת אריאל בשומרון",
        "name_en": "Ariel University",
        "type": InstitutionType.university,
        "location": "אריאל",
        "city": "Ariel",
        "website_url": "https://www.ariel.ac.il",
        "is_active": True,
    },
}
