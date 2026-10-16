import os
import json
import requests
from bs4 import BeautifulSoup

# Načítanie premenných prostredia z GitHub Secrets
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Alza URL adresa z tvojho zadania
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "sk-SK,sk;q=0.9,cs;q=0.8,en-US;q=0.7,en;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    products = {}
    try:
        response = requests.get(ALZA_URL, headers=headers)
        print(f"Alza HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Nepodarilo sa načítať Alzu, status: {response.status_code}")
            return products

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Hľadáme elementy produktov v zozname na Alze
        items = soup.select('.box.browsingitem')
        if not items:
            items = soup.select('.browsingitem')
        if not items:
            items = soup.select('.item')

        print(f"Nájdených elementov produktov: {len(items)}")

        for item in items:
            title_elem = item.select_one('.name, .browsingitem-title, a.name')
            price_elem = item.select_one('.price-box__price, .cena, span.price')
            link_elem = item.select_one('a.name, a.browsingitem-title, h3 a')

            if title_elem and price_elem:
                name = title_elem.get_text(strip=True)
                price_str = price_elem.get_text(strip=True)
                
                # Vyčistenie ceny na číslo
                price_clean = ''.join(c for c in price_str if c.isdigit() or c == ',').replace(',', '.')
                try:
                    price = float(price_clean)
                except ValueError:
                    continue
                
                link = ""
                if link_elem and link_elem.has_attr('href'):
                    link = link_elem['href']
                    if not link.startswith('http'):
                        link = "https://www.alza.sk" + link

                products[name] = {
                    "price": price,
                    "link": link
                }
                
    except Exception as e:
        print(f"Chyba pri parsovaní Alzy: {e}")
        
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
    print("Spúšťam kontrolu Alza zoznamu...")
    current_products = parse_alza_products()
    
    if not current_products:
        print("Nepodarilo sa nájsť žiadne produkty (možná ochrana proti botom alebo zmena štruktúry).")
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
    new_items = current_keys - old_keys
    for item in new_items:
        changes_detected = True
        p = current_products[item]
        report_lines.append(f"\n✨ *Nový produkt:* [{item}]({p['link']})\n💶 Cena: *{p['price']} €*")

    # 2. Vypadnuté produkty
    removed_items = old_keys - current_keys
    for item in removed_items:
        changes_detected = True
        report_lines.append(f"\n❌ *Vypredaný / Zmizol z ponuky:* {item}")

    # 3. Zmeny cien
    common_items = current_keys & old_keys
    for item in common_items:
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
        full_message = "\n".join(report_lines)
        send_telegram_message(full_message)
        print("Zmeny boli zaznamenané a odoslané do Telegramu.")
    else:
        print("Žiadne nové zmeny cien ani produktov.")

if __name__ == "__main__":
    main()
