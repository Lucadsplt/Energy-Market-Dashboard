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
