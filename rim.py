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
            
            # On attend que le composant de filtre soit chargé (vu dans ton HTML)
            await page.wait_for_selector("app-offers-filtre", timeout=30000)

            for word in keywords:
                print(f"🔍 Recherche de la pépite : {word}")
                
                # Selon ton HTML, on cherche l'input qui est lié au label "Objet A.O"
                # On utilise une approche par 'placeholder' ou 'label'
                input_field = page.locator("mat-form-field").filter(has_text="Objet A.O").locator("input")
                
                # On s'assure qu'il est visible et on force l'écriture
                await input_field.click(click_count=3)
                await page.keyboard.press("Backspace")
                await input_field.type(word, delay=100)
                
                # Clic sur le bouton Rechercher bleu (background-color: #3498db dans ton HTML)
                search_btn = page.locator("button.mat-flat-button.mat-primary").filter(has_text="Rechercher")
                await search_btn.click()
                
                # Attente du tableau de résultats
                await page.wait_for_timeout(7000)
                
                # Extraction basée sur tes balises 'mat-row' et 'mat-cell'
                rows = await page.locator("tr.mat-row").all()
                print(f"✅ {len(rows)} offres trouvées.")
                
                for row in rows:
                    cells = await row.locator("td.mat-cell").all()
                    if len(cells) >= 5:
                        # Colonne 1: Organisme, Colonne 3: Titre, Colonne 4: Date (selon ton HTML)
                        organisme = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date_exp = (await cells[4].inner_text()).strip()

                        supabase.table("offres").insert({
                            "titre": titre,
                            "organisme": organisme,
                            "date_expiration": date_exp,
                            "secteur": "TUNEPS"
                        }).execute()
                
                # On nettoie la recherche pour le mot suivant
                reset_btn = page.locator("button").filter(has_text="Réinitialiser")
                if await reset_btn.is_visible():
                    await reset_btn.click()
                    await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"❌ Erreur : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
