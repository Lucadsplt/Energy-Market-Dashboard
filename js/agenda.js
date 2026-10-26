// Volet Agenda de l'onglet News : événements à venir (banques centrales, OPEP+, politique, climat) et publications hebdomadaires.
// Données : data/agenda.json (pipeline/analysis/agenda.py). Les événements passés sont masqués ici, à chaque affichage.
(() => {
    const TYPES = { banque_centrale: "Banque centrale", opep: "OPEP+", politique: "Politique", climat: "Climat" };
    const MARCHES = { petrole: "Pétrole", gaz: "Gaz", electricite: "Électricité" };
    const IMPORTANCES = { haute: "Haute", moyenne: "Moyenne", faible: "Faible" };

    const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const FUSEAU = "Europe/Paris";

    let agenda = null;

    function debutEtFin(e) {
        if (e.quand) { const d = new Date(e.quand); return { debut: d, fin: new Date(d.getTime() + 3 * 3600e3), heure: true }; }
        const debut = new Date(e.jour + "T00:00:00Z");
        const fin = new Date((e.fin_jour || e.jour) + "T00:00:00Z");
        fin.setUTCDate(fin.getUTCDate() + 1);
        return { debut, fin, heure: false };
    }

    function quand(e) {
        const { debut, heure } = debutEtFin(e);
        if (heure) {
            return debut.toLocaleString("fr-FR", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: FUSEAU });
        }
        const jour = d => d.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
        if (e.fin_jour && e.fin_jour !== e.jour) {
            const f = new Date(e.fin_jour + "T00:00:00Z");
            return `du ${jour(debut)} au ${jour(f)}`;
        }
        return jour(debut);
    }

    function dans(e, maintenant) {
        const { debut, fin } = debutEtFin(e);
        if (maintenant >= debut && maintenant < fin) return "en cours";
        const jours = Math.ceil((debut - maintenant) / 86400e3);
        if (debut - maintenant < 0) return "aujourd'hui";
        if (jours <= 0) return "aujourd'hui";
        if (jours === 1) return "demain";
        return `dans ${jours} jours`;
    }

    function dessinerEvenements() {
        const marche = document.getElementById("agenda-marche").value;
        const type = document.getElementById("agenda-type").value;
        const maintenant = new Date();
        const liste = agenda.evenements.filter(e => debutEtFin(e).fin >= maintenant &&
            (!marche || e.marches.includes(marche)) && (!type || e.type === type));

        const zone = document.getElementById("agenda-table");
        if (!liste.length) {
            const aucun = agenda.evenements.every(e => debutEtFin(e).fin < maintenant);
            zone.innerHTML = `<tr><td>${aucun ? "Plus aucun événement à venir dans l'agenda : il doit être mis à jour." : "Aucun événement ne correspond à ces filtres."}</td></tr>`;
            return;
        }
        zone.innerHTML = `<tr><th>Quand</th><th></th><th>Événement</th><th>Type</th><th>Marchés</th><th>Importance</th><th>Statut</th><th>Source</th></tr>` +
            liste.map(e => {
                const source = /^https:\/\//.test(e.lien || "") ? `<a href="${esc(e.lien)}" target="_blank" rel="noopener noreferrer">${esc(e.source)}</a>` : esc(e.source);
                return `<tr>
                    <td class="quand">${esc(quand(e))}</td>
                    <td class="dans">${dans(e, maintenant)}</td>
                    <td class="etat"><b>${esc(e.titre)}</b><span class="sous-ligne">${esc(e.note)}</span></td>
                    <td>${TYPES[e.type]}</td>
                    <td>${e.marches.map(m => `<span class="tag-marche">${MARCHES[m]}</span>`).join(" ")}</td>
                    <td><span class="badge imp-${e.importance}">${IMPORTANCES[e.importance]}</span></td>
                    <td><span class="badge ${e.statut === "confirme" ? "demontre" : "artefact"}">${e.statut === "confirme" ? "Confirmé" : "À confirmer"}</span></td>
                    <td class="etat">${source}</td></tr>`;
            }).join("");
    }

    function dessinerHebdomadaires() {
        const maintenant = new Date();
        const fmt = iso => new Date(iso).toLocaleString("fr-FR", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: FUSEAU });
        document.getElementById("agenda-hebdo").innerHTML =
            `<tr><th>Rendez-vous</th><th>Prochaines dates (heure de Paris)</th><th>Marchés</th><th>Source</th></tr>` +
            agenda.hebdomadaires.map(h => {
                const prochaines = h.prochaines.filter(d => new Date(d) >= maintenant);
                return `<tr><td class="etat"><b>${esc(h.titre)}</b><span class="sous-ligne">${esc(h.note)}</span></td>
                    <td class="quand">${prochaines.map(fmt).map(esc).join("<br>") || "n.d."}</td>
                    <td>${h.marches.map(m => `<span class="tag-marche">${MARCHES[m]}</span>`).join(" ")}</td>
                    <td class="etat"><a href="${esc(h.lien)}" target="_blank" rel="noopener noreferrer">Calendrier officiel</a></td></tr>`;
            }).join("");
    }

    window.addEventListener("load", () => {
        fetch("data/agenda.json", { cache: "no-cache" })
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(d => {
                agenda = d;
                const verif = new Date(d.verifie_le + "T00:00:00Z").toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
                document.getElementById("agenda-verif").textContent = `Dates vérifiées le ${verif} auprès des sources indiquées.`;
                ["agenda-marche", "agenda-type"].forEach(id => document.getElementById(id).addEventListener("change", dessinerEvenements));
                dessinerEvenements();
                dessinerHebdomadaires();
                document.addEventListener("volet-affiche", e => { if (e.detail.page === "news" && e.detail.volet === "agenda") { dessinerEvenements(); dessinerHebdomadaires(); } });
            })
            .catch(e => {
                console.error("Agenda :", e);
                document.getElementById("agenda-table").innerHTML = "<tr><td>L'agenda n'a pas pu être chargé.</td></tr>";
            });
    });
})();
