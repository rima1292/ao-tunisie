import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "sonorisation", "studio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # Lancement avec un User-Agent pour éviter d'être détecté comme bot
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Recherche pour : {word}")
                
                # Attente du champ 'Objet A.O'
                input_selector = "input[ng-reflect-name='bidNmFr']"
                await page.wait_for_selector(input_selector, state="visible", timeout=20000)
                
                # Simulation humaine : on vide et on tape
                await page.click(input_selector, click_count=3)
                await page.keyboard.press("Backspace")
                await page.fill(input_selector, word)
                
                # 2. CLIC SÉCURISÉ : On cherche le bouton qui contient le texte "Rechercher"
                # XPath est plus précis ici pour différencier les deux boutons mat-flat-button
                search_button = page.locator("//button[contains(., 'Rechercher')]")
                await search_button.click()
                
                # 3. Attente du rafraîchissement Angular
                # On attend que le tableau de résultats soit visible
                try:
                    await page.wait_for_selector("tr.mat-row", timeout=15000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            # Extraction des données
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # 4. Insertion Supabase
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS"
                            }).execute()
                            print(f"💾 Ajouté : {organisme}")
                
                except Exception:
                    print(f"ℹ️ Aucun résultat pour '{word}'")

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
