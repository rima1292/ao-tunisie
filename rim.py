import os
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from supabase import create_client

# 1. Configuration Supabase (Utilise tes Secrets GitHub)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") # Assure-toi que le secret est bien nommé SUPABASE_KEY
supabase = create_client(url, key)

# 2. Tes Pépites (Mots-clés)
keywords = ["audio", "musique", "photographie", "سمعية بصرية"]

async def scrape_pépites():
    async with async_playwright() as p:
        # Lancement du navigateur
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # --- GESTION DES DATES DYNAMIQUES ---
        # On cherche les offres publiées depuis aujourd'hui (ou 7 jours en arrière pour sécurité)
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        # On définit une fin de publication lointaine pour ne rien filtrer
        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        
        print(f"📅 Scan lancé du {start_date} au {end_date}")

        for word in keywords:
            # 3. Utilisation de ta requête URL fonctionnelle
            target_url = f"https://www.appeloffres.net/appels-offres?keyword={word}&status=active&publicationStartDate={start_date}&publicationEndDate={end_date}"
            print(f"🔍 Recherche pour la pépite : {word}")
            
            try:
                await page.goto(target_url, wait_until="networkidle")
                
                # Attendre que le tableau apparaisse
                await page.wait_for_selector("tr.cursor-pointer", timeout=10000)
                rows = await page.query_selector_all("tr.cursor-pointer")
                print(f"✅ {len(rows)} offres trouvées pour '{word}'")
                
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 4:
                        # Extraction des colonnes (Titre, Organisme, Date)
                        titre = (await cells[1].inner_text()).strip().replace("\n", " ")
                        organisme = (await cells[3].inner_text()).strip()
                        # On récupère la date d'expiration (souvent dans la dernière colonne)
                        expiration = (await cells[-1].inner_text()).strip().split('\n')[0]

                        # 4. Insertion dans Supabase
                        try:
                            # Utilisation de la table 'offres'
                            supabase.table("offres").insert({
                                "titre": titre,
                                "organisme": organisme,
                                "date_expiration": expiration,
                                "secteur": "Audiovisuel"
                            }).execute()
                            print(f"💾 Sauvegardé : {titre[:40]}...")
                        except Exception as e:
                            # On ignore souvent les erreurs de doublons si tu as une contrainte UNIQUE
                            pass

            except Exception as e:
                print(f"ℹ️ Aucun résultat ou erreur pour '{word}' : {e}")
                continue

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_pépites())
