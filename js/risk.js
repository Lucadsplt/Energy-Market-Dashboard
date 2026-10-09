// Page Petrole : cone de projection Monte Carlo du Brent (données calculées par le pipeline Python)
window.addEventListener("load", () => {
    fetch("data/risk.json")
        .then(r => r.json())
        .then(d => dessinerRisque(d.brent))
        .catch(e => console.error("Risque :", e));
});

function dessinerRisque(b) {
    const hist = b.historique, fut = b.futur;
    const nH = hist.dates.length;
    const labels = hist.dates.concat(fut.dates);

    // Une bande commence au dernier prix connu, puis suit les percentiles simulés
    const bande = cle => {
        const vide = new Array(nH - 1).fill(null);
        return vide.concat([b.dernier_prix], fut[cle]);
    };
    const historique = hist.prix.concat(new Array(fut.dates.length).fill(null));

    const vert = "#12B981";
    const sansLigne = { borderWidth: 0, pointRadius: 0 };

    new Chart(document.getElementById("graphique-risque"), {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "5 %", data: bande("p5"), ...sansLigne },
                { label: "90 % des cas", data: bande("p95"), ...sansLigne, fill: "-1", backgroundColor: "rgba(18,185,129,0.12)" },
                { label: "25 %", data: bande("p25"), ...sansLigne },
                { label: "50 % des cas", data: bande("p75"), ...sansLigne, fill: "-1", backgroundColor: "rgba(18,185,129,0.25)" },
                { label: "Médiane simulée", data: bande("p50"), borderColor: vert, borderDash: [6, 4], borderWidth: 2, pointRadius: 0 },
                { label: "Historique", data: historique, borderColor: "#0F2A22", borderWidth: 2, pointRadius: 0 },
            ],
        },
        options: {
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { usePointStyle: true, boxWidth: 10, filter: i => !["5 %", "25 %"].includes(i.text) },
                },
                tooltip: {
                    backgroundColor: "#0F2A22", padding: 10, cornerRadius: 8,
                    filter: i => !["5 %", "25 %"].includes(i.dataset.label) && i.parsed.y !== null,
                    callbacks: { label: c => ` ${c.dataset.label} : ${c.parsed.y.toFixed(1)} $` },
                },
            },
            scales: {
                x: { grid: { color: "#eef1f4" }, ticks: { maxTicksLimit: 8, maxRotation: 0 } },
                y: { grid: { color: "#eef1f4" }, title: { display: true, text: "$/baril" } },
            },
        },
    });

    // Paramètres du modèle
    const p = b.parametres;
    document.getElementById("stats-risque").innerHTML = `
        <dt>Dernier prix</dt><dd>${b.dernier_prix.toFixed(1)} $/baril</dd>
        <dt>Prix d'équilibre estimé</dt><dd>${p.mu_prix.toFixed(1)} $/baril</dd>
        <dt>Retour à l'équilibre (demi-vie)</dt><dd>${Math.round(Math.LN2 / p.kappa)} jours ouvrés</dd>
        <dt>Volatilité annualisée</dt><dd>${(p.sigma_quotidien * Math.sqrt(252) * 100).toFixed(0)} %</dd>`;
    document.getElementById("risk-sous-titre").textContent = `horizon de ${b.horizon_jours} jours ouvrés`;
}
