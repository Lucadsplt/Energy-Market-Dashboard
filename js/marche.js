// Page d'accueil « Marchés » : bandeau de cotations, tableau de suivi, signaux, fraîcheur des données.
// Tout est lu dans les fichiers JSON produits par le pipeline : rien n'est calculé ici sauf des variations.

(() => {
const MOIS_ABR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

// ---------- Petits utilitaires ----------
const lireJson = nom => fetch(`data/${nom}.json`, { cache: "no-cache" }).then(r => (r.ok ? r.json() : null)).catch(() => null);
const sansVide = serie => serie.filter(v => v !== null && v !== undefined);
const fr = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
const signe = x => (x > 0 ? "+" : x < 0 ? "−" : "");

// Variation en % entre la dernière valeur et celle située `k` observations avant
function variation(serie, k) {
    const s = sansVide(serie);
    if (s.length <= k) return null;
    return (s[s.length - 1] / s[s.length - 1 - k] - 1) * 100;
}

function celluleVariation(v) {
    if (v === null) return '<td class="neutre">n.d.</td>';
    return `<td class="${v >= 0 ? "hausse" : "baisse"}">${signe(v)}${fr(Math.abs(v), 1)} %</td>`;
}

function courte(iso) {                       // "2026-10-16" -> "16 oct." ; "2026-10-19 12:30" -> "19 oct., 12h30"
    const jour = `${parseInt(iso.slice(8, 10), 10)} ${MOIS_ABR[parseInt(iso.slice(5, 7), 10) - 1]}`;
    return iso.length > 10 ? `${jour}, ${iso.slice(11, 13)}h${iso.slice(14, 16)}` : jour;
}

function heureLocale(isoUtc) {
    return new Date(isoUtc).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// Mini-courbe : une ligne grise qui suit les dernières observations
function minicourbe(serie) {
    const s = sansVide(serie).slice(-20);
    if (s.length < 3) return "";
    const min = Math.min(...s), max = Math.max(...s), echelle = max === min ? 1 : max - min;
    const points = s.map((v, i) => `${(i / (s.length - 1) * 100).toFixed(1)},${(30 - ((v - min) / echelle) * 22).toFixed(1)}`).join(" ");
    return `<svg width="64" height="22" viewBox="0 0 100 38" preserveAspectRatio="none" aria-hidden="true">
        <polyline fill="none" stroke="#7a847e" stroke-width="2.5" vector-effect="non-scaling-stroke" points="${points}"/></svg>`;
}

// Prix moyen par jour de l'électricité (les données sont au quart d'heure)
function moyennesJournalieres(elec) {
    const parJour = {};
    elec.dates.forEach((d, i) => {
        const v = elec.series.fr[i];
        if (v === null) return;
        (parJour[d.slice(0, 10)] = parJour[d.slice(0, 10)] || []).push(v);
    });
    const jours = Object.keys(parJour).sort();
    return { jours, valeurs: jours.map(j => parJour[j].reduce((a, b) => a + b, 0) / parJour[j].length) };
}

// ---------- Construction des lignes du tableau ----------
function construireLignes({ live, oil, gas, elec }) {
    const lignes = [];

    if (live || oil) {
        lignes.push({ groupe: "Pétrole", cle: "petrole", sous: "Brent et WTI · prix en dollars par baril", aller: "petrole" });
        if (live) {
            lignes.push({ nom: "Brent, contrat à terme", serie: live.brent.clotures, unite: "$/bbl", source: "Yahoo, " + heureLocale(live.brent.heure_utc), aller: "petrole", bandeau: "Brent" });
            lignes.push({ nom: "WTI, contrat à terme", serie: live.wti.clotures, unite: "$/bbl", source: "Yahoo, " + heureLocale(live.wti.heure_utc), aller: "petrole", bandeau: "WTI" });
        }
        if (oil) {
            const derniere = oil.dates[oil.series.brent.map(v => v !== null).lastIndexOf(true)];
            lignes.push({ nom: "Brent spot", serie: oil.series.brent, unite: "$/bbl", source: "FRED, au " + courte(derniere), aller: "petrole" });
        }
    }

    if (gas) {
        const dern = cle => courte(gas.dates[gas.series[cle].map(v => v !== null).lastIndexOf(true)]);
        lignes.push({ groupe: "Gaz", cle: "gaz", sous: "TTF européen, Henry Hub américain et GNL asiatique", aller: "gaz" });
        lignes.push({ nom: "TTF (Europe)", serie: gas.series.ttf, unite: "€/MWh", source: "Yahoo, au " + dern("ttf"), aller: "gaz", bandeau: "TTF" });
        lignes.push({ nom: "Henry Hub (États-Unis)", serie: gas.series.henry_hub, unite: "$/MMBtu", source: "Yahoo, au " + dern("henry_hub"), aller: "gaz", bandeau: "HH" });
        if (gas.series.jkm) {
            lignes.push({ nom: "JKM, GNL Asie (à terme)", serie: gas.series.jkm, unite: "$/MMBtu", source: "Yahoo, au " + dern("jkm"), aller: "gaz", bandeau: "JKM" });
        }
    }

    if (elec) {
        const { jours, valeurs } = moyennesJournalieres(elec);
        lignes.push({ groupe: "Électricité", cle: "electricite", sous: "Prix de marché de la veille pour le lendemain · France", aller: "electricite" });
        lignes.push({ nom: "France, day-ahead (moyenne du jour)", serie: valeurs, unite: "€/MWh", source: "ENTSO-E, " + courte(jours[jours.length - 1]), aller: "electricite", bandeau: "FR", sansSemaine: true });
    }
    return lignes;
}

// ---------- Rendu ----------
function afficherTableau(lignes) {
    const corps = lignes.map(l => {
        if (l.groupe) return `<tr class="groupe groupe-${l.cle} cliquable" data-aller="${l.aller}"><td colspan="7">
            <span class="barre"></span><b>${l.groupe}</b><span class="sous">${l.sous}</span><span class="voir">Voir l'analyse →</span></td></tr>`;
        const dernier = sansVide(l.serie).slice(-1)[0];
        const decimales = l.unite.includes("MMBtu") ? 2 : 2;
        return `<tr class="cliquable" data-aller="${l.aller}">
            <td>${l.nom}</td>
            <td>${fr(dernier, decimales)}<span class="unite">${l.unite}</span></td>
            ${celluleVariation(variation(l.serie, 1))}
            ${l.sansSemaine ? '<td class="neutre">n.d.</td><td class="neutre">n.d.</td>' : celluleVariation(variation(l.serie, 5)) + celluleVariation(variation(l.serie, 20))}
            <td>${minicourbe(l.serie)}</td>
            <td class="source">${l.source}</td></tr>`;
    }).join("");

    document.getElementById("suivi").innerHTML =
        `<tr><th>Instrument</th><th>Dernier</th><th>1 j</th><th>1 sem.</th><th>1 mois</th><th>Tendance</th><th>Source</th></tr>${corps}`;
    document.querySelectorAll("#suivi tr.cliquable").forEach(tr =>
        tr.addEventListener("click", () => afficherOnglet(tr.dataset.aller)));
}

function afficherBandeau(lignes) {
    document.getElementById("bandeau-cotations").innerHTML = lignes.filter(l => l.bandeau).map(l => {
        const v = variation(l.serie, 1);
        const dernier = sansVide(l.serie).slice(-1)[0];
        return `<span><b>${l.bandeau}</b>${fr(dernier)} ${v === null ? "" : `<span class="${v >= 0 ? "hausse" : "baisse"}">${signe(v)}${fr(Math.abs(v), 1)} %</span>`}</span>`;
    }).join("");
}

function afficherSignaux({ live, oa, ga, mar }) {
    const signaux = [];

    if (mar) {
        const ruptures = mar.detroits.filter(d => d.zscore <= -2);
        if (ruptures.length) {
            const pire = ruptures.reduce((a, b) => (b.zscore < a.zscore ? b : a));
            signaux.push({ niveau: "alerte", aller: "maritime",
                texte: `${pire.nom} : ${fr(pire.actuel_7j, 1)} pétrolier/jour contre ${fr(pire.reference, 1)} en 2025 (${pire.variation_pct} %). ${ruptures.length} détroit${ruptures.length > 1 ? "s" : ""} sur ${mar.detroits.length} en rupture.` });
        }
    }
    if (oa && oa.ecart) {
        const z = oa.ecart.stats;
        const terme = live ? ` À terme, l'écart n'est que de ${fr(live.brent.prix - live.wti.prix, 1)} $.` : "";
        signaux.push({ niveau: Math.abs(z.z_actuel) > 3 ? "alerte" : Math.abs(z.z_actuel) > 2 ? "attention" : "info", aller: "petrole",
            texte: `Écart Brent − WTI (spot) : ${fr(z.ecart_actuel, 1)} $ contre ${fr(z.moyenne_actuelle, 1)} $ en moyenne sur 1 an (z = ${signe(z.z_actuel)}${fr(Math.abs(z.z_actuel), 1)}).${terme}` });
    }
    if (ga && ga.gnl) {
        const g = ga.gnl.stats;
        signaux.push({ niveau: g.actuel < 0 ? "attention" : "info", aller: "gaz",
            texte: `Écart JKM − TTF : ${signe(g.actuel)}${fr(Math.abs(g.actuel), 2)} $/MMBtu. ${g.actuel < 0 ? "L'Europe paie le GNL plus cher que l'Asie." : "L'Asie paie le GNL plus cher que l'Europe."} (Asie plus chère ${g.asie_plus_chere_pct} % des jours depuis 2017.)` });
    }
    if (oa && oa.brent) {
        const mc = oa.brent.monte_carlo.gaussien;
        signaux.push({ niveau: "info", aller: "petrole",
            texte: `Risque du Brent à 30 jours : perte maximale probable de ${fr(mc.var95, 1)} % (VaR 95 %).` });
    }

    document.getElementById("signaux").innerHTML = signaux.length
        ? signaux.map(s => `<div class="ligne-signal cliquable" data-aller="${s.aller}"><span class="point ${s.niveau}"></span><span>${s.texte}</span></div>`).join("")
        : '<div class="ligne-signal"><span>Aucun signal.</span></div>';
    document.querySelectorAll("#signaux .cliquable").forEach(el =>
        el.addEventListener("click", () => afficherOnglet(el.dataset.aller)));
}

function afficherFraicheur({ live, oil, gas, elec, mar, meta }) {
    const dernierJour = (donnees, cle) => courte(donnees.dates[donnees.series[cle].map(v => v !== null).lastIndexOf(true)]);
    const lignes = [];
    if (live) lignes.push(["Contrats à terme pétrole (Yahoo)", heureLocale(live.brent.heure_utc) + ", différé"]);
    if (oil) lignes.push(["Pétrole spot (FRED)", "au " + dernierJour(oil, "brent") + ", retard ~1 sem."]);
    if (gas) lignes.push(["Gaz et GNL (Yahoo)", "au " + dernierJour(gas, "ttf")]);
    if (elec) lignes.push(["Électricité (ENTSO-E)", courte(elec.dates[elec.dates.length - 1])]);
    if (mar) lignes.push(["Trafic maritime (FMI)", "au " + courte(mar.derniere_date)]);
    if (meta) lignes.push(["Dernière mise à jour du site", heureLocale(meta.maj)]);
    document.getElementById("fraicheur").innerHTML =
        lignes.map(([nom, valeur]) => `<div class="ligne-fraicheur"><span>${nom}</span><span>${valeur}</span></div>`).join("");
}

window.addEventListener("load", () => {
    Promise.all(["oil_live", "oil", "gas", "electricity", "oil_analysis", "gas_analysis", "maritime", "meta"].map(lireJson))
        .then(([live, oil, gas, elec, oa, ga, mar, meta]) => {
            const lignes = construireLignes({ live, oil, gas, elec });
            afficherTableau(lignes);
            afficherBandeau(lignes);
            afficherSignaux({ live, oa, ga, mar });
            afficherFraicheur({ live, oil, gas, elec, mar, meta });
        })
        .catch(e => console.error("Page Marchés :", e));
});
})();
