
import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "numérique"

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Connexion à TUNEPS ---")
            await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
            
            await page.wait_for_selector('input', timeout=20000)
            await page.wait_for_timeout(3000)

            tous_les_inputs = page.locator('input')
            await tous_les_inputs.nth(1).click()
            await tous_les_inputs.nth(1).fill(keyword)
            
            await page.locator('button:has-text("Rechercher")').click()
            await page.wait_for_timeout(10000) 

            rows = await page.locator("tr").all()
            count = 0
            
            for row in rows:
                text = await row.inner_text()
                if keyword.lower() in text.lower() and "Désolé" not in text:
                    cells = await row.locator("td").all()
                    
                    if len(cells) >= 5:
                        # Extraction selon l'ordre du tableau TUNEPS
                        num_ao = (await cells[0].inner_text()).strip()      # N° A.O
                        org = (await cells[1].inner_text()).strip()         # Acheteur public
                        date_pub = (await cells[2].inner_text()).strip()    # Date Publication
                        titre = (await cells[3].inner_text()).strip()       # Objet A.O
                        date_lim = (await cells[4].inner_text()).strip()    # Dernier Délai (Expiration)
                        
                        print(f"Pépite : {num_ao} | {titre[:30]}...")
                        
                        try:
                            # On envoie TOUS les champs vers Supabase
                            supabase.table("offres").insert({
                                "numero_ao": num_ao,
                                "titre": titre,
                                "organisme": org,
                                "date_publication": date_pub,
                                "date_expiration": date_lim,
                                "secteur": "TUNEPS"
                            }).execute()
                            count += 1
                        except Exception as e_db:
                            print(f"Erreur ou doublon pour {num_ao}")

            print(f"Terminé : {count} nouvelles offres ajoutées avec tous les détails.")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
