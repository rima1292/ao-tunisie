import os
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase (Vérifie bien tes Secrets GitHub)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["musique", "audio", "visuel", "instrument","سمعية بصرية","studio","sonorisation"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # Lancement en mode headless pour GitHub Actions
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Dates dynamiques au format TUNEPS (JJ/MM/AAAA)
        start_date = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for word in keywords:
            print(f"🔍 Filtrage TUNEPS pour : {word}")
            # Accès à la page de recherche TUNEPS
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle")
            
            # 2. Remplissage du champ 'Objet A.O'
            # Utilisation du sélecteur technique identifié dans ton HTML
            try:
                await page.fill("input[ng-reflect-name='bidNmFr']", word)
                
                # 3. Activation du filtre 'National' (si besoin d'affiner)
                # Cliquer sur le bouton bleu 'Rechercher'
                await page.click("button.mat-raised-button.mat-primary") 
                
                # 4. Attente du tableau de résultats Angular (mat-row)
                await page.wait_for_selector("tr.mat-row", timeout=15000)
                rows = await page.query_selector_all("tr.mat-row")
                print(f"✅ {len(rows)} pépites trouvées pour '{word}'")
                
                for row in rows:
                    # Extraction basée sur les classes Angular mat-cell
                    cells = await row.query_selector_all("td.mat-cell")
                    
                    if len(cells) >= 5:
                        # Index basés sur ton extrait HTML
                        organisme = (await cells[1].inner_text()).strip() # bidInstNm
                        titre = (await cells[3].inner_text()).strip()     # bidNmFr
                        expiration = (await cells[4].inner_text()).strip() # bdRecvEndDt

                        # 5. Insertion propre dans Supabase
                        try:
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS Public"
                            }).execute()
                            print(f"💾 Ajouté à Supabase : {organisme}")
                        except Exception as e:
                            print(f"⚠️ Erreur insertion : {e}")

            except Exception:
                print(f"ℹ️ Aucun résultat pour '{word}' lors de ce passage.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
