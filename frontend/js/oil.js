window.addEventListener("load", () => {
    fetch("../data/oil.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-petrole");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        { label: "Pétrole Europe (Brent)", data: donnees.series.brent },
                        { label: "Pétrole US (WTI)", data: donnees.series.wti },
                    ],
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe petrole :", erreur));
});