window.addEventListener("load", () => {
    fetch("/api/news")
        .then(reponse => reponse.json())
        .then(donnees => {
            const conteneur = document.getElementById("liste-news");
            conteneur.innerHTML = "";

            if (!donnees.articles || donnees.articles.length === 0) {
                conteneur.textContent = "Aucune actualité pour le moment.";
                return;
            }

            for (const article of donnees.articles) {
                const bloc = document.createElement("div");
                bloc.className = "news-item";

                const lien = document.createElement("a");
                lien.href = article.lien;
                lien.target = "_blank";
                lien.rel = "noopener";
                lien.className = "news-titre";
                lien.textContent = article.titre;

                const meta = document.createElement("div");
                meta.className = "news-meta";
                const date = article.date
                    ? new Date(article.date).toLocaleDateString("fr-FR")
                    : "";
                meta.textContent = article.source + (date ? " · " + date : "");

                bloc.appendChild(lien);
                bloc.appendChild(meta);
                conteneur.appendChild(bloc);
            }
        })
        .catch(erreur => {
            document.getElementById("liste-news").textContent =
                "Actualités indisponibles (la fonction /api/news ne répond qu'en ligne sur Vercel, pas en local).";
            console.error("Erreur News :", erreur);
        });
});
