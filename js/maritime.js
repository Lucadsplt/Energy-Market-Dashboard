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
            dessinerCarte(d.detroits);
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


// ======================================================================
// Carte : détroits (IMF PortWatch) + pétroliers en direct (AISStream)
// ======================================================================
const URL_LIVE = "https://raw.githubusercontent.com/Lucadsplt/Energy-Market-Dashboard/live-data/tankers.json";
const URL_TEST = "data/tankers_demo.json";      // relevé d'exemple, utilisé tant que la branche live-data n'existe pas

// Position de chaque détroit : on cherche un mot-clé dans le nom affiché
const POSITIONS_DETROITS = [
    ["Ormuz", [26.57, 56.25]], ["Bab", [12.6, 43.35]], ["Suez", [30.45, 32.35]],
    ["Malacca", [2.5, 101.2]], ["Cap", [-34.35, 18.5]], ["Bosphore", [41.12, 29.05]],
];
const COULEUR_ETAT = { rupture: "#d6453d", baisse: "#d99a0b", normal: "#6f7a73", hausse: "#12B981" };
const COULEUR_COUVERTURE = { excellente: "#12B981", moyenne: "#d99a0b", faible: "#d6453d" };

const VUES = {
    monde: [[25, 25], 2], nord: [[54.5, 2], 5], mexique: [[28.4, -93], 6],
    gibraltar: [[36, -5.6], 8], ormuz: [[26.5, 56.5], 6],
};

function iconeFleche(cap) {
    const angle = cap === null || cap === undefined || cap >= 360 ? 0 : cap;     // 360 = cap non disponible
    return L.divIcon({
        className: "fleche-navire", iconSize: [16, 16], iconAnchor: [8, 8],
        html: `<svg width="16" height="16" viewBox="0 0 16 16" style="transform:rotate(${angle}deg)">
            <path d="M8 1 L13 14 L8 11 L3 14 Z" fill="#0F2A22" stroke="#fff" stroke-width="1.2" stroke-linejoin="round"/></svg>`,
    });
}

function fichePetrolier(p) {
    const lignes = [`<b>${p.nom}</b>`];
    if (p.destination) lignes.push(`Destination : ${p.destination}`);
    lignes.push(p.arret ? "À l'arrêt (ancre ou quai)" : `Vitesse : ${virgule(p.sog || 0)} nœuds`);
    if (p.tirant_eau) lignes.push(`Tirant d'eau : ${virgule(p.tirant_eau)} m`);
    if (p.longueur) lignes.push(`Longueur : ${p.longueur} m`);
    return lignes.join("<br>");
}

function ficheDetroit(d) {
    const [classe, texte] = etiquette(d.zscore);
    return `<b>${d.nom}</b><br>${virgule(d.actuel_7j)} pétroliers/jour (référence 2025 : ${virgule(d.reference)})<br>
        ${d.variation_pct > 0 ? "+" : ""}${d.variation_pct} % · z-score ${virgule(d.zscore)}<br>
        <span class="badge ${classe}">${texte}</span>`;
}

async function chargerReleve() {
    try {
        const r = await fetch(URL_LIVE, { cache: "no-cache" });
        if (!r.ok) throw new Error("branche live-data introuvable (" + r.status + ")");
        return { ...(await r.json()), test: false };
    } catch (e) {
        const r = await fetch(URL_TEST);
        return { ...(await r.json()), test: true };
    }
}

