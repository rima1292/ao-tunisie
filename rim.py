import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

async def scrape_ao():
    async with async_playwright() as p:
        # Lancement du navigateur
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. On va sur la page de recherche avec tes filtres
        # On utilise l'URL directe pour National + Tunisie + Mot-clé 'audio'
        search_url = "https://www.appeloffres.net/recherche?q=audio&type=national&pays=tunisie"
        print(f"🌐 Accès à : {search_url}")
        await page.goto(search_url, wait_until="networkidle")

        # 2. On attend que le tableau soit chargé
        try:
            await page.wait_for_selector("tr.cursor-pointer", timeout=15000)
            rows = await page.query_selector_all("tr.cursor-pointer")
            print(f"✅ {len(rows)} offres détectées sur la page.")
        except Exception as e:
            print("❌ Le tableau n'a pas été trouvé ou est vide.")
            await browser.close()
            return

        for row in rows:
            cells = await row.query_selector_all("td")
            
            if len(cells) >= 4:
                # Extraction avec sécurité (on prend le texte brut)
                titre = (await cells[1].inner_text()).strip()
                organisme = (await cells[3].inner_text()).strip()
                # La date est souvent dans la dernière ou l'avant-dernière colonne
                date_exp = (await cells[-1].inner_text()).strip().split('\n')[0]

                # 3. Insertion Supabase
                try:
                    # On utilise 'upsert' pour éviter les doublons si tu as une colonne ID unique
                    data = supabase.table("offres").insert({
                        "titre": titre,
                        "organisme": organisme,
                        "date_expiration": date_exp,
                        "secteur": "Audio & Musique"
                    }).execute()
                    print(f"💾 Inséré : {titre[:40]}...")
                except Exception as db_err:
                    print(f"⚠️ Erreur insertion Supabase : {db_err}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_ao())
