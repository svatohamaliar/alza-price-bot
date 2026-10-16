import os
import json
import re
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ALZA_URL = "https://www.alza.sk/stereo-zosilnovace/18873965.htm#f&limit=-1--500&cud=0&pg=1&prod=&par20152=4--6&par20159=2--8&sc=106"
CACHE_FILE = "products_cache.json"
DEBUG_FILE = "debug_alza.md"

def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Chýbajú Telegram token alebo Chat ID!")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Chyba pri odosielaní správy do Telegramu: {e}")

def parse_alza_products():
    products = {}
    jina_url = f"https://r.jina.ai/{ALZA_URL}"
    
    try:
        response = requests.get(jina_url, headers={"Accept": "text/markdown"})
        print(f"Jina API HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Nepodarilo sa načítať dáta, status: {response.status_code}")
            return products

        markdown_text = response.text

        # Uložíme surový výstup do súboru, aby sme videli, čo presne prišlo
        with open(DEBUG_FILE, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        print(f"Debugovací súbor {DEBUG_FILE} bol úspešne uložený.")

        lines = markdown_text.split('\n')
        current_title = None
        current_link = None
        
        for line in lines:
            line = line.strip()
            
            # Hľadáme odkazy vo formáte [Názov](URL)
            link_match = re.search(r'\[([^\]]+)\]\((https?://[^\)]+alza\.sk[^\)]+)\)', line)
            if link_match:
                title = link_match.group(1).strip()
                link = link_match.group(2).strip()
                if len(title) > 10 and "€" not in title and "http" not in title and "Alza" not in title:
                    current_title = title
                    current_link = link

            # Hľadáme cenu v riadku
            price_match = re.search(r'([\d\s]+(?:,\d{1,2})?)\s*€', line)
            if price_match and current_title:
                price_str = price_match.group(1).replace(' ', '').replace(',', '.')
                try:
                    price = float(price_str)
                    if 10 <= price <= 500:
                        products[current_title] = {
                            "price": price,
                            "link": current_link
                        }
                        current_title = None
                except ValueError:
                    pass

        print(f"Úspešne parsovaných produktov: {len(products)}")

    except Exception as e:
        print(f"Chyba pri parsovaní: {e}")
        
    return products

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    print("Spúštam kontrolu Alza zoznamu cez proxy...")
    current_products = parse_alza_products()
    
    # Uložíme dáta do cache (aj keby boli prázdne, ale aspoň uvidíme debug súbor)
    old_cache = load_cache()
    
    if not current_products:
        print("Nepodarilo sa nájsť žiadne produkty, ale debug súbor je vytvorený.")
        return

    if not old_cache:
        save_cache(current_products)
        send_telegram_message(f"🤖 *Alza Bot inicializovaný!*\nSledujem {len(current_products)} produktov.")
        print("Vytvorená počiatočná cache a odoslaná správa.")
        return

    # Ďalšia logika pre zmeny cien...
    save_cache(current_products)

if __name__ == "__main__":
    main()
