// Affiche la date de la dernière mise à jour des données (écrite par le robot dans data/meta.json)
window.addEventListener("load", () => {
    const cible = document.getElementById("maj-site");
    if (!cible) return;
    fetch("data/meta.json", { cache: "no-cache" })
        .then(r => r.json())
        .then(m => {
            const date = new Date(m.maj);
            cible.textContent = "dernière mise à jour le " +
                date.toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
        })
        .catch(() => { cible.textContent = "mises à jour automatiques"; });
});
