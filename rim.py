import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keyword = "musique"

async def scrape_tuneps():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"--- Connexion à TUNEPS ---")
            await page.goto("https://www.tuneps.tn/portail/offres", wait_until="networkidle", timeout=60000)
            
            await page.wait_for_selector('input', timeout=20000)
            await page.wait_for_timeout(3000)

            tous_les_inputs = page.locator('input')
            await tous_les_inputs.nth(1).click()
            await tous_les_inputs.nth(1).fill(keyword)
            
            await page.locator('button:has-text("Rechercher")').click()
            await page.wait_for_timeout(10000) 

            rows = await page.locator("tr").all()
            count = 0
            
            for row in rows:
                cells = await row.locator("td").all()
                
                if len(cells) >= 5:
                    # --- SECURITÉ INDEX ---
                    # On récupère le texte des deux premières cellules pour être sûr
                    cell0 = (await cells[0].inner_text()).strip()
                    cell1 = (await cells[1].inner_text()).strip()
                    
                    # Si la cellule 0 est vide (icône), le numéro est dans la cellule 1
                    # Sinon, c'est la cellule 0
                    num_ao = cell0 if len(cell0) > 2 else cell1
                    
                    # On vérifie si cette ligne est bien une offre (contient le mot clé)
                    ligne_complete = await row.inner_text()
                    
                    if keyword.lower() in ligne_complete.lower() and "Désolé" not in ligne_complete:
                        # Extraction des autres champs (on décale si num_ao était en index 1)
                        # On utilise des index fixes basés sur la structure standard
                        org = (await cells[1].inner_text()).strip()
                        date_pub = (await cells[2].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date_lim = (await cells[4].inner_text()).strip()
                        
                        # --- LOG DE DEBUG ---
                        print(f"--- TENTATIVE INSERTION ---")
                        print(f"NUMERO_AO trouvé : '{num_ao}'")
                        print(f"TITRE : '{titre[:30]}...'")

                        try:
                            data_to_insert = {
                                "numero_ao": str(num_ao), # Force en texte
                                "titre": str(titre),
                                "organisme": str(org),
                                "date_publication": str(date_pub),
                                "date_expiration": str(date_lim),
                                "secteur": "TUNEPS"
                            }
                            
                            supabase.table("offres").insert(data_to_insert).execute()
                            print(f"✅ Succès pour : {num_ao}")
                            count += 1
                        except Exception as e_db:
                            print(f"❌ Erreur Supabase : {e_db}")

            print(f"\nTerminé : {count} offres traitées.")

        except Exception as e:
            print(f"❌ Erreur Script : {e}")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
