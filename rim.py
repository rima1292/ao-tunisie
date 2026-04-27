
 import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "sonorisation", "studio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Recherche manuelle pour : {word}")
                
                # Ciblage de l'input 'Objet A.O'
                input_selector = "input[ng-reflect-name='bidNmFr']"
                await page.wait_for_selector(input_selector, state="visible", timeout=20000)
                
                # Simulation humaine : vider et remplir
                await page.click(input_selector, click_count=3)
                await page.keyboard.press("Backspace")
                await page.fill(input_selector, word)
                
                # Clic sur le bouton bleu 'Rechercher'
                await page.click("button.filter-btn.mat-primary")
                
                # Pause pour le chargement Angular
                await page.wait_for_timeout(4000) 
                
                try:
                    # Lecture des résultats
                    rows = await page.query_selector_all("tr.mat-row")
                    if rows:
                        print(f"✅ {len(rows)} offres trouvées.")
                        for row in rows:
                            cells = await row.query_selector_all("td.mat-cell")
                            if len(cells) >= 5:
                                organisme = (await cells[1].inner_text()).strip()
                                titre = (await cells[3].inner_text()).strip()
                                expiration = (await cells[4].inner_text()).strip()

                                # Insertion Supabase
                                supabase.table("offres").insert({
                                    "titre": titre, "organisme": organisme,
                                    "date_expiration": expiration, "secteur": "TUNEPS"
                                }).execute()
                    else:
                        print(f"ℹ️ Aucun résultat pour '{word}'")
                except:
                    continue

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
