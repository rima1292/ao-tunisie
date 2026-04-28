import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Liste de tes mots-clés stratégiques
keywords = ["musique", "audiovisuel", "sonorisation", "informatique"]

# Date du jour au format TUNEPS (JJ/MM/AAAA)
date_aujourdhui = datetime.now().strftime("%d/%m/%Y")

async def scrape_tuneps():
    async with async_playwright() as p:
        # headless=False pour voir le robot travailler en direct
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Début du Scan Multi-Clés : {date_aujourdhui} ---")
            
            for word in keywords:
                print(f"\n🔍 Recherche en cours pour : {word}")
                
                # Navigation vers la page stable identifiée
                await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(2000)

                # Saisie dans le champ "Objet A.O" (index 1)
                inputs = page.locator('input')
                await inputs.nth(1).click()
                await inputs.nth(1).fill(word)
                
                # Clic sur le bouton Rechercher
                await page.locator('button:has-text("Rechercher")').click()
                
                # Attente pour laisser le tableau se charger
                await page.wait_for_timeout(8000) 

                rows = await page.locator("tr").all()
                offres_du_mot_cle = 0
                
                for row in rows:
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        # Extraction des données
                        num_ao = (await cells[0].inner_text()).strip()
                        org = (await cells[1].inner_text()).strip()
                        date_pub = (await cells[2].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date_limite = (await cells[4].inner_text()).strip()
                        
                        # FILTRE : Uniquement aujourd'hui + mot-clé présent dans le titre
                        if date_pub == date_aujourdhui and word.lower() in titre.lower():
                            print(f"✨ Trouvé ! [{num_ao}] - {titre[:40]}...")
                            try:
                                # "secteur" a été supprimé ici comme demandé
                                supabase.table("offres").insert({
                                    "numero_ao": num_ao,
                                    "titre": titre,
                                    "organisme": org,
                                    "date_expiration": date_limite
                                }).execute()
                                offres_du_mot_cle += 1
                            except Exception:
                                # Doublon ignoré (numero_ao déjà présent)
                                pass

                print(f"✅ {offres_du_mot_cle} offre(s) trouvée(s) pour '{word}'")

            print(f"\n--- Scan terminé avec succès ---")

        except Exception as e:
            print(f"❌ Erreur Critique : {e}")
        finally:
            await page.wait_for_timeout(3000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
