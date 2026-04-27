import os
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from supabase import create_client

# Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "audio", "studio", "sonorisation"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for word in keywords:
            print(f"🔍 Recherche TUNEPS : {word}")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle")
            
            # 1. Remplir le champ Objet A.O
            await page.fill("input[ng-reflect-name='bidNmFr']", word)
            
            # 2. Cliquer sur le bouton spécifique identifié
            # On cible par la classe technique du bouton submit
            await page.click("button[type='submit'].mat-flat-button")
            
            # 3. Attendre que le chargement Angular se termine
            # On attend que le tableau contenant les lignes mat-row apparaisse
            try:
                await page.wait_for_selector("tr.mat-row", timeout=10000)
                rows = await page.query_selector_all("tr.mat-row")
                print(f"✅ {len(rows)} pépites trouvées pour '{word}'")
                
                for row in rows:
                    cells = await row.query_selector_all("td.mat-cell")
                    if len(cells) >= 5:
                        # Extraction selon tes colonnes TUNEPS
                        organisme = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        expiration = (await cells[4].inner_text()).strip()

                        # 4. Insertion Supabase
                        try:
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS Public"
                            }).execute()
                            print(f"💾 Inséré : {organisme}")
                        except:
                            pass # Évite les arrêts sur doublons

            except Exception:
                print(f"ℹ️ Aucun résultat visuel pour '{word}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
