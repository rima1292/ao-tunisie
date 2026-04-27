import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Liste des pépites à chercher
keywords = ["audiovisuel", "musique", "sonorisation", "studio", "instrument"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # Lancement du navigateur
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Connexion au portail TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Recherche active pour : {word}")
                
                # Attendre que l'input soit prêt
                input_selector = "input[ng-reflect-name='bidNmFr']"
                await page.wait_for_selector(input_selector, state="visible", timeout=20000)
                
                # Nettoyage et saisie "humaine"
                await page.click(input_selector, click_count=3)
                await page.keyboard.press("Backspace")
                await page.fill(input_selector, word)
                
                # 2. Clic sur le bouton de recherche
                # On cible spécifiquement le bouton bleu 'Rechercher'
                search_button = page.locator("button.mat-flat-button.mat-primary").filter(has_text="Rechercher")
                await search_button.click()
                
                # 3. CRUCIAL : Attendre que le tableau se mette à jour
                # On attend que le texte 'Chargement' disparaisse ou que les cellules apparaissent
                try:
                    # On attend explicitement qu'une cellule de donnée soit visible
                    await page.wait_for_selector("td.mat-cell", timeout=15000)
                    
                    # Lecture des lignes mat-row
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres détectées pour '{word}'")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
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
                            print(f"💾 Inséré : {organisme}")
                
                except Exception:
                    print(f"ℹ️ Aucun résultat visible pour '{word}' après 15s.")
                
                # Petite pause entre les mots-clés pour éviter le ban
                await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