function dessinerCarte(detroits) {
    if (typeof L === "undefined") return;
    const carte = L.map("carte-maritime", { minZoom: 2, worldCopyJump: true, scrollWheelZoom: false }).setView(...VUES.monde);
    window.carteMaritime = carte;
    carte.on("click", () => carte.scrollWheelZoom.enable());       // la molette ne zoome qu'après un clic sur la carte

    // Fond OpenStreetMap (gratuit pour un usage léger, attribution obligatoire)
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">les contributeurs OpenStreetMap</a>',
        maxZoom: 18,
    }).addTo(carte);

    const calqueDetroits = L.layerGroup().addTo(carte);
    const calqueZones = L.layerGroup().addTo(carte);
    const calqueMouvement = L.layerGroup().addTo(carte);
    const calqueArret = L.layerGroup().addTo(carte);

    // Détroits : un cercle par détroit, taille = trafic de référence, couleur = état
    detroits.forEach(d => {
        const entree = POSITIONS_DETROITS.find(([mot]) => d.nom.includes(mot));
        if (!entree) return;
        const [classe] = etiquette(d.zscore);
        const rayon = 7 + Math.sqrt(d.reference) * 1.7;
        L.circleMarker(entree[1], {
            radius: rayon, color: COULEUR_ETAT[classe], weight: 2, fillColor: COULEUR_ETAT[classe], fillOpacity: 0.45,
        }).bindPopup(ficheDetroit(d))
          .bindTooltip(d.nom.replace("Détroit d'", "").replace("Canal de ", ""), {
              permanent: true, direction: "bottom", offset: [0, rayon * 0.4], className: "etiquette-detroit" })
          .addTo(calqueDetroits);
    });

    L.control.layers(null, {
        "Détroits (PortWatch)": calqueDetroits,
        "Zones suivies (AIS)": calqueZones,
        "Pétroliers en mouvement": calqueMouvement,
        "Pétroliers à l'arrêt": calqueArret,
    }, { collapsed: false, position: "topright" }).addTo(carte);

    // Boutons de zoom rapide
    document.querySelectorAll("#carte-outils [data-vue]").forEach(b =>
        b.addEventListener("click", () => carte.setView(...VUES[b.dataset.vue])));

    chargerReleve().then(r => {
        r.zones.forEach(z => {
            L.rectangle(z.bbox, { color: COULEUR_COUVERTURE[z.couverture], weight: 1.5, dashArray: "5 4", fill: false })
                .bindTooltip(`${z.nom} : couverture ${z.couverture}`, { sticky: true })
                .addTo(calqueZones);
        });
        r.petroliers.forEach(p => {
            if (p.arret) {
                L.circleMarker([p.lat, p.lon], { radius: 4.5, color: "#fff", weight: 1, fillColor: "#d99a0b", fillOpacity: 0.95 })
                    .bindTooltip(fichePetrolier(p)).addTo(calqueArret);
            } else {
                L.marker([p.lat, p.lon], { icon: iconeFleche(p.cog) })
                    .bindTooltip(fichePetrolier(p)).addTo(calqueMouvement);
            }
        });
        remplirZones(r);
    }).catch(e => {
        console.error("Relevé AIS :", e);
        document.getElementById("zones-live").textContent = "Relevé AIS indisponible.";
    });
}

function remplirZones(r) {
    const date = new Date(r.releve_utc);
    const agePourcent = (Date.now() - date.getTime()) / 60000;
    let badge = "";
    if (r.test) badge = ' <span class="badge test">Données de test</span>';
    else if (agePourcent > 180) badge = ' <span class="badge baisse">Relevé ancien</span>';

    document.getElementById("carte-releve").innerHTML =
        "relevé du " + date.toLocaleString("fr-FR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }) + badge;

    const nb = n => Number(n).toLocaleString("fr-FR");
    document.getElementById("zones-live").innerHTML = r.zones.map(z => `
        <div class="zone-live">
            <div class="zone-tete"><b>${z.nom}</b><span class="badge ${z.couverture}">Couverture ${z.couverture}</span></div>
            <div class="zone-chiffres"><span><b>${nb(z.petroliers)}</b> pétroliers identifiés</span>
                <span>dont <b>${nb(z.a_l_ancre)}</b> à l'arrêt</span></div>
            <div class="zone-detail">${nb(z.navires)} navires entendus · ${nb(z.identifies)} dont le type est connu</div>
        </div>`).join("");
}

// La carte est créée dans un onglet masqué : elle doit recalculer sa taille quand l'onglet s'affiche
document.addEventListener("onglet-affiche", e => {
    if (e.detail === "maritime" && window.carteMaritime) setTimeout(() => window.carteMaritime.invalidateSize(), 60);
});
