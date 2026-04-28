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
        # On ajoute des arguments pour contourner les protections sandbox
        browser = await p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS (Tentative avec contournement)...")
            # On augmente le timeout global
            await page.goto("https://www.tuneps.tn/search", wait_until="commit", timeout=90000)
            
            # DIAGNOSTIC : On attend 10s et on prend une photo pour comprendre pourquoi l'input est "invisible"
            await page.wait_for_timeout(10000)
            await page.screenshot(path="debug_tuneps.png")
            print("📸 Capture d'écran de diagnostic enregistrée sous 'debug_tuneps.png'")

            for word in keywords:
                print(f"🔍 Recherche de : {word}")
                
                # On cherche TOUS les inputs de la page si le ID spécifique échoue
                await page.evaluate(f"""
                    (val) => {{
                        const inputs = Array.from(document.querySelectorAll('input'));
                        // On cherche l'input qui a "Objet" dans son label ou son placeholder
                        const target = inputs.find(i => i.outerHTML.toLowerCase().includes('objet') || i.id.includes('input'));
                        if (target) {{
                            target.value = val;
                            target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        
                        const btns = Array.from(document.querySelectorAll('button'));
                        const searchBtn = btns.find(b => b.innerText.includes('Rechercher'));
                        if (searchBtn) searchBtn.click();
                    }}
                """, word)
                
                print("⏳ Attente des résultats...")
                await page.wait_for_timeout(15000)

                # Extraction avec sélecteurs larges
                rows = await page.locator("tr").all()
                valid_rows = 0
                
                for row in rows:
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        try:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            if len(titre) > 5 and "aucun" not in titre.lower():
                                supabase.table("offres").insert({
                                    "titre": titre, "organisme": org,
                                    "date_expiration": date, "secteur": "TUNEPS"
                                }).execute()
                                valid_rows += 1
                        except:
                            continue
                
                print(f"✅ {valid_rows} offres sauvegardées pour {word}")
                
                # Navigation forcée pour reset
                await page.goto("https://www.tuneps.tn/search", wait_until="commit")
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
            await page.screenshot(path="error_state.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
