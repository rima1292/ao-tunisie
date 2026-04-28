import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Tes nouveaux mots-clés
keywords = ["audiovisuel", "sonorisation", "informatique", "musique"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # headless=False pour voir le comportement
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            for keyword in keywords:
                print(f"--- Lancement de la recherche pour : {keyword} ---")
                await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
                
                # On attend que les champs de filtrage apparaissent
                await page.wait_for_selector('input', timeout=20000)
                await page.wait_for_timeout(3000)

                # Ciblage du DEUXIÈME input (Objet A.O)
                tous_les_inputs = page.locator('input')
                
                print(f"Saisie du mot-clé : {keyword}")
                await tous_les_inputs.nth(1).click()
                await tous_les_inputs.nth(1).fill(keyword)
                
                # Clic sur le bouton "Rechercher"
                await page.locator('button:has-text("Rechercher")').click()
                
                # 3. Attente du chargement
                await page.wait_for_timeout(10000) 

                # 4. Extraction
                rows = await page.locator("tr").all()
                count_for_word = 0
                
                for row in rows:
                    text = await row.inner_text()
                    if keyword.lower() in text.lower() and "Désolé" not in text:
                        cells = await row.locator("td").all()
                        if len(cells) >= 4:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            
                            print(f"Pépite trouvée ({keyword}) : {titre[:50]}...")
                            try:
                                supabase.table("offres").insert({
                                    "titre": titre,
                                    "organisme": org
                                }).execute()
                                count_for_word += 1
                            except Exception as e_db:
                                print(f"Note : Doublon ou erreur DB pour '{titre[:20]}'")

                print(f"Terminé pour '{keyword}' : {count_for_word} offres ajoutées.\n")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
