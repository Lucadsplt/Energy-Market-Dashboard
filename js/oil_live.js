// Bandeau « Prix du jour » : contrats à terme Yahoo Finance, comparés au dernier prix spot FRED.
// Deux grandeurs différentes : le spot est le baril physique, le contrat à terme est le baril livré dans ~1 mois.
function fr(x, d = 1) {
    return x.toFixed(d).replace(".", ",");
}

function pastille(nom, m) {
    const sens = m.variation >= 0 ? "up" : "down";
    const fleche = m.variation >= 0 ? "▲" : "▼";
    return `<div class="live-prix">
        <span class="live-nom">${nom}</span>
        <span class="live-valeur">${fr(m.prix)} <small>$/baril</small></span>
        <span class="live-var ${sens}">${fleche} ${fr(Math.abs(m.variation), 2)} (${fr(Math.abs(m.variation_pct), 2)} %)</span>
    </div>`;
}

// Dernier prix spot FRED non nul : { date, valeur }
function dernierSpot(spot, serie) {
    for (let i = spot.series[serie].length - 1; i >= 0; i--) {
        if (spot.series[serie][i] !== null) return { date: spot.dates[i], valeur: spot.series[serie][i] };
    }
    return null;
}

function jourFr(iso) {
    return new Date(iso + "T12:00:00").toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
}

window.addEventListener("load", () => {
    const conteneurs = document.querySelectorAll(".bandeau-live");
    if (!conteneurs.length) return;

    Promise.all([
        fetch("data/oil_live.json", { cache: "no-cache" }).then(r => r.json()),
        fetch("data/oil.json").then(r => r.json()),
    ]).then(([live, spot]) => {
        const brent = live.brent, wti = live.wti;
        const heure = new Date(brent.heure_utc).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

        // Comparaison au dernier jour où le spot FRED existe : même date, deux prix différents
        let comparaison = "";
        const s = dernierSpot(spot, "brent");
        const i = s ? brent.dates.indexOf(s.date) : -1;
        if (s && i >= 0) {
            const terme = brent.clotures[i];
            const prime = s.valeur - terme;
            comparaison = `<p class="live-compare">
                <b>Spot ou contrat à terme ?</b> Le ${jourFr(s.date)}, dernier jour publié par FRED, le Brent spot valait
                <b>${fr(s.valeur)} $</b> et le contrat à terme <b>${fr(terme)} $</b>,
                soit ${prime >= 0 ? "une prime" : "une décote"} de <b>${fr(Math.abs(prime))} $</b> pour le baril physique par rapport au contrat à terme.
                Les analyses utilisent le spot (FRED) ; ce bandeau montre le prix du jour.
            </p>`;
        }

        const html = `
            <div class="live-tete">
                <span class="live-badge">Contrat à terme · Yahoo Finance</span>
                <span class="live-titre">Prix du jour</span>
                <span class="live-heure">cotation différée · ${heure}</span>
            </div>
            <div class="live-prix-liste">
                ${pastille("Brent", brent)}
                ${pastille("WTI", wti)}
                <div class="live-prix">
                    <span class="live-nom">Écart Brent − WTI</span>
                    <span class="live-valeur">${fr(brent.prix - wti.prix)} <small>$/baril</small></span>
                    <span class="live-var">à terme</span>
                </div>
            </div>
            ${comparaison}`;
        conteneurs.forEach(c => { c.innerHTML = html; });
    }).catch(e => {
        console.error("Prix du jour :", e);
        conteneurs.forEach(c => { c.style.display = "none"; });
    });
});
