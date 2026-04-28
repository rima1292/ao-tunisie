import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["musique", "audiovisuel", "sonorisation"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Accès à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)

            for word in keywords:
                print(f"🔍 Traitement de : {word}")
                
                # Injection de la valeur et clic forcés par JavaScript pour éviter les Timeouts Playwright
                # Cette méthode ignore si le bouton est 'disabled' ou non
                await page.evaluate(f"""
                    (val) => {{
                        const input = document.querySelector('#mat-input-0') || document.querySelector('input[matinput]');
                        if (input) {{
                            input.value = val;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        
                        // Recherche du bouton Rechercher par son texte
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const searchBtn = buttons.find(b => b.innerText.includes('Rechercher'));
                        if (searchBtn) {{
                            searchBtn.click();
                        }}
                    }}
                """, word)
                
                # Attente plus longue pour le chargement des résultats sur GitHub
                await page.wait_for_timeout(12000)
                
                rows = await page.locator("tr.mat-row").all()
                print(f"✅ {len(rows)} offres trouvées.")
                
                for row in rows:
                    try:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()
                    except:
                        continue
                
                # Petit refresh pour le mot suivant
                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
