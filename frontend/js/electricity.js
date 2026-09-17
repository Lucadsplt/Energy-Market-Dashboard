window.addEventListener("load", () => {
    fetch("../data/electricity.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-electricite");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        { label: "France (€/MWh)", data: donnees.series.fr },
                        { label: "Allemagne-Luxembourg (€/MWh)", data: donnees.series.de_lu },
                    ],
                },
                options: {
                    elements: { point: { radius: 0 } },
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe electricite :", erreur));
});