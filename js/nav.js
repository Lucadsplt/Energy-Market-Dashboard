// Titre affiché en haut de chaque page
const TITRES = {
    general:     ["Pétrole · gaz · GNL · électricité — données différées", "Marchés"],
    petrole:     ["Brent et WTI", "Pétrole"],
    gaz:         ["TTF et Henry Hub", "Gaz"],
    electricite: ["France et Allemagne", "Électricité"],
    news:        ["Pétrole · Gaz · Électricité", "Actualités"],
    maritime:    ["Pétroliers · détroits stratégiques", "Trafic maritime"],
    strategies:  ["Règles testées sur le pétrole et le gaz · outil d'étude, pas un conseil en investissement", "Stratégies"],
};
// Le sélecteur de période ne concerne que les pages avec des prix journaliers
const AVEC_PERIODE = ["petrole", "gaz"];

// Navigation par onglets (barre du haut + tags de la synthèse)
function afficherOnglet(cible) {
    document.querySelectorAll(".nav-link").forEach(l =>
        l.classList.toggle("active", l.dataset.cible === cible));
    document.querySelectorAll(".onglet").forEach(o =>
        o.classList.toggle("active", o.id === cible));

    // Les graphes ont été créés dans des onglets masqués : on les redessine.
    requestAnimationFrame(() => requestAnimationFrame(() => {
        document.getElementById(cible).querySelectorAll("canvas").forEach(canvas => {
            const graphe = Chart.getChart(canvas);
            if (graphe) { graphe.resize(); graphe.update(); }
        });
    }));
    document.getElementById("intro-sur").textContent = TITRES[cible][0];
    document.getElementById("intro-titre").textContent = TITRES[cible][1];
    document.getElementById("plage").style.display = AVEC_PERIODE.includes(cible) ? "" : "none";
    document.dispatchEvent(new CustomEvent("onglet-affiche", { detail: cible }));
    window.scrollTo({ top: 0 });
}

document.querySelectorAll(".nav-link").forEach(lien => {
    lien.addEventListener("click", e => {
        e.preventDefault();
        afficherOnglet(lien.dataset.cible);
    });
});

// Les tags de la synthèse renvoient vers l'onglet correspondant
document.querySelectorAll("[data-aller]").forEach(tag => {
    tag.addEventListener("click", e => {
        e.preventDefault();
        afficherOnglet(tag.dataset.aller);
    });
});
