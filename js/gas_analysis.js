// Analyses de la page Gaz
const MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

window.addEventListener("load", () => {
    fetch("data/gas_analysis.json")
        .then(r => r.json())
        .then(d => dessinerSaisonnalite(d.ttf.saisonnalite))
        .catch(e => console.error("Analyse gaz :", e));
});

function dessinerSaisonnalite(s) {
    // Une ligne grise par année, une ligne verte épaisse pour la médiane
    const annees = Object.entries(s.annees).map(([annee, valeurs]) => ({
        label: annee, data: valeurs,
        borderColor: "rgba(111,122,115,0.35)", borderWidth: 1.2, pointRadius: 0, tension: 0.3,
    }));
    const mediane = {
        label: "Médiane des années", data: s.mediane,
        borderColor: "#12B981", borderWidth: 3.5, pointRadius: 3, tension: 0.3,
    };

    new Chart(document.getElementById("graphique-saison-gaz"), {
        type: "line",
        data: { labels: MOIS, datasets: [...annees, mediane] },
        options: {
            interaction: { mode: "nearest", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: c => ` ${c.dataset.label} : ${c.parsed.y.toFixed(0)}` } },
            },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "#eee9dd" }, title: { display: true, text: "Indice (100 = moyenne)" } },
            },
        },
    });

    // Statistiques tirées de la médiane
    const m = s.mediane;
    const haut = m.indexOf(Math.max(...m)), bas = m.indexOf(Math.min(...m));
    document.getElementById("stats-saison-gaz").innerHTML = `
        <dt>Mois le plus cher (médiane)</dt><dd>${MOIS[haut]} · ${m[haut]}</dd>
        <dt>Mois le moins cher (médiane)</dt><dd>${MOIS[bas]} · ${m[bas]}</dd>
        <dt>Écart haut / bas</dt><dd>${(m[haut] - m[bas]).toFixed(0)} points</dd>
        <dt>Années analysées</dt><dd>${Object.keys(s.annees).length}</dd>`;
    document.getElementById("lecture-saison-gaz").textContent =
        "Chaque ligne grise est une année complète ; la ligne verte est la médiane. Un indice de 110 signifie que le mois est 10 % plus cher que la moyenne de son année. La forme varie d'une année à l'autre (2021 et 2022 sont atypiques) : la saisonnalité est une tendance, pas une règle.";
}