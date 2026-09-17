window.addEventListener("load", () => {
    fetch("../data/electricity.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-elec-spread");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        { label: "Spread FR − DE (€/MWh)", data: donnees.series.spread_fr_de },
                    ],
                },
                options: {
                    elements: { point: { radius: 0 } },
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe spread elec :", erreur));
});