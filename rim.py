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
        # On lance avec un User-Agent réel pour éviter d'être bloqué
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="networkidle")
            await page.wait_for_timeout(5000)

            for word in keywords:
                print(f"🔍 Tentative sur : {word}")
                
                # 1. On s'assure que le champ est là
                input_selector = "input[matinput], #mat-input-0"
                await page.wait_for_selector(input_selector, timeout=20000)
                
                # 2. On tape "comme un humain" pour activer les scripts Angular
                await page.click(input_selector)
                await page.fill(input_selector, "") # On vide
                await page.type(input_selector, word, delay=150) # On tape lentement
                
                # 3. LE CLIC FORCE (via JS)
                # On cherche tous les boutons et on clique sur celui qui contient "Rechercher"
                await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const target = btns.find(b => b.innerText.includes('Rechercher'));
                    if (target) {
                        target.scrollIntoView();
                        target.click();
                    }
                }""")
                
                print("⏳ Recherche lancée, attente des lignes...")
                
                # 4. On attend que la table se mette à jour
                # Au lieu d'attendre un sélecteur, on attend que le réseau se calme
                await page.wait_for_timeout(12000)

                # 5. Extraction
                rows = await page.locator("tr.mat-row").all()
                print(f"✅ {len(rows)} offres trouvées.")
                
                for row in rows:
                    cells = await row.locator("td.mat-cell").all()
                    if len(cells) >= 5:
                        org = (await cells[1].inner_text()).strip()
                        titre = (await cells[3].inner_text()).strip()
                        date = (await cells[4].inner_text()).strip()

                        if "aucun" not in titre.lower():
                            print(f"💾 Sauvegarde : {titre[:40]}...")
                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()

                # 6. Reset propre
                await page.goto("https://www.tuneps.tn/search")
                await page.wait_for_timeout(3000)

        except Exception as e:
            print(f"❌ Erreur détectée : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
