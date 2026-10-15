import os
import datetime
import requests

def main():
    # Načítanie hodnot z prostredia (GitHub Secrets)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Chyba: TELEGRAM_BOT_TOKEN alebo TELEGRAM_CHAT_ID nie je nastavené!")
        return

    # Získanie aktuálneho času vo formáte HH:MM
    teraz = datetime.datetime.now().strftime("%H:%M")
    sprava = f"ahoj {teraz}"

    # Odoslanie správy cez Telegram API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": sprava
    }

    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print(f"Správa '{sprava}' bola úspešne odoslaná.")
    else:
        print(f"Chyba pri odosielaní: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()