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
        # On définit un écran plus grand pour être sûr que les boutons sont cliquables
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Recherche de la pépite : {word}")
                
                # 1. On attend l'input 'Objet A.O'
                input_selector = "input[ng-reflect-name='bidNmFr']"
                await page.wait_for_selector(input_selector, state="visible", timeout=15000)
                
                # On nettoie le champ avant d'écrire
                await page.click(input_selector, click_count=3)
                await page.keyboard.press("Backspace")
                await page.fill(input_selector, word)
                
                # 2. Clic sur le bouton de recherche
                # On utilise un sélecteur qui cherche le texte 'Rechercher' à l'intérieur du bouton bleu
                search_btn = page.locator("button").filter(has_text="Rechercher")
                await search_btn.click()
                
                # 3. Attente dynamique des résultats
                # On fait une pause forcée car TUNEPS met du temps à rafraîchir son tableau Angular
                await page.wait_for_timeout(5000) 
                
                try:
                    # On attend l'apparition d'une cellule de donnée réelle
                    await page.wait_for_selector("td.mat-cell", timeout=15000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées pour '{word}'.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            # Extraction des textes
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
                            print(f"💾 Sauvegardé : {organisme}")
                            
                except Exception:
                    print(f"ℹ️ Pas de résultats visibles pour '{word}' après recherche.")
                
                # Petite pause pour éviter le blocage IP
                await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
