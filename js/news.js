// Mots-cles pour reconnaitre le marche dans un titre
const MOTS = {
    petrole: ["oil", "crude", "brent", "wti", "petrol", "pétrole", "opec", "opep",
              "baril", "barrel", "refin", "raffin", "shale", "drill", "offshore", "upstream"],
    gaz: ["gas", "gaz", "lng", "gnl", "ttf", "henry hub", "pipeline", "methane", "méthane"],
    electricite: ["electric", "électric", "power", "grid", "réseau", "renewable", "renouvelable",
                  "solar", "solaire", "wind", "éolien", "eolien", "nuclear", "nucléaire",
                  "utility", "utilities"],
};

const NOMS_MARCHES = { petrole: "Pétrole", gaz: "Gaz", electricite: "Électricité" };
const JOURS = { jour: 1, semaine: 7, mois: 30, tout: 100000 };

let tousLesArticles = [];

function marchesDe(titre) {
    const t = (titre || "").toLowerCase();
    return Object.keys(MOTS).filter(m => MOTS[m].some(mot => t.includes(mot)));
}

// Lit l'état des trois menus déroulants et affiche les articles correspondants
function afficher() {
    const periode = document.getElementById("filtre-periode").value;
    const marche = document.getElementById("filtre-marche").value;
    const source = document.getElementById("filtre-source").value;
    const conteneur = document.getElementById("liste-news");
    const limite = Date.now() - JOURS[periode] * 24 * 3600 * 1000;

    const articles = tousLesArticles.filter(a => {
        if (periode !== "tout" && (a.date ? new Date(a.date).getTime() : 0) < limite) return false;
        if (marche && !a.marches.includes(marche)) return false;
        if (source && a.source !== source) return false;
        return true;
    });

    document.getElementById("compte-news").textContent =
        articles.length + (articles.length > 1 ? " articles" : " article");
    conteneur.innerHTML = "";

    if (articles.length === 0) {
        conteneur.textContent = "Aucun article pour ces filtres.";
        return;
    }

    for (const article of articles) {
        const bloc = document.createElement("div");
        bloc.className = "news-item";

        if (article.image) {
            const img = document.createElement("img");
            img.className = "news-image";
            img.src = article.image;
            img.loading = "lazy";
            img.onerror = () => img.remove();
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
        const marches = article.marches.map(m => NOMS_MARCHES[m]).join(", ");
        meta.textContent = [article.source, date, marches].filter(Boolean).join(" · ");

        corps.appendChild(lien);
        corps.appendChild(meta);
        bloc.appendChild(corps);
        conteneur.appendChild(bloc);
    }
}

window.addEventListener("load", () => {
    ["filtre-periode", "filtre-marche", "filtre-source"].forEach(id =>
        document.getElementById(id).addEventListener("change", afficher));

    fetch("data/news.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            tousLesArticles = (donnees.articles || []).map(a => ({ ...a, marches: marchesDe(a.titre) }));

            // Les sources proposées dans le menu viennent des données elles-mêmes
            const sources = [...new Set(tousLesArticles.map(a => a.source))].sort();
            const menu = document.getElementById("filtre-source");
            sources.forEach(nom => menu.add(new Option(nom, nom)));

            afficher();
        })
        .catch(erreur => {
            document.getElementById("liste-news").textContent = "Actualités indisponibles.";
            console.error("Erreur News :", erreur);
        });
});
