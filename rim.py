import os
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase (Utilise tes Secrets GitHub)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# 2. Tes Pépites (Mots-clés bilingues)
# On les traite un par un pour ne pas bloquer le filtre du site
keywords = ["audio", "musique", "photographie", "سمعية بصرية"]

async def scrape_appel_offres():
    async with async_playwright() as p:
        # Lancement du navigateur
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for word in keywords:
            print(f"🔍 Recherche en cours pour : {word}")
            
            # Accès au site (Adapté à la structure de recherche)
            await page.goto(f"https://www.appeloffres.net/recherche?q={word}")
            
            # Attendre que le tableau des offres apparaisse
            try:
                await page.wait_for_selector("tr.cursor-pointer", timeout=10000)
            except:
                print(f"⚠️ Aucune offre trouvée pour '{word}' aujourd'hui.")
                continue

            # On récupère toutes les lignes du tableau
            rows = await page.query_selector_all("tr.cursor-pointer")
            
            for row in rows:
                # Extraction basée sur tes colonnes <td>
                cells = await row.query_selector_all("td")
                
                if len(cells) >= 4:
                    # Titre (2ème colonne)
                    titre_raw = await cells[1].inner_text()
                    # Organisme (4ème colonne)
                    organisme_raw = await cells[3].inner_text()
                    # Date d'expiration (Dernière colonne)
                    expiration_raw = await cells[-1].inner_text()

                    # Nettoyage des données
                    titre = titre_raw.strip().replace("\n", " ")
                    organisme = organisme_raw.strip()
                    # On garde seulement la date (ex: 12/05/2026)
                    date_expiration = expiration_raw.strip().split("\n")[0]

                    # 3. Insertion dans ta table Supabase
                    try:
                        data, count = supabase.table("offres").insert({
                            "titre": titre,
                            "organisme": organisme,
                            "date_expiration": date_expiration,
                            "secteur": "Audiovisuel & Musique"
                        }).execute()
                        print(f"✅ Ajouté : {titre[:30]}...")
                    except Exception as e:
                        print(f"❌ Erreur insertion : {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_appel_offres())
