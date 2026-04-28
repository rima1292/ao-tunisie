import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Liste de tes mots-clés
keywords = ["musique", "audiovisuel", "sonorisation", "informatique"]

# Date du jour (JJ/MM/AAAA)
date_aujourdhui = datetime.now().strftime("%d/%m/%Y")

async def scrape_tuneps():
    async with async_playwright() as p:
        # On garde headless=False pour que tu puisses voir chaque étape
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Début du Scan : {date_aujourdhui} ---")
            
            for word in keywords:
                print(f"\n🤖 Passage au mot-clé suivant : {word}")
                
                # Aller sur la page stable
                await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                # Cibler le champ "Objet A.O" (index 1)
                input_field = page.locator('input').nth(1)
                
                # On vide le champ avant d'écrire le nouveau mot
                await input_field.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                
                await input_field.fill(word)
                await page.locator('button:has-text("Rechercher")').click()
                
                # On attend que TUNEPS traite la demande
                print(f"⏳ Recherche de '{word}' en cours...")
                await page.wait_for_timeout(10000) 

                rows = await page.locator("tr").all()
                found_count = 0
                
                for row in rows:
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        # Extraction des infos
                        num_ao = (await cells[0].inner_text()).strip()
                        org = (await cells[1].inner_text()).strip()
                        date_pub = (await cells[2].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date_limite = (await cells[4].inner_text()).strip()
                        
                        # FILTRE : Date du jour uniquement
                        if date_pub == date_aujourdhui and word.lower() in titre.lower():
                            try:
                                supabase.table("offres").insert({
                                    "numero_ao": num_ao,
                                    "titre": titre,
                                    "organisme": org,
                                    "date_expiration": date_limite
                                }).execute()
                                print(f"✅ Enregistré : {num_ao}")
                                found_count += 1
                            except Exception:
                                pass # Doublon déjà en base

                print(f"Fin pour '{word}' : {found_count} trouvé(s).")

            print(f"\n--- Félicitations Rim, le scan complet est fini ! ---")

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
