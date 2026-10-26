// Onglet Idées : fiche par marché (indicateurs + fiabilité statistique, actualités, dimensionnement d'un trade en simulation).
// Tout est lu dans data/idees.json, produit par pipeline/analysis/idees.py : aucun calcul d'analyse ici, seulement le dimensionnement.
(() => {
    const LECTURES = {
        haussier: "Haussier", baissier: "Baissier", neutre: "Neutre", contexte: "Contexte",
    };
    const FIABILITES = {
        demontre: ["demontre", "Démontré"],
        non_demontre: ["non-demontre", "Non démontré"],
        artefact: ["artefact", "Probable artefact"],
        non_teste: ["non-teste", "Non testé"],
    };
    const AUCUN_CONTRAT = {
        electricite: "Aucun contrat d'électricité n'apparaît dans la liste Énergie du simulateur CME : cette fiche reste une lecture de marché.",
    };

    const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const fr = (x, d = 2) => Number(x).toFixed(d).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    const frSimple = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");

    let donnees = null;
    let marche = "petrole";

    // ---------------------------------------------------------------- lecture d'ensemble
    function dessinerSynthese(m) {
        const s = m.synthese;
        document.getElementById("idees-kpi").innerHTML = `
            <div class="kpi-idee"><span class="chiffre haut">${s.haussiers}</span><span class="legende">règle${s.haussiers > 1 ? "s" : ""} acheteuse${s.haussiers > 1 ? "s" : ""}</span></div>
            <div class="kpi-idee"><span class="chiffre bas">${s.baissiers}</span><span class="legende">règle${s.baissiers > 1 ? "s" : ""} vendeuse${s.baissiers > 1 ? "s" : ""}</span></div>
            <div class="kpi-idee"><span class="chiffre">${s.neutres}</span><span class="legende">hors marché</span></div>
            <div class="kpi-idee"><span class="chiffre">${s.regles_demontrees}</span><span class="legende">démontrée${s.regles_demontrees > 1 ? "s" : ""} sur ${s.regles_comptees}</span></div>`;
        document.getElementById("idees-phrase").textContent = m.phrase;
    }

    // ---------------------------------------------------------------- tableau des indicateurs
    function dessinerTableau(m) {
        const lignes = m.indicateurs.map(i => {
            const [classe, texte] = FIABILITES[i.fiabilite] || FIABILITES.non_teste;
            return `<tr>
                <td><b>${esc(i.nom)}</b>${i.compte ? "" : '<span class="sous-ligne">information de contexte</span>'}</td>
                <td class="etat">${esc(i.valeur)}</td>
                <td><span class="badge lecture ${i.lecture}">${LECTURES[i.lecture]}</span></td>
                <td><span class="badge ${classe}">${texte}</span></td>
                <td class="etat">${esc(i.detail)}</td></tr>`;
        }).join("");
        document.getElementById("idees-table").innerHTML =
            `<tr><th>Indicateur</th><th>Valeur actuelle</th><th>Lecture</th><th>Fiabilité statistique</th><th>Détail</th></tr>${lignes}`;
    }

    // ---------------------------------------------------------------- actualités
    function dessinerActualites(m) {
        const a = m.actualites;
        const ratio = a.ratio_vs_rythme === null ? "" : ` (${frSimple(a.ratio_vs_rythme, 2)} fois le rythme habituel)`;
        document.getElementById("idees-actu-sous").textContent = `${a.nb_24h} en 24 h · ${a.nb_7j} en 7 jours${ratio}`;
        const zone = document.getElementById("idees-actu");
        if (!a.derniers.length) { zone.innerHTML = '<p class="note">Aucun article récent.</p>'; return; }
        zone.innerHTML = a.derniers.map(x => {
            const d = new Date(x.date);
            const quand = d.toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
            const lien = /^https?:\/\//.test(x.lien || "") ? x.lien : null;
            const titre = lien ? `<a href="${esc(lien)}" target="_blank" rel="noopener noreferrer">${esc(x.titre)}</a>` : esc(x.titre);
            return `<div class="actu-idee">${titre}<span class="sous-ligne">${esc(x.source || "")} · ${quand}</span></div>`;
        }).join("") +
            '<p class="note">Le volume d\'articles mesure l\'attention portée au marché, pas le sens du prix. Le ton des articles n\'est pas analysé.</p>';
    }

    // ---------------------------------------------------------------- dimensionnement d'un trade
    function dessinerCalculateur(m) {
        const zone = document.getElementById("idees-calc");
        if (!m.instruments.length) {
            zone.innerHTML = `<p class="note">${esc(AUCUN_CONTRAT[marche] || "Aucun instrument disponible pour ce marché.")}</p>`;
            return;
        }
        zone.innerHTML = `
            <div class="calc">
                <label>Instrument <select id="calc-instrument" class="menu">${m.instruments.map((x, k) => `<option value="${k}">${esc(x.nom)} (${esc(x.code)})</option>`).join("")}</select></label>
                <label>Capital du simulateur ($) <input id="calc-capital" type="number" min="1000" step="1000" value="100000"></label>
                <label>Risque maximal par trade (%) <input id="calc-risque" type="number" min="0.1" max="5" step="0.1" value="1"></label>
                <label>Distance du stop <small id="calc-unite"></small> <input id="calc-stop" type="number" min="0.001" step="0.01"></label>
                <label>Distance de l'objectif <input id="calc-objectif" type="number" min="0.001" step="0.01"></label>
                <label>Valeur d'1,00 de variation ($) <input id="calc-mult" type="number" min="1" step="1"></label>
            </div>
            <dl class="stats" id="calc-resultat"></dl>
            <p class="note" id="calc-note"></p>`;

        const el = id => document.getElementById(id);
        const instrument = () => m.instruments[Number(el("calc-instrument").value)];

        function proposer() {                       // stop par défaut : 2 fois le mouvement quotidien typique
            const x = instrument();
            el("calc-unite").textContent = `(${x.unite})`;
            el("calc-mult").value = x.multiplicateur;
            if (x.prix && x.sigma_quotidien_pct) {
                const stop = 2 * x.sigma_quotidien_pct / 100 * x.prix;
                const decimales = stop < 1 ? 3 : 2;
                el("calc-stop").value = stop.toFixed(decimales);
                el("calc-objectif").value = (stop * 1.5).toFixed(decimales);
            }
            calculer();
        }

        function calculer() {
            const x = instrument();
            const capital = Number(el("calc-capital").value), pct = Number(el("calc-risque").value);
            const stop = Number(el("calc-stop").value), objectif = Number(el("calc-objectif").value), mult = Number(el("calc-mult").value);
            if (!(capital > 0 && pct > 0 && stop > 0 && mult > 0)) { el("calc-resultat").innerHTML = ""; return; }
            const risque = capital * pct / 100;
            const perte = stop * mult;
            const nb = Math.floor(risque / perte);
            const lignes = [
                ["Risque accepté", `${fr(risque, 0)} $`],
                ["Perte par contrat si le stop est touché", `${fr(perte, 0)} $`],
                ["Nombre maximal de contrats", `<b>${nb}</b>`],
            ];
            if (nb > 0) {
                lignes.push(["Perte totale au stop", `${fr(nb * perte, 0)} $`]);
                if (objectif > 0) lignes.push(["Gain total à l'objectif", `${fr(nb * objectif * mult, 0)} $ (rapport gain / risque : ${frSimple(objectif / stop, 2)})`]);
                if (x.prix) lignes.push(["Valeur du contrat au prix actuel", `${fr(nb * x.prix * mult, 0)} $`]);
            }
            el("calc-resultat").innerHTML = lignes.map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("");
            el("calc-note").innerHTML = (nb === 0
                ? "<b>Un seul contrat dépasse déjà le risque accepté.</b> Choisis un micro-contrat, un stop plus proche, ou un risque plus élevé en connaissance de cause. "
                : "") +
                `Stop proposé : 2 fois le mouvement quotidien typique (${frSimple(x.sigma_quotidien_pct || 0, 2)} % du prix, prix de référence ${x.prix ? frSimple(x.prix, 2) : "n.d."}). ` +
                "Les valeurs par contrat sont à confirmer dans la fiche produit du simulateur. Le dimensionnement fixe le risque, il ne dit pas dans quel sens trader.";
        }

        // on démarre sur le plus petit contrat : c'est celui qui convient à un capital de simulation de 100 000 $
        const plusPetit = m.instruments.reduce((k, x, i, tab) => (x.multiplicateur < tab[k].multiplicateur ? i : k), 0);
        el("calc-instrument").value = String(plusPetit);

        el("calc-instrument").addEventListener("change", proposer);
        ["calc-capital", "calc-risque", "calc-stop", "calc-objectif", "calc-mult"].forEach(id => el(id).addEventListener("input", calculer));
        proposer();
    }

    // ---------------------------------------------------------------- page
    function afficher(cle) {
        marche = cle;
        const m = donnees.marches[cle];
        dessinerSynthese(m);
        dessinerTableau(m);
        dessinerActualites(m);
        dessinerCalculateur(m);
    }

    window.addEventListener("load", () => {
        fetch("data/idees.json", { cache: "no-cache" })
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(d => {
                donnees = d;
                const genere = new Date(d.genere);
                document.getElementById("idees-genere").textContent =
                    "Fiche générée le " + genere.toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
                document.getElementById("idees-marche").addEventListener("change", e => afficher(e.target.value));
                afficher("petrole");
            })
            .catch(e => {
                console.error("Idées :", e);
                document.getElementById("idees-phrase").textContent = "La fiche n'a pas pu être chargée.";
            });
    });
})();
