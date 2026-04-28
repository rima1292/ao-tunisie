import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

keywords = ["musique", "audiovisuel", "sonorisation"]

async def scrape_tuneps():
    async with async_playwright() as p:
        # On simule un vrai navigateur Windows pour éviter le blocage pare-feu
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            }
        )
        page = await context.new_page()
        
        try:
            print("🌐 Tentative d'accès furtif à TUNEPS...")
            # On utilise 'domcontentloaded' au lieu de 'networkidle' car le réseau peut être bridé
            response = await page.goto("https://www.tuneps.tn/search", wait_until="domcontentloaded", timeout=60000)
            
            if response.status != 200:
                print(f"⚠️ Le site répond avec un code {response.status}. Blocage probable.")

            for word in keywords:
                print(f"🔍 Recherche active : {word}")
                
                # Injection directe via JS pour gagner du temps
                await page.evaluate(f"""
                    (val) => {{
                        const input = document.querySelector('input[matinput]') || document.querySelector('#mat-input-0');
                        if (input) {{
                            input.value = val;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                        const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Rechercher'));
                        if (btn) btn.click();
                    }}
                """, word)
                
                await page.wait_for_timeout(10000)

                rows = await page.locator("tr.mat-row").all()
                found = 0
                for row in rows:
                    cells = await row.locator("td.mat-cell").all()
                    if len(cells) >= 5:
                        titre = (await cells[3].inner_text()).strip()
                        if "aucun" not in titre.lower():
                            supabase.table("offres").insert({
                                "titre": titre, 
                                "organisme": (await cells[1].inner_text()).strip(),
                                "date_expiration": (await cells[4].inner_text()).strip(), 
                                "secteur": "TUNEPS"
                            }).execute()
                            found += 1
                print(f"✅ {found} offres pour {word}")

        except Exception as e:
            print(f"❌ Erreur réseau/structure : {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tuneps())
