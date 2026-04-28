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
        # On garde headless=False pour que tu puisses voir le succès sur ton écran
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Connexion a la page stable : /portail/offres ---")
            
            # 1. Navigation vers l'URL que tu as identifiée
            await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
            
            # On attend que le formulaire soit bien là
            await page.wait_for_timeout(5000)

            # 2. Recherche du champ de saisie
            # Sur cette page, on cherche souvent un input type text
            print("Recherche du champ de recherche...")
            search_input = page.locator('input[type="text"]').first
            
            if await search_input.is_visible():
                await search_input.click()
                await search_input.fill(keyword)
                await page.keyboard.press("Enter")
                print(f"Recherche pour '{keyword}' lancee.")
            else:
                print("Champ de recherche non detecte, tentative alternative...")
                # Si le premier echoue, on remplit le 2eme champ comme tu l'as suggere
                await page.locator('input').nth(1).fill(keyword)
                await page.keyboard.press("Enter")

            # 3. Attente des resultats
            print("Attente du chargement du tableau (12s)...")
            await page.wait_for_timeout(12000) 

            # 4. Extraction des lignes
            # On cible les lignes du tableau (souvent dans un <tbody>)
            rows = await page.locator("tr").all()
            print(f"Analyse de {len(rows)} lignes trouvees...")
            
            count = 0
            for row in rows:
                text = await row.inner_text()
                if keyword.lower() in text.lower():
                    cells = await row.locator("td").all()
                    if len(cells) >= 3:
                        # On adapte les index selon la structure de cette page
                        org = (await cells[1].inner_text()).strip() if len(cells) > 1 else "Inconnu"
                        titre = (await cells[2].inner_text()).strip() if len(cells) > 2 else "Sans titre"
                        
                        if "aucun" not in titre.lower():
                            print(f"Capture : {titre[:50]}...")
                            try:
                                supabase.table("offres").insert({
                                    "titre": titre,
                                    "organisme": org,
                                    "secteur": "TUNEPS"
                                }).execute()
                                count += 1
                            except Exception as e_db:
                                print(f"Erreur DB : {e_db}")

            print(f"Termine : {count} nouvelles pépites en base !")

        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
