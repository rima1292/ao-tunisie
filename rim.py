import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# ON TESTE UN SEUL MOT POUR ÉVITER LE TIMEOUT
keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        # Configuration robuste pour GitHub Actions
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Lancement du test unique pour : {keyword}")
            # On attend que le dom soit chargé, sans attendre les scripts externes (networkidle est trop risqué)
            await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded", timeout=60000)
            
            # 1. Localisation et Saisie
            input_selector = 'input[matinput], #mat-input-0'
            await page.wait_for_selector(input_selector, timeout=20000)
            
            await page.click(input_selector)
            await page.fill(input_selector, keyword)
            
            # Étape Cruciale : On simule une sortie du champ pour "réveiller" Angular
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(1000)
            
            # 2. Clic sur le bouton de recherche (via JS pour plus de fiabilité)
            print("🔘 Tentative de clic sur Rechercher...")
            await page.evaluate("""() => {
                const searchBtn = Array.from(document.querySelectorAll('button'))
                                       .find(b => b.innerText.includes('Rechercher'));
                if (searchBtn) {
                    searchBtn.click();
                }
            }""")
            
            # 3. Attente prolongée pour les résultats (on a de la marge avec un seul mot)
            print("⏳ Attente des résultats (15s)...")
            await page.wait_for_timeout(15000)

            # 4. Extraction
            rows = await page.locator("tr.mat-row").all()
            print(f"📊 Résultats : {len(rows)} offres trouvées.")
            
            for row in rows:
                cells = await row.locator("td.mat-cell").all()
                if len(cells) >= 5:
                    titre = (await cells[3].inner_text()).strip()
                    if "aucun" not in titre.lower():
                        org = (await cells[1].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()
                        
                        print(f"💾 Offre captée : {titre[:50]}")
                        supabase.table("offres").insert({
                            "titre": titre, "organisme": org,
                            "date_expiration": date, "secteur": "TUNEPS"
                        }).execute()

        except Exception as e:
            print(f"❌ Erreur lors du test unique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
