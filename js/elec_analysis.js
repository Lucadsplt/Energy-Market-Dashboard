// Analyses de la page Électricité
const VERT = [18, 185, 129], CREME = [246, 244, 238], ROUGE = [214, 69, 61];

window.addEventListener("load", () => {
    fetch("data/electricity_analysis.json")
        .then(r => r.json())
        .then(d => {
            dessinerProfil(d.fr.profil);
            dessinerNegatifs(d.fr.negatifs);
        })
        .catch(e => console.error("Analyse électricité :", e));
});

// Mélange deux couleurs : t = 0 donne a, t = 1 donne b
function melange(a, b, t) {
    return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

// Vert (pas cher) -> crème (milieu) -> rouge (cher)
function couleur(t) {
    const c = t < 0.5 ? melange(VERT, CREME, t * 2) : melange(CREME, ROUGE, (t - 0.5) * 2);
    return `rgb(${c.join(",")})`;
}

function dessinerProfil(p) {
    const tout = p.matrice.flat();
    const min = Math.min(...tout), max = Math.max(...tout);

    // Carte de chaleur : une ligne d'en-têtes (heures), puis une ligne par jour
    let html = '<div class="cellule entete"></div>';
    for (let h = 0; h < 24; h++) html += `<div class="cellule entete">${h}h</div>`;
    p.matrice.forEach((ligne, j) => {
        html += `<div class="cellule jour">${p.jours[j]}</div>`;
        ligne.forEach((v, h) => {
            const t = (v - min) / (max - min);
            const texte = t > 0.85 ? "#fff" : "var(--texte)";
            html += `<div class="cellule" style="background:${couleur(t)};color:${texte}" title="${p.jours[j]} ${h}h : ${v} €/MWh">${Math.round(v)}</div>`;
        });
    });
    document.getElementById("heatmap-elec").innerHTML = html;
    document.getElementById("legende-min").textContent = Math.round(min) + " €/MWh";
    document.getElementById("legende-max").textContent = Math.round(max) + " €/MWh";

    const s = p.stats;
    document.getElementById("stats-profil").innerHTML = `
        <dt>Prix moyen sur l'année</dt><dd>${s.moyenne} €/MWh</dd>
        <dt>Heure la plus chère (en moyenne)</dt><dd>${s.heure_la_plus_chere} h</dd>
        <dt>Heure la moins chère (en moyenne)</dt><dd>${s.heure_la_moins_chere} h</dd>
        <dt>Quarts d'heure à prix négatif</dt><dd>${s.negatifs_pct} %</dd>
        <dt>Prix minimum / maximum</dt><dd>${s.prix_min} / ${s.prix_max} €/MWh</dd>
        <dt>Jours analysés</dt><dd>${s.nb_jours}</dd>`;
    document.getElementById("lecture-profil").textContent =
        "Le creux de la mi-journée vient de la production solaire, surtout le week-end quand la demande est faible ; le pic du soir apparaît quand le soleil se couche alors que la consommation reste élevée. Un prix négatif signifie que les producteurs paient pour injecter du courant sur un réseau saturé.";
}

const NOMS_MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

// Diagramme en barres simple, axe vertical en pourcentage
function barres(id, labels, valeurs) {
    new Chart(document.getElementById(id), {
        type: "bar",
        data: { labels, datasets: [{ data: valeurs, backgroundColor: "rgba(18,185,129,0.65)", borderRadius: 3 }] },
        options: {
            plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${c.parsed.y} %` } } },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
                y: { grid: { color: "#eee9dd" }, ticks: { callback: v => v + " %" } },
            },
        },
    });
}

function dessinerNegatifs(n) {
    const libelle = ym => NOMS_MOIS[+ym.slice(5) - 1] + " " + ym.slice(2, 4);
    barres("graphique-neg-mois", n.mois.labels.map(libelle), n.mois.pct);
    barres("graphique-neg-heure", Array.from({ length: 24 }, (_, h) => h + "h"), n.heures);

    const s = n.stats;
    document.getElementById("stats-neg").innerHTML = `
        <dt>Part de quarts d'heure négatifs</dt><dd>${s.pct_total} %</dd>
        <dt>Durée cumulée</dt><dd>${s.heures_negatives} heures</dd>
        <dt>Part tombant un week-end</dt><dd>${s.pct_weekend} % (les week-ends = 29 % des jours)</dd>
        <dt>Prix moyen quand négatif</dt><dd>${s.prix_moyen_si_negatif} €/MWh</dd>
        <dt>Prix minimum</dt><dd>${s.prix_min} €/MWh</dd>`;
    document.getElementById("lecture-neg").textContent =
        "Les prix négatifs apparaissent quand la production (surtout solaire) dépasse la demande et ce que les interconnexions peuvent exporter : ils se concentrent à la mi-journée, au printemps et en été, et sont plus fréquents le week-end quand la consommation est basse. Le premier et le dernier mois du graphique sont incomplets.";
}