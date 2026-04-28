import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Mot-clé de recherche
keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # headless=True pour le runner, mais tu peux mettre False sur ton PC pour voir
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Lancement du scan pour : {keyword} ---")
            
            # Navigation vers la page de recherche directe
            await page.goto("https://www.tuneps.tn/search/searchAvisInp.do", wait_until="domcontentloaded", timeout=60000)
            
            # 2. Ciblage du DEUXIÈME champ (nth(1))
            print("Attente des champs de saisie...")
            await page.wait_for_selector('input', timeout=30000)
            
            inputs = page.locator('input')
            count = await inputs.count()
            
            if count >= 2:
                print(f"Action : Saisie dans le 2ème champ sur {count} trouvés...")
                # On clique et on remplit le deuxième champ (index 1)
                await inputs.nth(1).click()
                await inputs.nth(1).fill(keyword)
                await page.keyboard.press("Enter")
                print(f"Mot-clé '{keyword}' envoyé.")
            else:
                print("Erreur : Impossible de trouver le deuxième champ.")
                return

            # 3. Attente du chargement des résultats
            print("⏳ Attente des résultats (12s)...")
            await page.wait_for_timeout(12000) 

            # 4. Extraction des données
            rows = await page.locator("tr").all()
            print(f"Analyse de {len(rows)} lignes potentielles...")
            
            offres_ajoutees = 0
            for row in rows:
                text = await row.inner_text()
                # On vérifie si la ligne contient le mot-clé
                if keyword.lower() in text.lower():
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()
                        
                        # On évite les lignes vides ou de message "aucun résultat"
                        if titre and "aucun" not in titre.lower():
                            print(f"💾 Capture : {titre[:50]}...")
                            
                            try:
                                supabase.table("offres").insert({
                                    "titre": titre, 
                                    "organisme": org,
                                    "date_expiration": date, 
                                    "secteur": "TUNEPS"
                                }).execute()
                                offres_ajoutees += 1
                            except Exception as e_db:
                                print(f"Erreur Supabase : {e_db}")

            print(f"--- Terminé : {offres_ajoutees} offres en base ! ---")

        except Exception as e:
            print(f"Erreur Critique : {e}")
        finally:
            await browser.close()
            print("--- Fin du script ---")

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
