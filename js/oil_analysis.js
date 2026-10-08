// Analyses de la page Pétrole
window.addEventListener("load", () => {
    fetch("data/oil_analysis.json")
        .then(r => r.json())
        .then(d => dessinerDistribution(d.brent.distribution))
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