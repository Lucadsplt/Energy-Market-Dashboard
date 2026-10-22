// Onglet Stratégies : règles de trading testées sur le pétrole et le gaz (résultats produits par le pipeline)
(() => {
    const NOMS_VERDICT = {
        demontre: ["demontre", "Démontré"],
        non_demontre: ["non-demontre", "Non démontré"],
        artefact: ["artefact", "Probable artefact"],
    };

    // Textes propres à chaque marché : le reste de la page est commun
    const MARCHES = {
        petrole: {
            fichier: "data/strategies.json",
            intro: "Quatre règles de trading classiques testées sur le pétrole depuis 2000, avec des garde-fous pour ne pas se laisser tromper par un bon résultat passé.",
            avertissement: "<b>Outil d'étude, pas un conseil en investissement.</b> Ces règles sont des hypothèses testées sur des prix passés. Un résultat passé ne garantit rien, et les prix utilisés (spot) ne sont pas directement négociables.",
            reference: "Acheter et garder le Brent",
            donnees: "Données : prix spot du Brent et du WTI (FRED), positions des fonds spéculatifs (rapports COT de la CFTC).",
            limites: [
                "Les prix sont des <b>prix spot</b> (FRED), qui ne se négocient pas directement : un vrai trader passerait par des contrats à terme, avec leur roulement et leurs frais propres.",
                "Le <b>Brent et le WTI spot</b> ne sont pas relevés à la même heure, ce qui fausse les règles fondées sur leur écart.",
                "Les <b>positions des fonds (COT)</b> sont hebdomadaires et publiées avec trois jours de décalage.",
                "Quatre règles seulement ont été testées. Ne pas en trouver de démontrée n'est pas un échec : c'est un résultat attendu sur des marchés très suivis.",
                "Un backtest ne remplace pas un <b>suivi en conditions réelles</b>, que l'on peut faire dans un simulateur de trading.",
            ],
        },
        gaz: {
            fichier: "data/strategies_gaz.json",
            intro: "Quatre règles testées sur le gaz (Henry Hub, TTF, JKM), avec les mêmes garde-fous que pour le pétrole.",
            avertissement: "<b>Outil d'étude, pas un conseil en investissement.</b> Ces règles sont des hypothèses testées sur des prix passés. Un résultat passé ne garantit rien, et les séries utilisées sont des contrats à terme « continus » qui ne se négocient pas tels quels.",
            reference: "Acheter et garder le Henry Hub",
            donnees: "Données : contrats à terme continus Henry Hub (NG=F), TTF (TTF=F), JKM (JKM=F) et taux EUR/USD (Yahoo Finance).",
            limites: [
                "Les prix sont des <b>contrats à terme continus</b> non ajustés : à chaque changement de contrat, la série saute. Ces sauts contaminent les gains des règles sur le Henry Hub, qui sont donc à lire avec prudence.",
                "Le <b>TTF, le Henry Hub et le JKM</b> ne sont pas relevés à la même heure (Europe, États-Unis, Asie). Les règles sur un écart sont exposées à un artefact de mesure, d'où le test de retard d'exécution.",
                "Le <b>JKM</b> est peu liquide et ses prix sont parfois figés, ce qui peut fabriquer un faux retour à la moyenne.",
                "L'historique du <b>TTF ne commence qu'en 2017</b> : les règles sur écarts sont comparées avant et après 2022 (crise gazière), sur peu d'années.",
                "Une règle proche du seuil, comme l'écart JKM − TTF, reste <b>fragile</b> : un simple changement de convention de calcul suffit à déplacer sa probabilité de hasard.",
                "Un backtest ne remplace pas un <b>suivi en conditions réelles</b>, que l'on peut faire dans un simulateur de trading.",
            ],
        },
    };

    const fr = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
    const signe = (x, d = 2) => (x > 0 ? "+" : x < 0 ? "−" : "") + fr(Math.abs(x), d);
    const badge = cle => `<span class="badge ${NOMS_VERDICT[cle][0]}">${NOMS_VERDICT[cle][1]}</span>`;

    const resultats = {};          // données chargées, par marché
    let marche = "petrole";
    let donnees = null;
    let grapheCourbe = null, grapheRetard = null;

    // ---------------------------------------------------------------- synthèse
    function dessinerSynthese(d) {
        document.getElementById("strat-periode").textContent = `${d.meta.periode.replace("→", "à")}, coûts de ${fr(d.meta.cout_pb_par_jambe, 0)} points de base par jambe`;

        const lignes = d.signaux.map(s => `<tr class="cliquable" data-cle="${s.cle}">
            <td><b>${s.nom}</b><span class="sous-ligne">${s.actif}</span></td>
            <td>${signe(s.metriques.annualise_pct, 1)} %</td>
            <td>${signe(s.metriques_sans_retard.sharpe)}</td>
            <td><b>${signe(s.metriques.sharpe)}</b></td>
            <td>${fr(s.p_valeur, 3)}</td>
            <td>${badge(s.verdict)}</td>
            <td class="etat">${s.etat.libelle}</td></tr>`).join("");

        const r = d.reference;
        const reference = `<tr class="reference"><td><b>${MARCHES[marche].reference}</b><span class="sous-ligne">pour comparaison</span></td>
            <td>${signe(r.annualise_pct, 1)} %</td><td>${signe(r.sharpe)}</td><td>${signe(r.sharpe)}</td><td>${fr(r.p_valeur, 3)}</td><td></td><td class="etat">Position permanente</td></tr>`;

        document.getElementById("table-strat").innerHTML =
            `<tr><th>Règle</th><th>Rendement annuel</th><th>Sharpe sans retard</th><th>Sharpe à 1 jour de retard</th><th>Probabilité de hasard</th><th>Verdict</th><th>Position théorique actuelle</th></tr>${lignes}${reference}`;

        document.querySelectorAll("#table-strat tr.cliquable").forEach(tr => tr.addEventListener("click", () => {
            document.getElementById("strat-choix").value = tr.dataset.cle;
            document.querySelector('#strategies [data-volet="detail"]').click();
            afficherDetail(tr.dataset.cle);
        }));

        const nb = { demontre: 0, non_demontre: 0, artefact: 0 };
        d.signaux.forEach(s => { nb[s.verdict] += 1; });
        document.getElementById("lecture-strat").innerHTML =
            `<b>${d.signaux.length} règles testées : ${nb.demontre} démontrée${nb.demontre > 1 ? "s" : ""}, ${nb.artefact} probable${nb.artefact > 1 ? "s" : ""} artefact${nb.artefact > 1 ? "s" : ""}, ${nb.non_demontre} non démontrée${nb.non_demontre > 1 ? "s" : ""}.</b> ` +
            `Le Sharpe mesure le rendement par unité de risque (au-dessus de 0,5 c'est intéressant, au-dessus de 1 c'est rare). ` +
            `La probabilité de hasard est celle d'obtenir un résultat aussi bon sans aucun talent ; comme ${d.meta.nb_tests} règles ont été essayées, le seuil est ramené à ${fr(d.meta.seuil_corrige, 4)}. ` +
            `Cliquez sur une règle pour voir son détail.`;
    }

    // ---------------------------------------------------------------- détail d'une règle
    function remplirChoix(d) {
        const menu = document.getElementById("strat-choix");
        menu.innerHTML = "";
        d.signaux.forEach(s => menu.add(new Option(s.nom, s.cle)));
    }

    function afficherDetail(cle) {
        const s = donnees.signaux.find(x => x.cle === cle);
        const m = s.metriques;
        document.getElementById("strat-regle").textContent = `${s.regle} Actif : ${s.actif}.`;

        // courbe de performance (échelle logarithmique : un placement qui perd 90 % reste lisible)
        const jeux = [{ label: s.nom + " (après coûts)", data: s.courbe.strategie, borderColor: "#1f4e79", borderWidth: 2, pointRadius: 0, tension: 0.1 }];
        if (s.courbe.reference) jeux.push({ label: "Acheter et garder", data: s.courbe.reference, borderColor: "#8a948e", borderWidth: 1.5, borderDash: [5, 4], pointRadius: 0, tension: 0.1 });
        if (grapheCourbe) grapheCourbe.destroy();
        grapheCourbe = new Chart(document.getElementById("graphique-strat-courbe"), {
            type: "line",
            data: { labels: s.courbe.dates, datasets: jeux },
            options: {
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } },
                scales: {
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0, callback: (v, i) => s.courbe.dates[i].slice(0, 4) } },
                    y: { type: "logarithmic", grid: { color: "#eee9dd" }, title: { display: true, text: "valeur d'un placement de 100" } },
                },
            },
        });

        // sensibilité au retard d'exécution
        if (grapheRetard) grapheRetard.destroy();
        grapheRetard = new Chart(document.getElementById("graphique-strat-retard"), {
            type: "bar",
            data: {
                labels: s.retard.map(r => r.jours === 0 ? "aucun retard" : r.jours + " jour" + (r.jours > 1 ? "s" : "")),
                datasets: [{ data: s.retard.map(r => r.sharpe), borderRadius: 3,
                    backgroundColor: s.retard.map(r => r.sharpe >= 0 ? "rgba(31,78,121,0.75)" : "rgba(192,57,43,0.75)") }],
            },
            options: {
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` Sharpe ${signe(c.parsed.y)}` } } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "#eee9dd" }, title: { display: true, text: "ratio de Sharpe" } } },
            },
        });

        document.getElementById("stats-strat").innerHTML = `
            <dt>Rendement annualisé</dt><dd>${signe(m.annualise_pct, 1)} %</dd>
            <dt>Volatilité annualisée</dt><dd>${fr(m.volatilite_pct, 1)} %</dd>
            <dt>Ratio de Sharpe (1 jour de retard)</dt><dd>${signe(m.sharpe)}</dd>
            <dt>Perte maximale depuis un sommet</dt><dd>${fr(m.max_drawdown_pct, 1)} %</dd>
            <dt>Nombre de changements de position</dt><dd>${m.trades}</dd>
            <dt>Part du temps en position</dt><dd>${m.jours_en_position_pct} %</dd>
            <dt>Probabilité de hasard</dt><dd>${fr(s.p_valeur, 3)}</dd>
            <dt>Sharpe ${s.sous_periodes[0].nom}</dt><dd>${signe(s.sous_periodes[0].sharpe)}</dd>
            <dt>Sharpe ${s.sous_periodes[1].nom}</dt><dd>${signe(s.sous_periodes[1].sharpe)}</dd>`;

        document.getElementById("strat-verdict-badge").innerHTML = badge(s.verdict);
        document.getElementById("strat-verdict").textContent = s.explication;
        document.getElementById("strat-etat").innerHTML =
            `<b>${s.etat.libelle}</b><br><span class="sous-ligne">depuis le ${s.etat.depuis.split("-").reverse().join("/")}</span>`;
    }

    // ---------------------------------------------------------------- changement de marché
    function choisirMarche(cle) {
        if (!resultats[cle]) return;
        marche = cle;
        donnees = resultats[cle];
        const t = MARCHES[cle];
        document.getElementById("strat-intro").textContent = t.intro;
        document.getElementById("strat-avertissement").innerHTML = t.avertissement;
        document.getElementById("strat-limites").innerHTML = t.limites.map(l => `<li>${l}</li>`).join("");
        document.getElementById("strat-donnees").textContent = t.donnees;
        dessinerSynthese(donnees);
        remplirChoix(donnees);
        afficherDetail(donnees.signaux[0].cle);
    }

    function charger(cle) {
        return fetch(MARCHES[cle].fichier, { cache: "no-cache" })
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(d => { resultats[cle] = d; })
            .catch(e => {
                console.error("Stratégies (" + cle + ") :", e);
                const option = document.querySelector(`#strat-marche option[value="${cle}"]`);
                if (option) option.remove();
            });
    }

    window.addEventListener("load", () => {
        Promise.all(Object.keys(MARCHES).map(charger)).then(() => {
            if (!resultats.petrole && !resultats.gaz) return;
            choisirMarche(resultats.petrole ? "petrole" : "gaz");
            document.getElementById("strat-marche").addEventListener("change", e => choisirMarche(e.target.value));
            document.getElementById("strat-choix").addEventListener("change", e => afficherDetail(e.target.value));
        });
    });
})();
