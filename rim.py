import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Mot-cle de recherche
keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # headless=False permet de VOIR le navigateur sur ton PC
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Lancement du scan pour : {keyword} ---")
            
            # Navigation vers la page de recherche
            await page.goto("https://www.tuneps.tn/search/searchAvisInp.do", wait_until="domcontentloaded", timeout=60000)
            
            # 2. Ciblage du DEUXIEME champ (index 1)
            print("Attente des champs de saisie...")
            await page.wait_for_selector('input', timeout=30000)
            
            inputs = page.locator('input')
            count = await inputs.count()
            
            if count >= 2:
                print(f"Action : Saisie dans le 2eme champ sur {count} trouves...")
                # On clique pour donner le focus et on remplit
                await inputs.nth(1).click()
                await inputs.nth(1).fill(keyword)
                # On simule la touche Entree
                await page.keyboard.press("Enter")
                print("Recherche envoyee.")
            else:
                print("Erreur : Pas assez de champs de saisie trouves.")
                return

            # 3. Attente des resultats (15 secondes pour laisser le temps au site de repondre)
            print("Attente des resultats (15s)...")
            await page.wait_for_timeout(15000) 

            # 4. Extraction des donnees
            rows = await page.locator("tr").all()
            print(f"Analyse de {len(rows)} lignes trouvees...")
            
            offres_ajoutees = 0
            for row in rows:
                text = await row.inner_text()
                # On verifie si le mot-cle est dans la ligne
                if keyword.lower() in text.lower():
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()
                        
                        # On filtre les messages "aucun resultat"
                        if titre and "aucun" not in titre.lower():
                            print(f"Capture : {titre[:50]}")
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

            print(f"Termine : {offres_ajoutees} offres envoyees en base.")

        except Exception as e:
            print(f"Erreur Critique : {e}")
        finally:
            # On attend 5 secondes avant de fermer pour que tu puisses voir le resultat final
            await page.wait_for_timeout(5000)
            await browser.close()
            print("--- Fin du script ---")

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
