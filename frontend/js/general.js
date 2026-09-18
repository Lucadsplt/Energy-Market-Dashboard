// Derniere valeur non nulle d'une serie + variation vs l'avant-derniere
function dernierEtVariation(valeurs) {
    const propres = valeurs.filter(v => v !== null);
    const dernier = propres[propres.length - 1];
    const precedent = propres[propres.length - 2];
    const variation = precedent !== undefined ? dernier - precedent : null;
    return { dernier, variation };
}

// Affiche une variation, coloree en vert (hausse) ou rouge (baisse)
function afficherVariation(id, variation) {
    if (variation === null) return;
    const el = document.getElementById(id);
    const signe = variation >= 0 ? "+" : "";
    el.textContent = signe + variation.toFixed(1);
    el.classList.add(variation >= 0 ? "up" : "down");
}

window.addEventListener("load", () => {
    // Gaz : prix TTF + volatilite
    fetch("../data/gas.json")
        .then(r => r.json())
        .then(d => {
            const ttf = dernierEtVariation(d.series.ttf);
            document.getElementById("kpi-ttf").textContent = ttf.dernier.toFixed(1);
            afficherVariation("kpi-ttf-var", ttf.variation);

            const vol = dernierEtVariation(d.series.ttf_vol);
            document.getElementById("kpi-vol-ttf").textContent = vol.dernier.toFixed(1);
        })
        .catch(e => console.error("KPI gaz :", e));

    // Petrole : Brent + spread Brent-WTI
    fetch("../data/oil.json")
        .then(r => r.json())
        .then(d => {
            const brent = dernierEtVariation(d.series.brent);
            document.getElementById("kpi-brent").textContent = brent.dernier.toFixed(1);
            afficherVariation("kpi-brent-var", brent.variation);

            const spread = dernierEtVariation(d.series.spread);
            document.getElementById("kpi-spread-oil").textContent = spread.dernier.toFixed(1);
        })
        .catch(e => console.error("KPI petrole :", e));

    // Electricite : prix FR + spread FR-DE
    fetch("../data/electricity.json")
        .then(r => r.json())
        .then(d => {
            const fr = dernierEtVariation(d.series.fr);
            document.getElementById("kpi-elec-fr").textContent = fr.dernier.toFixed(1);
            afficherVariation("kpi-elec-fr-var", fr.variation);

            const spread = dernierEtVariation(d.series.spread_fr_de);
            document.getElementById("kpi-spread-elec").textContent = spread.dernier.toFixed(1);
        })
        .catch(e => console.error("KPI electricite :", e));
});