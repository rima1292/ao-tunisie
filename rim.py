import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "sonorisation", "studio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # On utilise une version stable et on cache les traces de bot
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print("🌐 Accès au portail...")
            # On va sur la page et on attend 10 secondes qu'elle soit VRAIMENT chargée
            await page.goto("https://www.tuneps.tn/search", wait_until="load", timeout=60000)
            await page.wait_for_timeout(10000)

            for word in keywords:
                print(f"🚀 Action furtive pour : {word}")
                
                # 1. On tente de cliquer au milieu de l'écran pour activer la page
                await page.mouse.click(640, 400)
                
                # 2. On cherche l'input avec un sélecteur CSS minimaliste
                # Si ça échoue, on ne s'arrête pas, on essaie de tabuler
                try:
                    # On cherche TOUS les champs de saisie
                    inputs = await page.query_selector_all("input")
                    target_input = None
                    
                    for inp in inputs:
                        name = await inp.get_attribute("ng-reflect-name")
                        if name == "bidNmFr":
                            target_input = inp
                            break
                    
                    if target_input:
                        await target_input.click()
                        await page.keyboard.type(word, delay=150)
                    else:
                        # Plan B : On tabule 5 fois (souvent l'ordre des champs sur TUNEPS)
                        await page.keyboard.press("Tab")
                        await page.wait_for_timeout(500)
                        await page.keyboard.type(word, delay=100)
                    
                    # 3. Validation par la touche ENTRÉE (souvent plus fiable qu'un clic sur ce site)
                    await page.keyboard.press("Enter")
                    
                    # Attente du tableau
                    await page.wait_for_timeout(8000)
                    
                    rows = await page.query_selector_all("tr.mat-row")
                    print(f"✅ Résultats : {len(rows)} trouvés.")
                    
                    for row in rows:
                        cells = await row.query_selector_all("td.mat-cell")
                        if len(cells) >= 5:
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": organisme,
                                "date_expiration": expiration, "secteur": "TUNEPS"
                            }).execute()
                            print(f"💾 {organisme} enregistré.")

                except Exception as e:
                    print(f"⚠️ Mot '{word}' ignoré : {e}")
                    
                # On recharge la page pour le mot suivant pour éviter les bugs Angular
                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
