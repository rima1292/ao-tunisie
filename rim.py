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
                
                # Étape 1 : Injection du texte
                await page.evaluate(f"""
                    (val) => {{
                        const input = document.querySelector('#mat-input-0') || document.querySelector('input[matinput]');
                        if (input) {{
                            input.value = val;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """, word)
                
                # Étape 2 : Clic sur Rechercher
                search_btn = page.locator("button.mat-primary").filter(has_text="Rechercher")
                await search_btn.click()
                
                # Étape 3 : Attendre que le loader disparaisse (ton idée !)
                # On attend que la table soit visible ou qu'un certain délai de stabilité passe
                print("⏳ Attente de la mise à jour du tableau...")
                await page.wait_for_timeout(15000) 

                # Étape 4 : Extraction des lignes
                rows = await page.locator("tr.mat-row").all()
                print(f"✅ {len(rows)} offres détectées pour {word}")
                
                for row in rows:
                    try:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            # On évite d'insérer si c'est le message "aucun résultat"
                            if "aucun" in titre.lower():
                                continue

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()
                    except:
                        continue
                
                # Reset pour le prochain mot
                await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
