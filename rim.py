import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
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
            await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded", timeout=60000)
            
            # Attente longue pour que les scripts Angular se stabilisent sur GitHub
            await page.wait_for_timeout(15000)

            for word in keywords:
                print(f"🚀 Tentative d'injection pour : {word}")
                
                # JavaScript pour trouver l'input par sa classe plutôt que son ID dynamique
                # On force aussi la suppression de l'attribut disabled
                try:
                    await page.evaluate(f"""
                        (val) => {{
                            const input = document.querySelector('input.mat-input-element') || document.querySelector('input[matinput]');
                            if (input) {{
                                input.disabled = false;
                                input.readOnly = false;
                                input.value = val;
                                // On déclenche les événements pour qu'Angular détecte la saisie
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                            }}
                        }}
                    """, word)
                    
                    # On laisse un court instant pour que le bouton 'Rechercher' s'active
                    await page.wait_for_timeout(2000)
                    
                    # Clic sur le bouton de recherche
                    search_btn = page.locator("button.mat-primary").filter(has_text="Rechercher")
                    await search_btn.click()
                    
                    # Attente des résultats
                    await page.wait_for_timeout(10000)
                    
                    rows = await page.locator("tr.mat-row").all()
                    print(f"✅ {len(rows)} offres trouvées pour '{word}'.")
                    
                    for row in rows:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            # Insertion Supabase
                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()
                            
                except Exception as e:
                    print(f"⚠️ Erreur pour '{word}': {e}")
                
                # On recharge la page pour éviter les conflits d'état Angular
                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
