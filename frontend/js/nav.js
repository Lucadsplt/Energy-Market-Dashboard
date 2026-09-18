// Recupere tous les liens de navigation
const liens = document.querySelectorAll(".nav-link");

liens.forEach(lien => {
    lien.addEventListener("click", (evenement) => {
        evenement.preventDefault();   // empeche le saut de page du lien "#"

        // 1. Retire "active" de TOUS les liens et de TOUS les onglets
        document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
        document.querySelectorAll(".onglet").forEach(o => o.classList.remove("active"));

        // 2. Active le lien clique
        lien.classList.add("active");

        // 3. Affiche l'onglet correspondant (data-cible -> id de la section)
        const cible = lien.dataset.cible;
        const section = document.getElementById(cible);
        section.classList.add("active");

        // 4. Redessiner les graphes de l'onglet (crees quand il etait masque).
        //    Double requestAnimationFrame : on attend que la mise en page ET le
        //    redimensionnement soient termines avant de recalculer/redessiner.
        requestAnimationFrame(() => requestAnimationFrame(() => {
            section.querySelectorAll("canvas").forEach(canvas => {
                const graphe = Chart.getChart(canvas);
                if (graphe) {
                    graphe.resize();
                    graphe.update();
                }
            });
        }));
    });
});