// Mots-cles pour reconnaitre la commodite dans un titre
const MOTS = {
    petrole: ["oil", "crude", "brent", "wti", "petrol", "pétrole", "opec", "opep",
              "baril", "barrel", "refin", "raffin", "shale", "drill", "offshore", "upstream"],
    gaz: ["gas", "gaz", "lng", "gnl", "ttf", "henry hub", "pipeline", "methane", "méthane"],
    electricite: ["electric", "électric", "power", "grid", "réseau", "renewable", "renouvelable",
                  "solar", "solaire", "wind", "éolien", "eolien", "nuclear", "nucléaire",
                  "utility", "utilities"],
};

const ICONES = { petrole: "🛢️", gaz: "🔥", electricite: "⚡" };

let tousLesArticles = [];
const filtresActifs = new Set();

// Renvoie la liste des commodites detectees dans un titre
function commoditesDe(titre) {
    const t = (titre || "").toLowerCase();
    const trouvees = [];
    for (const [com, mots] of Object.entries(MOTS)) {
        if (mots.some(m => t.includes(m))) trouvees.push(com);
    }
    return trouvees;
}

// (Re)construit la liste selon les filtres actifs
function afficher() {
    const conteneur = document.getElementById("liste-news");
    conteneur.innerHTML = "";

    const articles = tousLesArticles.filter(a => {
        if (filtresActifs.size === 0) return true;               // aucun filtre = tout
        return a.commodites.some(c => filtresActifs.has(c));     // sinon, au moins une commodite active
    });

    if (articles.length === 0) {
        conteneur.textContent = "Aucun article pour ce filtre.";
        return;
    }

    for (const article of articles) {
        const bloc = document.createElement("div");
        bloc.className = "news-item";

        // Vignette (si disponible)
        if (article.image) {
            const img = document.createElement("img");
            img.className = "news-image";
            img.src = article.image;
            img.loading = "lazy";
            img.onerror = () => img.remove();   // image cassee -> on la retire
            bloc.appendChild(img);
        }

        const corps = document.createElement("div");
        corps.className = "news-corps";

        const lien = document.createElement("a");
        lien.href = article.lien;
        lien.target = "_blank";
        lien.rel = "noopener";
        lien.className = "news-titre";
        lien.textContent = article.titre;

        const meta = document.createElement("div");
        meta.className = "news-meta";
        const date = article.date ? new Date(article.date).toLocaleDateString("fr-FR") : "";
        const icones = article.commodites.map(c => ICONES[c]).join(" ");
        meta.textContent = article.source + (date ? " · " + date : "") + (icones ? " · " + icones : "");

        corps.appendChild(lien);
        corps.appendChild(meta);
        bloc.appendChild(corps);
        conteneur.appendChild(bloc);
    }
}

// Boutons de filtre
document.querySelectorAll(".news-filtre").forEach(bouton => {
    bouton.addEventListener("click", () => {
        const com = bouton.dataset.com;
        if (filtresActifs.has(com)) {
            filtresActifs.delete(com);
            bouton.classList.remove("actif");
        } else {
            filtresActifs.add(com);
            bouton.classList.add("actif");
        }
        afficher();
    });
});

window.addEventListener("load", () => {
    fetch("/api/news")
        .then(reponse => reponse.json())
        .then(donnees => {
            tousLesArticles = (donnees.articles || []).map(a => ({
                ...a,
                commodites: commoditesDe(a.titre),
            }));
            afficher();
        })
        .catch(erreur => {
            document.getElementById("liste-news").textContent =
                "Actualités indisponibles (la fonction /api/news ne répond qu'en ligne sur Vercel, pas en local).";
            console.error("Erreur News :", erreur);
        });
});
