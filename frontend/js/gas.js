window.addEventListener("load", () => {
    fetch("../data/gas.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            const canvas = document.getElementById("graphique-gaz");
            new Chart(canvas, {
                type: "line",
                data: {
                    labels: donnees.dates,
                    datasets: [
                        {
                            label: "Gaz Europe (TTF, €/MWh)",
                            data: donnees.series.ttf,
                            yAxisID: "y",
                        },
                        {
                            label: "Gaz US (Henry Hub, $/MMBtu)",
                            data: donnees.series.henry_hub,
                            yAxisID: "y2",
                        },
                    ],
                },
                options: {
                    scales: {
                        y: {
                            position: "left",
                            title: { display: true, text: "TTF (€/MWh)" },
                        },
                        y2: {
                            position: "right",
                            title: { display: true, text: "Henry Hub ($/MMBtu)" },
                            grid: { drawOnChartArea: false },
                        },
                    },
                },
            });
        })
        .catch(erreur => console.error("Erreur de chargement du graphe :", erreur));
});