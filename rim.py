import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # headless=False pour voir la correction sur ton écran
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Connexion à TUNEPS ---")
            await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
            
            # On attend que les champs de filtrage apparaissent
            await page.wait_for_selector('input', timeout=20000)
            await page.wait_for_timeout(3000)

            # CORRECTIF : Cibler précisément le champ "Objet A.O"
            # Dans ta capture, c'est le DEUXIÈME input de la ligne de filtre
            print("Action : Saisie dans le champ Objet A.O...")
            
            # On utilise un sélecteur plus précis pour éviter le premier champ (N° A.O)
            tous_les_inputs = page.locator('input')
            
            # On remplit le deuxième champ (index 1)
            await tous_les_inputs.nth(1).click()
            await tous_les_inputs.nth(1).fill(keyword)
            
            # On clique sur le bouton "Rechercher" bleu
            await page.locator('button:has-text("Rechercher")').click()
            
            print(f"Recherche lancée pour l'objet : {keyword}")

            # 3. Attente du chargement des résultats réels
            await page.wait_for_timeout(10000) 

            # 4. Extraction des lignes (si le tableau n'est plus vide)
            rows = await page.locator("tr").all()
            print(f"Analyse de {len(rows)} lignes trouvées...")
            
            count = 0
            for row in rows:
                text = await row.inner_text()
                # On vérifie si la ligne contient le mot-clé et n'est pas le message "vide"
                if keyword.lower() in text.lower() and "Désolé" not in text:
                    cells = await row.locator("td").all()
                    if len(cells) >= 4:
                        # Index basés sur ton tableau : 1=Acheteur, 3=Objet
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        
                        print(f"Pépite trouvée : {titre[:50]}...")
                        try:
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": org,
                                "secteur": "TUNEPS"
                            }).execute()
                            count += 1
                        except Exception as e_db:
                            print(f"Erreur DB : {e_db}")

            print(f"Terminé : {count} offres ajoutées.")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
