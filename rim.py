
import os
import asyncio
from supabase import create_client
from playwright.async_api import async_playwright

# GitHub Actions récupérera ces valeurs dans tes "Secrets"
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

async def run_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Le site cible que tu as choisi
        await page.goto("https://www.appeloffres.net/appels-offres")
        
        # Tes mots-clés bilingues
        keywords = ["musique", "audio", "photo", "سمعية بصرية"]
        
        # Logique de détection des offres
        offres_elements = await page.query_selector_all(".post-column")
        for el in offres_elements:
            text = await el.inner_text()
            if any(word in text.lower() for word in keywords):
                title_el = await el.query_selector("h2")
                title = await title_el.inner_text() if title_el else "Nouvelle Offre"
                
                # Insertion dans ta table Supabase
                supabase.table("offres").insert({
                    "titre": title.strip(),
                    "organisme": "Automatique GitHub",
                    "secteur": "Audio & Musique"
                }).execute()
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())
