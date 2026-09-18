window.addEventListener("load", () => {
    fetch("data/gas.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-gaz-vol");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        { label: "Volatilité TTF (annualisée, %)", data: donnees.series.ttf_vol },
                        { label: "Volatilité Henry Hub (annualisée, %)", data: donnees.series.henry_hub_vol },
                    ],
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe volatilite :", erreur));
});
