import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "sonorisation", "studio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # On définit un écran large et un délai d'attente global plus long
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        page.set_default_timeout(30000)
        
        try:
            print("🌐 Navigation vers le portail de recherche...")
            # On utilise l'URL directe du formulaire pour gagner du temps
            await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded")
            
            for word in keywords:
                print(f"🔍 Tentative de saisie pour : {word}")
                
                # SÉCURITÉ : On cherche l'input qui est juste à côté du texte "Objet A.O"
                # C'est beaucoup plus fiable que 'ng-reflect'
                try:
                    # On attend que le formulaire soit là
                    await page.wait_for_selector("input", state="visible")
                    
                    # On cherche l'input par son placeholder ou son label proche
                    input_field = page.get_by_label("Objet A.O").first
                    if await input_field.count() == 0:
                        input_field = page.locator("input[ng-reflect-name='bidNmFr']").first
                    
                    await input_field.fill("") # On vide
                    await input_field.type(word, delay=100) # On tape doucement
                    
                    # Clic sur Rechercher
                    await page.get_by_role("button", name="Rechercher").click()
                    
                    # Attente de la mise à jour du tableau
                    await page.wait_for_timeout(5000)
                    
                    # Extraction des lignes
                    rows = await page.locator("tr.mat-row").all()
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # Insertion Supabase
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "TUNEPS"
                            }).execute()
                            
                except Exception as e:
                    print(f"⚠️ Erreur sur le mot '{word}': {e}")
                    continue

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
