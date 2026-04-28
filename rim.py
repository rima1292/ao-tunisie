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
            print("🌐 Connexion au portail TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded", timeout=60000)
            
            # Pause de sécurité pour laisser le temps au DOM de se stabiliser
            await page.wait_for_timeout(10000)

            for word in keywords:
                print(f"🚀 Injection forcée pour : {word}")
                
                # On utilise l'ID 'mat-input-0' que tu as extrait du HTML
                # On force la valeur et on lève les verrous Angular par JS
                try:
                    await page.evaluate(f"""
                        (val) => {{
                            const input = document.querySelector('#mat-input-0') || document.querySelector('input[matinput]');
                            if (input) {{
                                input.disabled = false; // On force l'activation
                                input.value = val;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    """, word)
                    
                    # On clique sur 'Rechercher' (ton bouton mat-primary)
                    await page.locator("button.mat-primary").filter(has_text="Rechercher").click()
                    
                    # Attente du tableau
                    await page.wait_for_timeout(8000)
                    
                    rows = await page.locator("tr.mat-row").all()
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            # Extraction selon la structure de ta vidéo
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()
                            
                except Exception as e:
                    print(f"⚠️ Erreur sur '{word}': {e}")
                
                # Reset pour le prochain mot
                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
