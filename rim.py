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
        # On simule un vrai navigateur Windows pour éviter le blocage
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        
        try:
            print("🌐 Ouverture du portail TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Traitement de la pépite : {word}")
                
                # 1. Attente et Saisie de l'Objet A.O
                # On utilise un sélecteur plus large au cas où ng-reflect n'est pas encore là
                input_field = page.locator("input[ng-reflect-name='bidNmFr'], input[id*='mat-input']").first
                await input_field.wait_for(state="visible", timeout=20000)
                
                # On vide le champ proprement (simulation clavier)
                await input_field.click(click_count=3)
                await page.keyboard.press("Backspace")
                await input_field.fill(word)
                
                # 2. Clic sur le BON bouton 'Rechercher'
                # On cible le bouton qui contient l'icône 'search'
                search_btn = page.locator("button.filter-btn").filter(has=page.locator("mat-icon:has-text('search')"))
                await search_btn.click()
                
                # 3. Attente du tableau de résultats
                # On attend que le loader Angular disparaisse et que les lignes apparaissent
                try:
                    await page.wait_for_selector("tr.mat-row", timeout=15000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            # Extraction propre
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # 4. Envoi Supabase
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS"
                            }).execute()
                
                except Exception:
                    print(f"ℹ️ Aucun résultat visuel pour '{word}'")
                
                # Petite pause pour ne pas saturer le serveur
                await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
