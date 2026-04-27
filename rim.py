import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Config Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["audiovisuel", "musique", "sonorisation", "studio"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # On utilise une version de Chrome plus stable pour les iFrames
        browser = await p.chromium.launch(headless=True)
        
        # On simule un écran standard et on ignore les erreurs HTTPS si besoin
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            for word in keywords:
                print(f"🚀 Tentative directe pour : {word}")
                
                # On force l'URL de recherche TUNEPS pour réinitialiser l'état Angular
                await page.goto("https://www.tuneps.tn/search", wait_until="load", timeout=60000)
                
                # On attend un peu que les scripts internes se chargent
                await page.wait_for_timeout(5000)
                
                # TECHNIQUE DE LA DERNIÈRE CHANCE : On cherche TOUS les inputs et on prend celui qui ressemble au champ 'Objet'
                try:
                    # On tape directement au clavier après avoir cliqué dans la zone centrale si l'input est timide
                    input_field = page.locator("input[ng-reflect-name='bidNmFr'], input[placeholder*='A.O']").first
                    
                    await input_field.click()
                    await page.keyboard.type(word, delay=100)
                    
                    # On clique sur le bouton bleu par ses classes CSS exactes fournies
                    await page.locator("button.mat-primary").filter(has_text="Rechercher").click()
                    
                    # On attend que le tableau apparaisse
                    await page.wait_for_selector("tr.mat-row", timeout=20000)
                    
                    rows = await page.locator("tr.mat-row").all()
                    print(f"✅ Succès ! {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            organisme = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            expiration = (await cells[4].inner_text()).strip()

                            # Insertion Supabase
                            supabase.table("offres").insert({
                                "titre": titre, "organisme": organisme,
                                "date_expiration": expiration, "secteur": "TUNEPS"
                            }).execute()
                            
                except Exception as e:
                    print(f"⚠️ Échec pour '{word}': l'élément n'a pas répondu.")
                    continue

        except Exception as e:
            print(f"❌ Erreur générale : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
