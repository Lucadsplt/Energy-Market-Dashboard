// Onglet Trafic maritime : pétroliers par détroit (IMF PortWatch) mis en regard du prix du Brent
const MOIS_LONGS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];

const virgule = (x, d = 1) => Number(x).toFixed(d).replace(".", ",");

function dateLongue(iso) {
    return `${parseInt(iso.slice(8, 10), 10)} ${MOIS_LONGS[parseInt(iso.slice(5, 7), 10) - 1]} ${iso.slice(0, 4)}`;
}

// Mini-courbe SVG : une ligne qui suit la série, sans axes
function minicourbe(serie, couleur) {
    const L = 110, H = 28, marge = 2;
    const min = Math.min(...serie), max = Math.max(...serie);
    const echelle = max === min ? 1 : max - min;
    const points = serie.map((v, i) => {
        const x = marge + (i / (serie.length - 1)) * (L - 2 * marge);
        const y = H - marge - ((v - min) / echelle) * (H - 2 * marge);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return `<svg width="${L}" height="${H}" viewBox="0 0 ${L} ${H}" aria-hidden="true">
        <polyline points="${points}" fill="none" stroke="${couleur}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}

// Étiquette selon le z-score : en dessous de -2, le trafic est anormalement bas
function etiquette(z) {
    if (z <= -2) return ["rupture", "Rupture"];
    if (z <= -1) return ["baisse", "En baisse"];
    if (z >= 1) return ["hausse", "En hausse"];
    return ["normal", "Normal"];
}

window.addEventListener("load", () => {
    fetch("data/maritime.json")
        .then(r => r.json())
        .then(d => {
            dessinerOrmuz(d.ormuz_vs_brent);
            remplirTableau(d.detroits);
            remplirResume(d);
        })
        .catch(e => console.error("Trafic maritime :", e));
});

function remplirResume(d) {
    const ormuz = d.detroits.find(x => x.nom.includes("Ormuz")) || d.detroits[0];
    document.getElementById("mar-ormuz").textContent = virgule(ormuz.actuel_7j);
    const varOrmuz = document.getElementById("mar-ormuz-var");
    varOrmuz.textContent = `${ormuz.variation_pct > 0 ? "+" : ""}${ormuz.variation_pct} % vs 2025 (${virgule(ormuz.reference)}/jour)`;
    varOrmuz.classList.add(ormuz.variation_pct >= 0 ? "up" : "down");

    const nb = d.detroits.filter(x => x.zscore <= -2).length;
    document.getElementById("mar-rupture").textContent = `${nb} / ${d.detroits.length}`;
    const noms = d.detroits.filter(x => x.zscore <= -2).map(x => x.nom).join(", ");
    document.getElementById("mar-rupture-txt").textContent = noms || "aucun";

    document.getElementById("mar-date").textContent = dateLongue(d.derniere_date).replace(/ \d{4}$/, "");
}

function remplirTableau(detroits) {
    const lignes = detroits.map(x => {
        const [classe, texte] = etiquette(x.zscore);
        const couleur = classe === "rupture" ? "#d6453d" : classe === "baisse" ? "#d99a0b" : classe === "hausse" ? "#12B981" : "#6f7a73";
        return `<tr>
            <td>${x.nom}</td>
            <td>${virgule(x.actuel_7j)}</td>
            <td>${virgule(x.reference)}</td>
            <td>${x.variation_pct > 0 ? "+" : ""}${x.variation_pct} %</td>
            <td>${virgule(x.zscore)}</td>
            <td><span class="badge ${classe}">${texte}</span></td>
            <td>${minicourbe(x.serie, couleur)}</td></tr>`;
    }).join("");

    document.getElementById("table-detroits").innerHTML =
        `<tr><th>Détroit</th><th>Pétroliers/jour</th><th>Référence 2025</th><th>Variation</th><th>Z-score</th><th>État</th><th>90 derniers jours</th></tr>` + lignes;
}

function dessinerOrmuz(o) {
    const axeX = {
        grid: { display: false },
        ticks: { maxTicksLimit: 8, maxRotation: 0, callback: (v, i) => o.dates[i].slice(0, 7) },
    };
    new Chart(document.getElementById("graphique-ormuz"), {
        type: "line",
        data: {
            labels: o.dates,
            datasets: [
                {
                    label: "Pétroliers à Ormuz (par jour, moyenne 7 jours)", data: o.ormuz_7j, yAxisID: "y",
                    borderColor: "#0F2A22", backgroundColor: "rgba(15,42,34,0.10)", fill: true,
                    borderWidth: 2, pointRadius: 0, tension: 0.2,
                },
                {
                    label: "Brent spot (FRED, $/baril)", data: o.brent, yAxisID: "y2",
                    borderColor: "#c2621f", borderWidth: 2, pointRadius: 0, tension: 0.2, spanGaps: true,
                },
            ],
        },
        options: {
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } },
                tooltip: { backgroundColor: "#0F2A22", padding: 10, cornerRadius: 8 },
            },
            scales: {
                x: axeX,
                y: { position: "left", min: 0, grid: { color: "#eee9dd" }, title: { display: true, text: "pétroliers / jour" } },
                y2: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "Brent spot ($/baril)" } },
            },
        },
    });

    // Phrase de lecture calculée à partir des données
    // premier jour à partir d'une date où le prix FRED existe (pas de prix le week-end)
    const jourAvecPrix = debut => o.dates.findIndex((d, i) => d >= debut && o.brent[i] !== null);
    const avant = jourAvecPrix("2026-02-01");
    const mars = jourAvecPrix("2026-04-01");
    let texte = "Le trafic des pétroliers à Ormuz est mesuré en moyenne sur 7 jours. ";
    if (avant >= 0 && mars >= 0 && o.brent[avant] && o.brent[mars]) {
        texte += `Entre février et avril 2026, il passe de ${virgule(o.ormuz_7j[avant], 0)} à ${virgule(o.ormuz_7j[mars], 0)} pétroliers par jour, alors que le Brent spot passe de ${virgule(o.brent[avant], 0)} à ${virgule(o.brent[mars], 0)} $. `;
    }
    texte += `Le lien n'est pas mécanique : d'autres facteurs jouent sur les prix, et le Brent spot (FRED) est publié avec environ une semaine de retard, d'où l'arrêt de la courbe orange.`;
    document.getElementById("lecture-ormuz").textContent = texte;
}
