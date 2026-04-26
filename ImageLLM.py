import os
import cv2
from google import genai
from google.genai import types
from pydantic import BaseModel  # Used for structured output
from dotenv import load_dotenv # For loading API keys from .env
from PIL import Image

# --- CONFIGURATION ---
MODEL_ID = "gemma-4-26b-a4b-it"

load_dotenv()
API_KEY = os.getenv("GEMMA_KEY")

client = genai.Client(api_key=API_KEY)

if not API_KEY:
    raise ValueError("GEMMA_KEY not found in .env file")


# 1. Define the Structured Response Format
class WasteResponse(BaseModel):
    bin: str  # organics, recycling, trash, rejected, accidental
    processing_required: bool
    sass: str  # The grumpy personality response


def take_photo(filename="current_item.jpg"):
    print("Snapping photo...")
    cap = cv2.VideoCapture(0)
    for _ in range(60): cap.read()  # Warm up
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
        print("Photo saved!\n")
    else:
        print("Failed to grab frame.")
    cap.release()
    print("after release")
    return filename


def judge_item(image_path):
    # Upload the image
    print("start upload")
    img = Image.open(image_path)
    print("starting judge")
    # 2. System Instructions with Toronto 2026 Rules integration
    persona = (
        "You are a grumpy environment-obsessed Smart Trashcan operating in Toronto (April 2026). "
        "Analyze the image and categorize the item strictly based on the following official Toronto waste categories:\n\n"

        "=== [ORGANICS] (Green Bin) ===\n"
        "- FOOD WASTE: All food scraps, fruit, veg, meat, bones, fish, dairy, bread, pasta, coffee grounds, paper tea bags.\n"
        "- SOILED PAPER: Food-soiled pizza boxes, facial tissues (Kleenex), paper towels, paper napkins, unlined paper plates.\n"
        "- HYGIENE & MEDICAL: Disposable diapers (baby and adult), incontinence pads, sanitary napkins, menstrual pads, tampons.\n"
        "- PET WASTE: Pet waste, dog/cat poop, organic/clay/wood kitty litter, animal bedding.\n"
        "- GREASE: Small amounts of cooking oil, fats, butter, and grease.\n\n"

        "=== [RECYCLING] (Blue Bin - Circular Materials) ===\n"
        "*(Note: Items MUST be empty and free from food residue. If soiled, set processing_required: true)*\n"
        "- PLASTICS: Plastic bottles, jugs, tubs, clear clamshells, empty pill/shampoo bottles, plastic cups.\n"
        "- FLEXIBLE PLASTICS & BAGS: Plastic grocery bags, milk bags, Ziploc bags, bubble wrap, chip bags, snack bags, pouches.\n"
        "- PAPER/CARDBOARD: Clean boxes, shredded paper (in clear bag), magazines, empty paper coffee/drink cups.\n"
        "- METAL: Aluminum pop cans, food/tin cans, empty aerosol cans, aluminum foil and trays (balled up).\n"
        "- GLASS: Clear and colored glass bottles and jars (empty, lids off).\n"
        "- CARTONS: Milk, juice, soup cartons, Tetra Paks.\n"
        "- FOAM/STYROFOAM: Clean foam packaging, meat trays (film removed), packing peanuts, Styrofoam cups/plates.\n\n"

        "=== [TRASH] (Garbage Bin) ===\n"
        "- COMPOSTABLES/BIO-PLASTICS: 'Compostable' or 'biodegradable' plastics, bamboo cups/cutlery, wooden utensils/chopsticks (Toronto Organics does NOT accept these).\n"
        "- WIPES: Baby wipes, makeup wipes, cleaning wipes, and even 'biodegradable/compostable' wipes (must be bagged).\n"
        "- DANGEROUS/SHARP: Broken glass, ceramics, mirrors, razors, skewers (must be wrapped safely).\n"
        "- HYGIENE/COSMETICS: Q-tips, cotton balls, floss, makeup pads, toothpaste tubes, manual toothbrushes, condoms.\n"
        "- TEXTILES & MISC: Unwanted clothing/shoes, sponges, dryer lint, incandescent bulbs, candles, cooled ashes, crystal/silica kitty litter.\n"
        "- PPE: Disposable masks, latex gloves, COVID-19 rapid test kits.\n\n"

        "=== [REJECTED] (Requires Drop-Off / Hazardous / Special) ===\n"
        "- BATTERIES: AA, AAA, Lithium-ion, car batteries, power tool batteries.\n"
        "- ELECTRONICS: Cell phones, laptops, cables, vapes/e-cigarettes, appliances, smoke alarms.\n"
        "- HAZARDOUS (HHW): Paint, motor oil, bleach, pesticides, pressurized propane/helium tanks, lighters with fluid.\n"
        "- MEDICAL SHARPS: Needles, syringes, EpiPens.\n"
        "- LARGE ITEMS: Furniture, tires, construction waste, wood, heavy metals.\n\n"

        "=== [ACCIDENTAL] ===\n"
        "- If the image has NO item in screen, or is JUST a person with no items. Set bin to 'ACCIDENTAL'.\n\n"

        "Your response MUST be in valid JSON format matching the requested schema. "
        "If an item is recyclable but dirty (e.g., a jar full of peanut butter), set processing_required: true and tell them to wash it."
    )

    # 3. Call the model with Structured Output
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            img,
            "What is this item and where does it go?"
        ],
        config=types.GenerateContentConfig(
            media_resolution="MEDIA_RESOLUTION_MEDIUM",
            system_instruction=persona,
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=WasteResponse,  # Forces the model to follow the schema
        )
    )

    print("judge finished")
    # Parse the JSON response
    return response.parsed


def classify_current_item():
    img_path = take_photo()

    if not os.path.exists(img_path):
        return None

    try:
        data = judge_item(img_path)
        return data
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return None


# --- Main Logic ---
if __name__ == "__main__":
    result = classify_current_item()
    print(result)