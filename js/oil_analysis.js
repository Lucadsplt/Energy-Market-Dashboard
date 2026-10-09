// Analyses de la page Pétrole
window.addEventListener("load", () => {
    fetch("data/oil_analysis.json")
        .then(r => r.json())
        .then(d => {
            dessinerDistribution(d.brent.distribution);
            dessinerMonteCarlo(d.brent.monte_carlo);
            dessinerBacktest(d.brent.backtest);
            dessinerZscore(d.ecart);
        })
        .catch(e => console.error("Analyse pétrole :", e));
});

function dessinerDistribution(dist) {
    new Chart(document.getElementById("graphique-distribution"), {
        data: {
            labels: dist.centres,
            datasets: [
                { type: "bar", label: "Observé", data: dist.densite,
                  backgroundColor: "rgba(18,185,129,0.55)", barPercentage: 1, categoryPercentage: 1 },
                { type: "line", label: "Loi normale", data: dist.normale,
                  borderColor: "#0F2A22", borderWidth: 2, pointRadius: 0, tension: 0.35 },
            ],
        },
        options: {
            plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 9, callback: (v, i) => dist.centres[i] + " %" } },
                y: { display: false },
            },
        },
    });

    const s = dist.stats;
    const lignes = [
        ["Écart-type quotidien", s.ecart_type + " %"],
        ["Pire jour", s.pire_jour + " %"],
        ["Meilleur jour", "+" + s.meilleur_jour + " %"],
        ["Asymétrie", s.asymetrie],
        ["Kurtosis en excès", s.kurtosis_exces],
        ["Jours à plus de 3 écarts-types", s.jours_extremes_pct + " % (loi normale : 0,27 %)"],
    ];
    document.getElementById("stats-distribution").innerHTML =
        lignes.map(([nom, val]) => `<dt>${nom}</dt><dd>${val}</dd>`).join("");

    const fois = (s.jours_extremes_pct / 0.27).toFixed(1);
    document.getElementById("lecture-distribution").textContent =
        `Sur ${s.nb_jours} jours, les mouvements extrêmes sont ${fois} fois plus fréquents que ne le prévoirait une loi normale : le risque est sous-estimé par un modèle gaussien.`;
}

function dessinerMonteCarlo(mc) {
    const g = mc.gaussien, q = mc.queues_epaisses;
    new Chart(document.getElementById("graphique-mc-final"), {
        data: {
            labels: g.histogramme.centres,
            datasets: [
                { type: "bar", label: "Chocs gaussiens", data: g.histogramme.pourcent,
                  backgroundColor: "rgba(18,185,129,0.5)", barPercentage: 1, categoryPercentage: 1 },
                { type: "line", label: "Chocs à queues épaisses", data: q.histogramme.pourcent,
                  borderColor: "#0F2A22", borderWidth: 2, pointRadius: 0, tension: 0.3 },
            ],
        },
        options: {
            plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 8, callback: (v, i) => g.histogramme.centres[i] + " $" } },
                y: { display: false },
            },
        },
    });

    document.getElementById("mc-sous-titre").textContent = `prix actuel ${mc.dernier_prix} $, horizon ${mc.horizon_jours} jours`;
    document.getElementById("stats-mc").innerHTML = `
        <dt>Médiane simulée</dt><dd>${g.mediane} $</dd>
        <dt>Perte maximale probable (VaR 95 %)</dt><dd>${g.var95} % · ${q.var95} %</dd>
        <dt>Perte moyenne pires cas (ES 95 %)</dt><dd>${g.es95} % · ${q.es95} %</dd>`;
    document.getElementById("table-proba").innerHTML =
        "<tr><th>Niveau atteint d'ici 30 jours</th><th>Gaussien</th><th>Queues épaisses</th></tr>" +
        g.probas.map((p, i) => {
            const nom = (p.variation > 0 ? "+" : "") + p.variation + " % (" + p.seuil + " $)";
            return `<tr><td>${nom}</td><td>${p.proba} %</td><td>${q.probas[i].proba} %</td></tr>`;
        }).join("");
    document.getElementById("lecture-mc").textContent =
        "Les valeurs de VaR et d'ES sont données au format gaussien · queues épaisses. La probabilité compte les scénarios qui touchent le niveau à un moment quelconque des 30 jours.";
}

function dessinerBacktest(lignes) {
    document.getElementById("table-backtest").innerHTML =
        "<tr><th>Calibration sur</th><th>Tests</th><th>Dépassements à la baisse</th><th>À la hausse</th><th>Valeur p (Kupiec)</th><th>Verdict</th></tr>" +
        lignes.map(l => `<tr>
            <td>${l.fenetre_ans} ans</td><td>${l.tests}</td>
            <td>${l.depassement_bas_pct} %</td><td>${l.depassement_haut_pct} %</td>
            <td>${l.p_kupiec}</td><td>${l.p_kupiec > 0.05 ? "Cohérent" : "Rejeté"}</td></tr>`).join("");
    document.getElementById("lecture-backtest").textContent =
        "Pour chaque date, le modèle est calibré uniquement sur le passé, puis comparé au rendement observé 30 jours plus tard. Si la VaR 95 % est bien calibrée, environ 5 % des cas la dépassent. Un test de Kupiec avec une valeur p supérieure à 0,05 signifie que l'écart à 5 % peut s'expliquer par le hasard.";
}

function dessinerZscore(e) {
    const seuil = valeur => e.dates.map(() => valeur);
    const trait = { pointRadius: 0, tension: 0.2 };

    new Chart(document.getElementById("graphique-zscore"), {
        type: "line",
        data: { labels: e.dates, datasets: [
            { label: "Seuil +2", data: seuil(2), ...trait, borderColor: "#d6453d", borderDash: [5, 4], borderWidth: 1 },
            { label: "Seuil −2", data: seuil(-2), ...trait, borderColor: "#d6453d", borderDash: [5, 4], borderWidth: 1 },
            { label: "Z-score", data: e.z, ...trait, borderColor: "#e8a317", borderWidth: 1.8 },
        ] },
        options: {
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 8, maxRotation: 0, callback: (v, i) => e.dates[i].slice(0, 4) } },
                y: { grid: { color: "#eee9dd" }, title: { display: true, text: "écarts-types" } },
            },
        },
    });

    const s = e.stats;
    const etat = Math.abs(s.z_actuel) > 3 ? "très inhabituel" : Math.abs(s.z_actuel) > 2 ? "inhabituel" : "normal";
    document.getElementById("stats-zscore").innerHTML = `
        <dt>Écart actuel / moyenne sur 1 an</dt><dd>${s.ecart_actuel} / ${s.moyenne_actuelle} $/baril</dd>
        <dt>Z-score actuel</dt><dd>${s.z_actuel} (${etat})</dd>
        <dt>Jours avec |z| &gt; 2</dt><dd>${s.jours_extremes_pct} % (loi normale : 5 %)</dd>`;
    document.getElementById("lecture-zscore").textContent =
        "Le z-score compare l'écart du jour à sa moyenne et à sa variabilité des 252 derniers jours de bourse : au-delà de ±2, l'écart sort de sa zone habituelle. Si la situation dure, la moyenne glissante s'y adapte et le z-score redescend de lui-même.";
}