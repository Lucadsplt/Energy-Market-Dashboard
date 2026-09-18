window.addEventListener("load", () => {
    fetch("data/oil.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-spread");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        { label: "Spread Brent-WTI", data: donnees.series.spread },
                    ],
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe petrole :", erreur));
});