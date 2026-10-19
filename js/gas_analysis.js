// Analyses de la page Gaz
const MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];

window.addEventListener("load", () => {
    fetch("data/gas_analysis.json")
        .then(r => r.json())
        .then(d => {
            dessinerSaisonnalite(d.ttf.saisonnalite);
            dessinerEcart(d.ecart);
            if (d.gnl) dessinerGnl(d.gnl);
        })
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
        borderColor: "#1f4e79", borderWidth: 3.5, pointRadius: 3, tension: 0.3,
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

function dessinerEcart(e) {
    const axeX = {
        grid: { display: false },
        ticks: { maxTicksLimit: 8, maxRotation: 0, callback: (v, i) => e.dates[i].slice(0, 4) },
    };
    const ligne = (label, data, couleur, extra = {}) => ({
        label, data, borderColor: couleur, borderWidth: 1.8, pointRadius: 0, tension: 0.2, ...extra,
    });
    const options = {
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } },
        scales: { x: axeX, y: { grid: { color: "#eee9dd" } } },
    };

    new Chart(document.getElementById("graphique-ecart-prix"), {
        type: "line",
        data: { labels: e.dates, datasets: [
            ligne("TTF (Europe)", e.ttf, "#1f4e79"),
            ligne("Henry Hub (États-Unis)", e.hh_eur, "#c26a1a"),
        ] },
        options,
    });

    new Chart(document.getElementById("graphique-ecart"), {
        type: "line",
        data: { labels: e.dates, datasets: [
            ligne("Écart TTF − Henry Hub", e.ecart, "#b8861b",
                  { fill: true, backgroundColor: "rgba(184,134,27,0.15)" }),
        ] },
        options: { ...options, plugins: { legend: { display: false } } },
    });

    const s = e.stats;
    document.getElementById("stats-ecart").innerHTML = `
        <dt>Écart actuel</dt><dd>${s.actuel} €/MWh</dd>
        <dt>Médiane depuis 2017</dt><dd>${s.mediane} €/MWh</dd>
        <dt>Maximum</dt><dd>${s.maximum} €/MWh (${s.date_max})</dd>
        <dt>Minimum</dt><dd>${s.minimum} €/MWh (${s.date_min})</dd>
        <dt>Plus élevé que</dt><dd>${s.centile_actuel} % des jours</dd>`;
    document.getElementById("lecture-ecart").textContent =
        "Le Henry Hub (cotation en $/MMBtu) est converti en €/MWh avec le taux EUR/USD du jour. L'écart reflète en grande partie le coût de liquéfaction, de transport par méthanier et de regazéification du GNL : quand il s'envole, le gaz européen est en tension.";
}

// ---------------------------------------------------------------------------
// GNL : le JKM (Asie) comparé au TTF (Europe), dans la même unité
// ---------------------------------------------------------------------------
function dessinerGnl(e) {
    const axeX = {
        grid: { display: false },
        ticks: { maxTicksLimit: 8, maxRotation: 0, callback: (v, i) => e.dates[i].slice(0, 4) },
    };
    const trait = { pointRadius: 0, tension: 0.2, borderWidth: 1.6 };
    const optionsBase = {
        interaction: { mode: "index", intersect: false },
        scales: { x: axeX, y: { grid: { color: "#eee9dd" }, title: { display: true, text: "$/MMBtu" } } },
    };

    new Chart(document.getElementById("graphique-gnl"), {
        type: "line",
        data: { labels: e.dates, datasets: [
            { label: "JKM, GNL Asie", data: e.jkm, ...trait, borderColor: "#7a5c99" },
            { label: "TTF, gaz Europe (converti)", data: e.ttf_usd, ...trait, borderColor: "#1f4e79" },
        ] },
        options: { ...optionsBase, plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } } } },
    });

    // l'écart, avec la ligne de référence à zéro : au-dessus, l'Asie paie plus cher
    const zero = e.dates.map(() => 0);
    new Chart(document.getElementById("graphique-gnl-ecart"), {
        type: "line",
        data: { labels: e.dates, datasets: [
            { label: "Zéro", data: zero, ...trait, borderColor: "#8a948e", borderDash: [5, 4], borderWidth: 1 },
            { label: "Écart JKM − TTF", data: e.ecart, ...trait, borderColor: "#b8861b", backgroundColor: "rgba(184,134,27,0.14)", fill: "origin" },
        ] },
        options: { ...optionsBase, plugins: { legend: { display: false } } },
    });

    const s = e.stats;
    const virgule = x => String(x).replace(".", ",");
    document.getElementById("stats-gnl").innerHTML = `
        <dt>Écart actuel</dt><dd>${s.actuel > 0 ? "+" : ""}${virgule(s.actuel)} $/MMBtu</dd>
        <dt>JKM / TTF converti</dt><dd>${virgule(s.jkm)} / ${virgule(s.ttf_usd)} $/MMBtu</dd>
        <dt>Médiane depuis 2017</dt><dd>${s.mediane > 0 ? "+" : ""}${virgule(s.mediane)} $/MMBtu</dd>
        <dt>Jours où l'Asie est plus chère</dt><dd>${s.asie_plus_chere_pct} %</dd>
        <dt>Maximum</dt><dd>+${virgule(s.maximum)} $ (${s.date_max})</dd>
        <dt>Minimum</dt><dd>${virgule(s.minimum)} $ (${s.date_min})</dd>`;
    document.getElementById("lecture-gnl").textContent =
        "Un écart positif signifie que le GNL vaut plus cher en Asie qu'en Europe : les cargaisons flexibles sont attirées vers l'Asie. Un écart négatif attire le GNL vers l'Europe. Le TTF est converti en $/MMBtu avec le taux EUR/USD du jour. Le JKM est un contrat à terme premier mois : la série peut sauter au changement de contrat, et ce contrat est moins liquide que le TTF.";
}
