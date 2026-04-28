import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # On garde headless=False pour que tu puisses voir la correction
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Tentative de connexion stable ---")
            
            # On va sur l'accueil recherche au lieu du lien direct 404
            await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # 2. On cherche le champ de saisie (on essaie tous les inputs si le 2eme echoue)
            print("Analyse des champs disponibles...")
            inputs = page.locator('input')
            count = await inputs.count()
            
            if count > 0:
                # On essaie de remplir le champ qui semble etre celui de la recherche
                # Si le 2eme (index 1) ne marche pas, on essaie le 1er (index 0)
                target_index = 1 if count >= 2 else 0
                print(f"Saisie dans le champ index {target_index}...")
                
                await inputs.nth(target_index).click()
                await inputs.nth(target_index).fill(keyword)
                await page.keyboard.press("Enter")
                print("Recherche lancee.")
            else:
                print("Erreur : Aucun champ trouvé. Le site a peut-être un probleme de chargement.")
                return

            # 3. Attente des resultats
            print("⏳ Attente des resultats (15s)...")
            await page.wait_for_timeout(15000) 

            # 4. Extraction
            rows = await page.locator("tr").all()
            offres_ajoutees = 0
            
            for row in rows:
                text = await row.inner_text()
                if keyword.lower() in text.lower():
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()
                        
                        if titre and "aucun" not in titre.lower():
                            print(f"💾 Trouve : {titre[:50]}")
                            try:
                                supabase.table("offres").insert({
                                    "titre": titre, "organisme": org,
                                    "date_expiration": date, "secteur": "TUNEPS"
                                }).execute()
                                offres_ajoutees += 1
                            except Exception as e_db:
                                print(f"Erreur DB : {e_db}")

            print(f"Termine : {offres_ajoutees} offres ajoutees.")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(4000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
