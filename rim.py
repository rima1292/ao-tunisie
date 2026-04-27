
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
        # On lance le navigateur
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Navigation vers le portail TUNEPS...")
            # On attend que la page soit totalement chargée
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Traitement du mot-clé : {word}")
                
                # 1. On attend que l'input soit prêt et on tape manuellement
                input_selector = "input[ng-reflect-name='bidNmFr']"
                await page.wait_for_selector(input_selector, state="visible", timeout=20000)
                
                # On vide le champ avant de taper (important pour les boucles)
                await page.click(input_selector, click_count=3)
                await page.keyboard.press("Backspace")
                await page.fill(input_selector, word)
                
                # 2. Clic manuel sur le bouton bleu 'Rechercher'
                # On utilise un sélecteur plus robuste qui cherche le bouton avec l'icône loupe
                search_button = page.locator("button.filter-btn.mat-primary").first
                await search_button.click()
                
                # 3. Attente du rafraîchissement du tableau
                await page.wait_for_timeout(3000) # Pause pour laisser Angular réagir
                
                try:
                    # On attend que les lignes de résultats mat-row apparaissent
                    await page.wait_for_selector("tr.mat-row", timeout=10000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées pour '{word}'")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            # Extraction selon la structure TUNEPS
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # 4. Envoi vers Supabase
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS Public"
                            }).execute()
                    
                except Exception:
                    print(f"ℹ️ Aucun résultat pour '{word}'")
                
                # On réinitialise pour le prochain mot-clé si nécessaire
                await page.wait_for_timeout(1000)

        except Exception as e:
            print(f"❌ Erreur critique sur TUNEPS : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
