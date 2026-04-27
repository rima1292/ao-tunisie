import os
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from supabase import create_client

# Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["musique", "audio", "photographie", "سمعية بصرية"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Dates dynamiques au format TUNEPS (JJ/MM/AAAA)
        start_date = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        
        for word in keywords:
            print(f"🔍 Filtrage TUNEPS pour : {word}")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle")
            
            # 1. Remplir l'input 'Objet A.O'
            # On cible l'input qui contient le label ou le placeholder 'Objet A.O'
            await page.fill("input[ng-reflect-name='bidNmFr']", word)
            
            # 2. Gérer le filtre 'Mode passation' ou 'Type' si nécessaire
            # Pour un filtre simple, on peut juste cliquer sur Rechercher après le mot-clé
            await page.click("button.mat-raised-button.mat-primary") # Le bouton bleu 'Rechercher'
            
            try:
                # 3. Attendre le tableau de résultats Angular
                await page.wait_for_selector("tr.mat-row", timeout=12000)
                rows = await page.query_selector_all("tr.mat-row")
                print(f"✅ {len(rows)} pépites trouvées pour '{word}'")
                
                for row in rows:
                    # Extraction basée sur tes colonnes mat-cell
                    cells = await row.query_selector_all("td.mat-cell")
                    
                    if len(cells) >= 5:
                        # Colonne 1: Organisme (bidInstNm)
                        organisme = (await cells[1].inner_text()).strip()
                        # Colonne 3: Titre (bidNmFr)
                        titre = (await cells[3].inner_text()).strip()
                        # Colonne 4: Date d'expiration (bdRecvEndDt)
                        expiration = (await cells[4].inner_text()).strip()

                        # 4. Insertion dans ta table Supabase
                        supabase.table("offres").insert({
                            "titre": titre,
                            "organisme": organisme,
                            "date_expiration": expiration,
                            "secteur": "TUNEPS Public"
                        }).execute()
                        print(f"💾 Ajouté : {organisme}")

            except Exception:
                print(f"ℹ️ Aucun résultat pour '{word}' avec ces filtres.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
