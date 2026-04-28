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
        # On lance un vrai navigateur pour mieux gérer les scripts complexes
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("🌐 Connexion à TUNEPS...")
            await page.goto("https://www.tuneps.tn/search", wait_until="load", timeout=90000)
            
            # Attente très longue pour GitHub Actions
            await page.wait_for_timeout(20000)

            for word in keywords:
                print(f"🚀 Scan profond pour : {word}")
                
                # JavaScript avancé pour trouver l'input par son label
                success = await page.evaluate(f"""
                    (val) => {{
                        const labels = Array.from(document.querySelectorAll('label, mat-label'));
                        const targetLabel = labels.find(l => l.innerText.includes('Objet A.O'));
                        
                        if (targetLabel) {{
                            const inputId = targetLabel.getAttribute('for') || 'mat-input-0';
                            const input = document.getElementById(inputId) || document.querySelector('input[matinput]');
                            
                            if (input) {{
                                input.disabled = false;
                                input.readOnly = false;
                                input.value = val;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """, word)

                if success:
                    # Clic sur Rechercher
                    await page.locator("button.mat-primary").filter(has_text="Rechercher").click()
                    await page.wait_for_timeout(10000)
                    
                    rows = await page.locator("tr.mat-row").all()
                    print(f"✅ {len(rows)} offres trouvées.")
                    
                    for row in rows:
                        cells = await row.locator("td.mat-cell").all()
                        if len(cells) >= 5:
                            org = (await cells[1].inner_text()).strip()
                            titre = (await cells[3].inner_text()).strip()
                            date = (await cells[4].inner_text()).strip()

                            supabase.table("offres").insert({
                                "titre": titre, "organisme": org,
                                "date_expiration": date, "secteur": "TUNEPS"
                            }).execute()
                else:
                    print(f"⚠️ Impossible de localiser le champ pour '{word}'")

                await page.reload()
                await page.wait_for_timeout(5000)

        except Exception as e:
            print(f"❌ Erreur critique : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
