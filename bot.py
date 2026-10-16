import os
import json
import re
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ALZA_URL = "https://www.alza.sk/stereo-zosilnovace/18873965.htm#f&limit=-1--500&cud=0&pg=1&prod=&par20152=4--6&par20159=2--8&sc=106"
CACHE_FILE = "products_cache.json"

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
    # Použijeme Jina API na obídenie Cloudflare blokovania na GitHub Actions
    jina_url = f"https://r.jina.ai/{ALZA_URL}"
    
    try:
        response = requests.get(jina_url, headers={"Accept": "text/markdown"})
        print(f"Jina API HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Nepodarilo sa načítať dáta, status: {response.status_code}")
            return products

        markdown_text = response.text
        
        # Jina vracia markdown obsah, kde produkty a ceny bývajú štruktúruje. 
        # Rozdelíme text na bloky/riadky a vyhľadáme produkty a ceny pomocou regulárnych výrazov.
        # Hľadáme vzory produktov a cien v eurách (napr. "349 €" alebo "349,00 €")
        
        lines = markdown_text.split('\n')
        current_title = None
        current_link = None
        
        for line in lines:
            line = line.strip()
            # Hladáme markdown odkazy, ktoré často reprezentujú názov produktu
            link_match = re.search(r'\[([^\]]+)\]\((https?://[^\)]+alza\.sk[^\)]+)\)', line)
            if link_match:
                potential_title = link_match.group(1)
                potential_link = link_match.group(2)
                # Filtrujeme len zmysluplné názvy produktov (vynecháme menu, filtre atď.)
                if len(potential_title) > 5 and "€" not in potential_title:
                    current_title = potential_title
                    current_link = potential_link

            # Hľadáme cenu v riadku (napr. "349 €" alebo "Cena: 349 €")
            price_match = re.search(r'(\d[\d\s]*(?:,\d{1,2})?)\s*€', line)
            if price_match and current_title:
                price_str = price_match.group(1).replace(' ', '').replace(',', '.')
                try:
                    price = float(price_str)
                    # Ak je cena v rozumnom limite pre zosilňovače (do 500 €)
                    if 10 <= price <= 500:
                        products[current_title] = {
                            "price": price,
                            "link": current_link or ALZA_URL
                        }
                        current_title = None # reset pre ďalší produkt
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
    print("Spúšťam kontrolu Alza zoznamu cez proxy...")
    current_products = parse_alza_products()
    
    if not current_products:
        print("Nepodarilo sa nájsť žiadne produkty.")
        return

    old_cache = load_cache()
    
    if not old_cache:
        save_cache(current_products)
        send_telegram_message(f"🤖 *Alza Bot inicializovaný!*\nSledujem {len(current_products)} produktov z vybranej kategórie.")
        print("Vytvorená počiatočná cache a odoslaná správa o inicializácii.")
        return

    changes_detected = False
    report_lines = ["🔍 *Hlásenie zmeny cien na Alze:*"]

    current_keys = set(current_products.keys())
    old_keys = set(old_cache.keys())

    # 1. Nové produkty
    for item in current_keys - old_keys:
        changes_detected = True
        p = current_products[item]
        report_lines.append(f"\n✨ *Nový produkt:* [{item}]({p['link']})\n💶 Cena: *{p['price']} €*")

    # 2. Vypadnuté produkty
    for item in old_keys - current_keys:
        changes_detected = True
        report_lines.append(f"\n❌ *Vypredaný / Zmizol z ponuky:* {item}")

    # 3. Zmeny cien
    for item in current_keys & old_keys:
        old_price = old_cache[item]["price"]
        new_price = current_products[item]["price"]
        link = current_products[item]["link"]

        if new_price != old_price:
            changes_detected = True
            diff = new_price - old_price
            if new_price < old_price:
                report_lines.append(f"\n📉 *ZĽAVA!* [{item}]({link})\n💶 Stará cena: {old_price} € ➡️ Nová cena: *{new_price} €* (Ušetríš {abs(diff):.2f} €)")
            else:
                report_lines.append(f"\n📈 *Zdraženie:* [{item}]({link})\n💶 Stará cena: {old_price} € ➡️ Nová cena: *{new_price} €* (Vzostup o {diff:.2f} €)")

    save_cache(current_products)

    if changes_detected:
        send_telegram_message("\n".join(report_lines))
        print("Zmeny boli zaznamenané a odoslané do Telegramu.")
    else:
        print("Žiadne nové zmeny cien ani produktov.")

if __name__ == "__main__":
    main()
