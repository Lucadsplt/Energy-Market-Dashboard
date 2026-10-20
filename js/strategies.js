// Onglet Stratégies : règles de trading testées sur le pétrole (résultats produits par le pipeline, data/strategies.json)
(() => {
    const NOMS_VERDICT = {
        demontre: ["demontre", "Démontré"],
        non_demontre: ["non-demontre", "Non démontré"],
        artefact: ["artefact", "Probable artefact"],
    };

    const fr = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
    const signe = (x, d = 2) => (x > 0 ? "+" : x < 0 ? "−" : "") + fr(Math.abs(x), d);
    const badge = cle => `<span class="badge ${NOMS_VERDICT[cle][0]}">${NOMS_VERDICT[cle][1]}</span>`;

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
        const reference = `<tr class="reference"><td><b>Acheter et garder le Brent</b><span class="sous-ligne">pour comparaison</span></td>
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
        d.signaux.forEach(s => menu.add(new Option(s.nom, s.cle)));
        menu.addEventListener("change", () => afficherDetail(menu.value));
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

    window.addEventListener("load", () => {
        fetch("data/strategies.json", { cache: "no-cache" })
            .then(r => r.json())
            .then(d => {
                donnees = d;
                dessinerSynthese(d);
                remplirChoix(d);
                afficherDetail(d.signaux[0].cle);
            })
            .catch(e => console.error("Stratégies :", e));
    });
})();
