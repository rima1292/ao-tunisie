import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # On utilise le runner local (ton PC)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Lancement du scan pour : {keyword} ---")
            
            # 1. Aller sur la page de recherche
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            # 2. Saisie du mot-clé
            input_selector = 'input[matinput]'
            await page.wait_for_selector(input_selector, timeout=20000)
            await page.fill(input_selector, keyword)
            
            # 3. Lancer la recherche par la touche Entrée (plus fiable que le clic bouton)
            print("Action : Envoi de la recherche...")
            await page.keyboard.press("Enter")
            
            # 4. Attente du chargement des données
            print("Attente des resultats (10s)...")
            await page.wait_for_timeout(10000) 

            # 5. Extraction des lignes du tableau
            # On cherche les lignes du tableau mat-table
            rows = await page.locator("tr.mat-row").all()
            
            if not rows:
                print("Info : Aucun resultat visible sur la page.")
                # Petit debug : on prend une photo si on est sur ton PC (optionnel)
                # await page.screenshot(path="debug_tuneps.png")
            else:
                print(f"Succes : {len(rows)} lignes detectees.")
            
            for row in rows:
                cells = await row.locator("td.mat-cell").all()
                if len(cells) >= 5:
                    titre = (await cells[3].inner_text()).strip()
                    org = (await cells[1].inner_text()).strip()
                    date = (await cells[4].inner_text()).strip()
                    
                    if titre and "aucun" not in titre.lower():
                        print(f"Capture : {titre[:50]}...")
                        
                        # Envoi vers Supabase
                        try:
                            supabase.table("offres").insert({
                                "titre": titre, 
                                "organisme": org,
                                "date_expiration": date, 
                                "secteur": "TUNEPS"
                            }).execute()
                        except Exception as e_db:
                            print(f"Erreur Supabase : {e_db}")

        except Exception as e:
            print(f"Erreur Critique : {e}")
        finally:
            await browser.close()
            print("--- Fin du script ---")

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
