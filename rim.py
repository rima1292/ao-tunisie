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
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle", timeout=60000)
            
            for word in keywords:
                print(f"🔍 Traitement de : {word}")
                
                # 1. On cible l'ID exact que tu as envoyé : mat-input-0
                # On attend que l'élément soit présent dans le DOM
                input_selector = "#mat-input-0"
                await page.wait_for_selector(input_selector, state="attached", timeout=20000)
                
                # 2. SOLUTION RADICALE : On utilise JavaScript pour forcer la valeur
                # Cela contourne le "ng-reflect-disabled=true"
                await page.evaluate(f"""
                    (selector, val) => {{
                        const el = document.querySelector(selector);
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """, input_selector, word)
                
                # 3. Clic sur le bouton de recherche
                # On utilise la classe 'mat-primary' de ton code précédent
                search_btn = page.locator("button.mat-primary").filter(has_text="Rechercher")
                await search_btn.click()
                
                # Attente des résultats
                await page.wait_for_timeout(5000)
                
                try:
                    await page.wait_for_selector("tr.mat-row", timeout=10000)
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # Insertion Supabase
                            supabase.table("offres").insert({
                                "titre": titre, "organisme": organisme,
                                "date_expiration": expiration, "secteur": "TUNEPS"
                            }).execute()
                            
                except Exception:
                    print(f"ℹ️ Pas de résultats pour '{word}'")
                
                await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
