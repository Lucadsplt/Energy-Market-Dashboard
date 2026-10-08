// Tous les graphes du dashboard : un seul fichier, un seul style.

const COULEURS = {
    vert: "#12B981",
    bleu: "#3b6fb6",
    ambre: "#e8a317",
    rouge: "#e03131",
    gris: "#6b7683",
};

Chart.defaults.maintainAspectRatio = false;
Chart.defaults.font.family = '"DM Sans", system-ui, sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = "#6b7683";

// Graphes déjà créés, pour pouvoir filtrer la période sans les reconstruire
const graphes = [];   // { chart, dates, series: [tableaux complets] }
let plageJours = 0;   // 0 = tout

function ajouterAlpha(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

function tranche(tableau, jours) {
    return jours > 0 ? tableau.slice(-jours) : tableau;
}

function appliquerPlage(entree) {
    const { chart, dates, series, dailyOnly } = entree;
    const jours = dailyOnly ? plageJours : 0;
    chart.data.labels = tranche(dates, jours);
    chart.data.datasets.forEach((ds, i) => { ds.data = tranche(series[i], jours); });
    chart.update("none");
}

// Graphe en courbes complet (axes, légende, infobulle)
function creerGraphe(canvasId, donnees, courbes, { dailyOnly = true, escalier = false } = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const doubleAxe = courbes.some(c => c.axe === "y2");

    const chart = new Chart(canvas, {
        type: "line",
        data: {
            labels: donnees.dates,
            datasets: courbes.map(c => ({
                label: c.label,
                data: donnees.series[c.cle],
                yAxisID: c.axe || "y",
                borderColor: c.couleur,
                backgroundColor: ajouterAlpha(c.couleur, 0.10),
                fill: !!c.remplir,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: escalier ? 0 : 0.25,
                stepped: escalier,
                spanGaps: true,
            })),
        },
        options: {
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true } },
                tooltip: {
                    backgroundColor: "#0F2A22",
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label} : ${ctx.parsed.y?.toFixed(2)}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: "#eef1f4" },
                    ticks: { maxTicksLimit: 7, maxRotation: 0 },
                },
                y: {
                    position: "left",
                    grid: { color: "#eef1f4" },
                    title: { display: !!courbes[0].unite, text: courbes[0].unite },
                },
                ...(doubleAxe ? {
                    y2: {
                        position: "right",
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: courbes.find(c => c.axe === "y2").unite },
                    },
                } : {}),
            },
        },
    });

    const entree = { chart, dates: donnees.dates, series: courbes.map(c => donnees.series[c.cle]), dailyOnly };
    graphes.push(entree);
    appliquerPlage(entree);
    return chart;
}

// Mini-courbe sans axes pour les cartes KPI
function creerSparkline(canvasId, dates, valeurs, couleur) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    new Chart(canvas, {
        type: "line",
        data: {
            labels: dates,
            datasets: [{
                data: valeurs,
                borderColor: couleur,
                backgroundColor: ajouterAlpha(couleur, 0.12),
                fill: true,
                borderWidth: 1.8,
                pointRadius: 0,
                tension: 0.3,
                spanGaps: true,
            }],
        },
        options: {
            events: [],
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
            scales: { x: { display: false }, y: { display: false } },
            layout: { padding: 0 },
        },
    });
}

// --- KPI ---
function dernierEtVariation(valeurs) {
    const propres = valeurs.filter(v => v !== null);
    const dernier = propres[propres.length - 1];
    const precedent = propres[propres.length - 2];
    return { dernier, variation: precedent !== undefined ? dernier - precedent : null };
}

function afficherKpi(id, valeurs, { variation = true } = {}) {
    const { dernier, variation: v } = dernierEtVariation(valeurs);
    document.getElementById(id).textContent = dernier.toFixed(1);
    if (!variation || v === null) return;
    const el = document.getElementById(id + "-var");
    el.textContent = (v >= 0 ? "▲ +" : "▼ ") + v.toFixed(1);
    el.classList.add(v >= 0 ? "up" : "down");
}

function afficherMaj(id, dates) {
    const el = document.getElementById(id);
    if (el) el.textContent = "dernière donnée du " + dates[dates.length - 1].slice(0, 10);
}

function charger(nom) {
    return fetch(`data/${nom}.json`).then(r => r.json());
}

window.addEventListener("load", () => {
    const { vert, bleu, ambre, gris } = COULEURS;

    charger("oil").then(d => {
        afficherKpi("kpi-brent", d.series.brent);
        afficherKpi("kpi-spread-oil", d.series.spread, { variation: false });
        creerSparkline("spark-brent", d.dates, d.series.brent, vert);
        creerSparkline("spark-spread-oil", d.dates, d.series.spread, gris);
        afficherMaj("maj-oil", d.dates);

        const prix = [
            { cle: "brent", label: "Brent", couleur: vert, unite: "$/baril" },
            { cle: "wti", label: "WTI", couleur: bleu },
        ];
        creerGraphe("synth-petrole", d, prix);
        creerGraphe("graphique-petrole", d, prix);
        creerGraphe("graphique-spread", d, [
            { cle: "spread", label: "Écart Brent − WTI", couleur: ambre, unite: "$/baril", remplir: true },
        ]);
    }).catch(e => console.error("Pétrole :", e));

    charger("gas").then(d => {
        afficherKpi("kpi-ttf", d.series.ttf);
        afficherKpi("kpi-vol-ttf", d.series.ttf_vol, { variation: false });
        creerSparkline("spark-ttf", d.dates, d.series.ttf, vert);
        creerSparkline("spark-vol", d.dates, d.series.ttf_vol, ambre);
        afficherMaj("maj-gas", d.dates);

        const prix = [
            { cle: "ttf", label: "TTF (€/MWh)", couleur: vert, unite: "TTF (€/MWh)" },
            { cle: "henry_hub", label: "Henry Hub ($/MMBtu)", couleur: bleu, axe: "y2", unite: "Henry Hub ($/MMBtu)" },
        ];
        creerGraphe("synth-gaz", d, prix);
        creerGraphe("graphique-gaz", d, prix);
        creerGraphe("graphique-gaz-vol", d, [
            { cle: "ttf_vol", label: "TTF", couleur: vert, unite: "%" },
            { cle: "henry_hub_vol", label: "Henry Hub", couleur: bleu },
        ]);
    }).catch(e => console.error("Gaz :", e));

    charger("electricity").then(d => {
        afficherKpi("kpi-elec-fr", d.series.fr);
        afficherKpi("kpi-spread-elec", d.series.spread_fr_de, { variation: false });
        creerSparkline("spark-elec", d.dates, d.series.fr, vert);
        creerSparkline("spark-spread-elec", d.dates, d.series.spread_fr_de, gris);

        creerGraphe("graphique-electricite", d, [
            { cle: "fr", label: "France", couleur: vert, unite: "€/MWh" },
            { cle: "de_lu", label: "Allemagne-Luxembourg", couleur: bleu },
        ], { dailyOnly: false, escalier: true });
        creerGraphe("graphique-elec-spread", d, [
            { cle: "spread_fr_de", label: "Écart France − Allemagne", couleur: ambre, unite: "€/MWh", remplir: true },
        ], { dailyOnly: false, escalier: true });
    }).catch(e => console.error("Électricité :", e));

    // Sélecteur de période (30 jours / tout)
    document.querySelectorAll("#plage .segment-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#plage .segment-btn").forEach(b => b.classList.remove("actif"));
            btn.classList.add("actif");
            plageJours = parseInt(btn.dataset.jours, 10);
            graphes.forEach(appliquerPlage);
        });
    });
});
