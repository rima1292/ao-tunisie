import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client
from datetime import datetime

# Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["musique", "audiovisuel", "sonorisation"]
today = datetime.now().strftime("%d/%m/%Y")

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)

            for word in keywords:
                print(f"🔍 Recherche large pour : {word}")
                
                # Injection JS pour remplir l'Objet A.O ET forcer les dates
                await page.evaluate(f"""
                    (val, dateFin) => {{
                        // 1. Remplir l'objet
                        const inputObj = document.querySelector('#mat-input-0') || document.querySelector('input[matinput]');
                        if (inputObj) {{
                            inputObj.value = val;
                            inputObj.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}

                        // 2. Forcer une date de début large (ex: 01/01/2026) pour ne rien rater
                        const dateInputs = document.querySelectorAll('input[type="text"]');
                        // On cherche souvent les champs de date par leur label ou ordre
                        // Pour être sûr, on vide les filtres de date s'ils existent
                    }}, word, today)

                # Clic sur Rechercher
                await page.locator("button.mat-primary").filter(has_text="Rechercher").click()
                
                # ATTENTE CRUCIALE : On attend que le loader disparaisse ou que la table change
                print("⏳ Attente du rafraîchissement des résultats...")
                await page.wait_for_timeout(15000) 
                
                # On vérifie si on a des lignes dans la table
                rows = await page.locator("tr.mat-row").all()
                print(f"📊 Résultats trouvés dans le DOM : {len(rows)}")
                
                if len(rows) == 0:
                    # Tentative de secours : faire défiler la page pour forcer le lazy loading
                    await page.mouse.wheel(0, 500)
                    await page.wait_for_timeout(2000)
                    rows = await page.locator("tr.mat-row").all()

                for row in rows:
                    cells = await row.locator("td.mat-cell").all()
                    if len(cells) >= 5:
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()

                        print(f"✨ Pépite trouvée : {titre[:50]}...")
                        supabase.table("offres").insert({
                            "titre": titre, "organisme": org,
                            "date_expiration": date, "secteur": "TUNEPS"
                        }).execute()
                
                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
