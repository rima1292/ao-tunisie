import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "audiovisuel"

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

            print("Action : Saisie dans le champ Objet A.O...")
            tous_les_inputs = page.locator('input')
            
            await tous_les_inputs.nth(1).click()
            await tous_les_inputs.nth(1).fill(keyword)
            
            await page.locator('button:has-text("Rechercher")').click()
            print(f"Recherche lancée pour l'objet : {keyword}")

            await page.wait_for_timeout(10000) 

            rows = await page.locator("tr").all()
            print(f"Analyse de {len(rows)} lignes trouvées...")
            
            count = 0
            for row in rows:
                text = await row.inner_text()
                if keyword.lower() in text.lower() and "Désolé" not in text:
                    cells = await row.locator("td").all()
                    # On vérifie qu'on a bien toutes les colonnes nécessaires
                    if len(cells) >= 5:
                        # Index basés sur le tableau TUNEPS :
                        # 0=N°AO, 1=Acheteur, 2=Date Pub, 3=Objet, 4=Délai
                        org = (await cells[1].inner_text()).strip()
                        date_pub = (await cells[2].inner_text()).strip() # <--- AJOUT ICI
                        titre = (await cells[3].inner_text()).strip()
                        
                        print(f"Pépite trouvée : {titre[:50]}... (Publié le : {date_pub})")
                        try:
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": org,
                                "date_publication": date_pub, # <--- INSERTION ICI
                                "secteur": "TUNEPS"
                            }).execute()
                            count += 1
                        except Exception as e_db:
                            print(f"Erreur DB : {e_db}")

            print(f"Terminé : {count} offres ajoutées.")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
