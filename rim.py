import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "audio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # On définit un User-Agent pour éviter d'être bloqué comme un robot
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Tentative pour : {word}")
                
                # On attend explicitement que n'importe quel input soit visible avant de chercher le spécifique
                await page.wait_for_selector("input", timeout=20000)
                
                # On utilise un sélecteur plus large (placeholder ou attribut name)
                search_input = page.locator("input[ng-reflect-name='bidNmFr'], input[placeholder*='Objet']").first
                
                await search_input.fill(word)
                
                # On clique sur le bouton de recherche
                await page.click("button[type='submit']")
                
                # Attente des résultats
                try:
                    await page.wait_for_selector("tr.mat-row", timeout=10000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": organisme, 
                                "date_expiration": expiration, "secteur": "TUNEPS"
                            }).execute()
                except:
                    print(f"ℹ️ Aucun résultat visuel pour '{word}'")
                    
        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
