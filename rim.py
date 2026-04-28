# ... (début du script identique)

            for word in keywords:
                print(f"🔍 Recherche de : {word}")
                
                # Étape 1 : Injection propre
                await page.evaluate(f"""
                    (val) => {{
                        const input = document.querySelector('#mat-input-0') || document.querySelector('input[matinput]');
                        if (input) {{
                            input.value = val;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """, word)
                
                # Étape 2 : Clic sur le bouton de recherche
                # On utilise locator().click() pour que Playwright gère l'état 'cliquable'
                try:
                    search_btn = page.locator("button.mat-primary").filter(has_text="Rechercher")
                    await search_btn.click()
                    print("⏳ Clic effectué, attente des résultats...")
                except:
                    # Secours JavaScript si le bouton est récalcitrant
                    await page.evaluate("document.querySelector('button.mat-primary').click()")

                # Étape 3 : L'ASTUCE - Attendre que le tableau contienne des données
                # On attend soit qu'une ligne apparaisse, soit un timeout de 15s
                try:
                    # On attend qu'au moins un élément avec la classe 'mat-row' soit présent dans le DOM
                    await page.wait_for_selector("tr.mat-row", timeout=15000)
                except:
                    print(f"ℹ️ Aucune ligne 'mat-row' apparue pour {word} après 15s.")

                # Étape 4 : Lecture des résultats
                rows = await page.locator("tr.mat-row").all()
                print(f"✅ {len(rows)} offres détectées dans le tableau.")
                
                for row in rows:
                    # ... (logique d'extraction et insertion Supabase)
                    cells = await row.locator("td.mat-cell").all()
                    if len(cells) >= 5:
                        titre = (await cells[3].inner_text()).strip()
                        # Si le texte est "Aucun résultat trouvé", on ignore
                        if "aucun" in titre.lower():
                            continue
                        
                        # Ton extraction continue ici...
                
                # Étape 5 : Reset complet pour le mot suivant
                await page.goto("https://www.tuneps.tn/search", wait_until="networkidle")
                await page.wait_for_timeout(3000)
