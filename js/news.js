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
const JOURS = { jour: 1, semaine: 7, mois: 30, tout: 100000 };

let tousLesArticles = [];
let periodeActive = "tout";
const filtresCommodite = new Set();

function commoditesDe(titre) {
    const t = (titre || "").toLowerCase();
    const trouvees = [];
    for (const [com, mots] of Object.entries(MOTS)) {
        if (mots.some(m => t.includes(m))) trouvees.push(com);
    }
    return trouvees;
}

function afficher() {
    const conteneur = document.getElementById("liste-news");
    conteneur.innerHTML = "";

    const limite = Date.now() - JOURS[periodeActive] * 24 * 3600 * 1000;

    const articles = tousLesArticles.filter(a => {
        // Filtre periode
        if (periodeActive !== "tout") {
            const d = a.date ? new Date(a.date).getTime() : 0;
            if (d < limite) return false;
        }
        // Filtre commodite (aucun = tout)
        if (filtresCommodite.size > 0 && !a.commodites.some(c => filtresCommodite.has(c))) {
            return false;
        }
        return true;
    });

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
        const icones = article.commodites.map(c => ICONES[c]).join(" ");
        meta.textContent = article.source + (date ? " · " + date : "") + (icones ? " · " + icones : "");

        corps.appendChild(lien);
        corps.appendChild(meta);
        bloc.appendChild(corps);
        conteneur.appendChild(bloc);
    }
}

// Filtre PERIODE (un seul actif a la fois)
document.querySelectorAll("#filtres-periode .news-filtre").forEach(bouton => {
    bouton.addEventListener("click", () => {
        periodeActive = bouton.dataset.periode;
        document.querySelectorAll("#filtres-periode .news-filtre")
            .forEach(b => b.classList.remove("actif"));
        bouton.classList.add("actif");
        afficher();
    });
});

// Filtre COMMODITE (plusieurs cumulables)
document.querySelectorAll("#filtres-commodite .news-filtre").forEach(bouton => {
    bouton.addEventListener("click", () => {
        const com = bouton.dataset.com;
        if (filtresCommodite.has(com)) {
            filtresCommodite.delete(com);
            bouton.classList.remove("actif");
        } else {
            filtresCommodite.add(com);
            bouton.classList.add("actif");
        }
        afficher();
    });
});

window.addEventListener("load", () => {
    fetch("data/news.json")
        .then(reponse => reponse.json())
        .then(donnees => {
            tousLesArticles = (donnees.articles || []).map(a => ({
                ...a,
                commodites: commoditesDe(a.titre),
            }));
            afficher();
        })
        .catch(erreur => {
            document.getElementById("liste-news").textContent = "Actualités indisponibles.";
            console.error("Erreur News :", erreur);
        });
});
