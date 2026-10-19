// Sous-onglets (« volets ») d'une page de données : un seul groupe de graphiques est affiché à la fois.
// Une page qui en a besoin porte l'attribut data-volets ; ses boutons sont dans .sous-nav et ses blocs dans .volet.
(() => {
    const pages = document.querySelectorAll("[data-volets]");

    function majPeriode(page, nom) {
        // le sélecteur « 30 jours / Tout » ne concerne que le volet des prix journaliers
        const periode = document.getElementById("plage");
        if (!periode || !page.classList.contains("active") || !page.dataset.periodeVolet) return;
        periode.style.display = page.dataset.periodeVolet === nom ? "" : "none";
    }

    pages.forEach(page => {
        const boutons = [...page.querySelectorAll(".sous-nav button")];
        const volets = [...page.querySelectorAll(".volet")];
        const memoire = "volet-" + page.id;

        function afficher(nom) {
            boutons.forEach(b => b.classList.toggle("actif", b.dataset.volet === nom));
            volets.forEach(v => { v.hidden = v.dataset.volet !== nom; });

            // les graphiques créés dans un bloc masqué n'ont pas de taille : on les redessine à l'affichage
            requestAnimationFrame(() => requestAnimationFrame(() => {
                page.querySelectorAll(".volet:not([hidden]) canvas").forEach(canvas => {
                    const graphe = Chart.getChart(canvas);
                    if (graphe) { graphe.resize(); graphe.update("none"); }
                });
            }));
            document.dispatchEvent(new CustomEvent("volet-affiche", { detail: { page: page.id, volet: nom } }));
            majPeriode(page, nom);
            try { localStorage.setItem(memoire, nom); } catch (e) { /* stockage indisponible : sans importance */ }
        }

        boutons.forEach(b => b.addEventListener("click", () => afficher(b.dataset.volet)));

        let depart = boutons[0].dataset.volet;
        try {
            const sauve = localStorage.getItem(memoire);
            if (sauve && boutons.some(b => b.dataset.volet === sauve)) depart = sauve;
        } catch (e) { /* idem */ }
        afficher(depart);
    });

    // quand on arrive sur une page à volets, on réapplique la règle du sélecteur de période
    document.addEventListener("onglet-affiche", e => {
        const page = document.getElementById(e.detail);
        if (!page || page.dataset.volets === undefined) return;
        const actif = page.querySelector(".sous-nav button.actif");
        if (actif) majPeriode(page, actif.dataset.volet);
    });
})();
