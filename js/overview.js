// Signaux clés de la Vue d'ensemble, lus dans les fichiers d'analyse produits par le pipeline
function signal(id, valeur, texte) {
    document.getElementById(id).textContent = valeur;
    document.getElementById(id + "-txt").textContent = texte;
}

window.addEventListener("load", () => {
    const lire = nom => fetch(`data/${nom}.json`).then(r => r.json());

    // Promise.all attend que les trois fichiers soient arrivés avant d'écrire quoi que ce soit
    Promise.all([lire("oil_analysis"), lire("gas_analysis"), lire("electricity_analysis")])
        .then(([petrole, gaz, elec]) => {
            // Pétrole : z-score de l'écart Brent - WTI (prix spot FRED)
            const z = petrole.ecart.stats;
            const etat = Math.abs(z.z_actuel) > 3 ? "Très inhabituel" : Math.abs(z.z_actuel) > 2 ? "Inhabituel" : "Normal";
            signal("sig-zscore", "z = " + (z.z_actuel > 0 ? "+" : "") + z.z_actuel,
                `${etat} : ${z.ecart_actuel} $ contre ${z.moyenne_actuelle} $ en moyenne sur 1 an.`);

            // Pétrole : risque à 30 jours
            const mc = petrole.brent.monte_carlo.gaussien;
            const baisse20 = mc.probas.find(p => p.variation === -20);
            signal("sig-var", mc.var95 + " %",
                `Perte maximale probable dans 95 % des cas ; ${baisse20.proba} % de chances de toucher −20 % d'ici 30 jours.`);

            // Gaz : écart TTF - Henry Hub
            const g = gaz.ecart.stats;
            signal("sig-gaz", g.actuel + " €/MWh",
                `Plus élevé que ${g.centile_actuel} % des jours depuis 2017 (médiane : ${g.mediane} €/MWh).`);

            // Électricité : prix négatifs
            const n = elec.fr.negatifs.stats;
            signal("sig-elec", n.pct_total + " %",
                `des quarts d'heure sur 12 mois, dont ${n.pct_weekend} % un week-end. Heure la plus chère : ${elec.fr.profil.stats.heure_la_plus_chere} h.`);
        })
        .catch(e => console.error("Vue d'ensemble :", e));
});

// Alerte « trafic maritime » dans le bloc Pétrole : affichée seulement si un détroit sort de sa zone normale
window.addEventListener("load", () => {
    const alerte = document.getElementById("alerte-maritime");
    if (!alerte) return;

    fetch("data/maritime.json")
        .then(r => r.json())
        .then(m => {
            const ruptures = m.detroits.filter(d => d.zscore <= -2);
            if (ruptures.length === 0) return;                       // rien d'anormal : on n'affiche rien

            const pire = ruptures.reduce((a, b) => (b.zscore < a.zscore ? b : a));
            const fr = x => String(x).replace(".", ",");
            alerte.innerHTML = `<span><b>Trafic maritime :</b> ${pire.nom} à ${fr(pire.actuel_7j)} pétrolier/jour contre
                ${fr(pire.reference)} en 2025 (${pire.variation_pct} %). ${ruptures.length} détroit${ruptures.length > 1 ? "s" : ""} sur ${m.detroits.length} en rupture.</span>
                <span class="alerte-lien">Voir le trafic →</span>`;
            alerte.hidden = false;
        })
        .catch(() => { /* pas de données maritimes : l'alerte reste masquée */ });
});
