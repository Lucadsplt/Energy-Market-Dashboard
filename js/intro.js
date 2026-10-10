// Animation d'introduction du logo Luceo.
// Port en JavaScript pur du film d'animation : mêmes coordonnées (planche de 2000 x 729),
// même chorégraphie, mais sans le moteur d'origine (léger, rien à installer).
(() => {
    const IMAGE = "assets/intro/luceo-horizontal-slogan-sombre.png";
    const VERT = "#13b981";
    const BARRE = "#f0f9f5";

    // Découpe du mot « luceo » (une tranche par lettre), en px de la planche
    const LETTRES = [[752, 832], [866, 1100], [1118, 1360], [1362, 1624], [1630, 1906]];

    // Mise à l'échelle du logo dans la scène de 1920 x 1080
    const K = 0.7;
    const BOX_L = 960 - 1000 * K;
    const BOX_T = 540 - 364.5 * K + 34 * K;    // sans slogan, le logo est un peu descendu pour rester centré

    // Repères de temps, en secondes (les scènes du film : Lumière, Symbole, Signature, puis le logo tient)
    const SYMBOLE = 1.2, SIGNATURE = 2.0;
    const FIN = 3.6;    // l'animation s'arrête ici et le logo reste affiché
    const DUREE_FILM = 5.2;

    // --- Courbes d'accélération ---
    const courbe = {
        sortieCubique: t => 1 - Math.pow(1 - t, 3),
        entreeSortieCubique: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
        rebond: t => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
    };
    // Valeur qui passe de a à b entre les instants t0 et t1 (bornée en dehors)
    const anime = (f, a, b, t0, t1, T) => {
        const p = Math.min(1, Math.max(0, (T - t0) / (t1 - t0)));
        return a + (b - a) * f(p);
    };

    // --- Construction des éléments ---
    const el = (parent, css, tag = "div") => {
        const e = document.createElement(tag);
        e.style.cssText = css;
        parent.appendChild(e);
        return e;
    };
    const tranche = (parent, a, haut, hauteur, b) => {    // fenêtre qui ne montre qu'une partie de la planche
        const fenetre = el(parent, `position:absolute;left:${a}px;top:${haut}px;width:${b - a}px;height:${hauteur}px;overflow:hidden`);
        const img = el(fenetre, `position:absolute;left:${-a}px;top:${-haut}px;width:2000px;height:729px`, "img");
        img.src = IMAGE;
        img.alt = "";
        return { fenetre, img };
    };

    const stage = document.getElementById("stage");
    const choix = document.getElementById("choix");
    const passer = document.getElementById("passer");

    const piece = el(stage, "position:absolute;inset:0");
    const boite = el(piece, `position:absolute;left:${BOX_L}px;top:${BOX_T}px;width:2000px;height:729px;transform:scale(${K});transform-origin:0 0`);
    boite.setAttribute("role", "img");
    boite.setAttribute("aria-label", "Luceo");

    const lettres = LETTRES.map(([a, b]) => tranche(boite, a, 80, 420, b));

    // Le symbole : un point de lumière, un quart de cercle, puis la barre
    const symbole = el(boite, "position:absolute;left:0;top:0;width:2000px;height:729px;transform-origin:368.5px 364px");
    const halo = el(symbole, `position:absolute;left:80px;top:301px;width:520px;height:520px;border-radius:50%;background:radial-gradient(circle at 50% 50%, ${VERT}55, transparent 62%);opacity:0`);
    const point = el(symbole, `position:absolute;left:326px;top:547px;width:28px;height:28px;border-radius:50%;background:${VERT};box-shadow:0 0 40px ${VERT}`);
    const quart = el(symbole, "position:absolute;left:340px;top:356px;width:205px;height:205px;border-top-right-radius:205px");
    const barre = el(symbole, `position:absolute;left:192px;top:167px;width:114px;height:394px;background:${BARRE};transform-origin:50% 100%`);

    // --- Dessin d'une image, en fonction du seul temps T ---
    function dessiner(T) {
        const point_ = anime(courbe.rebond, 0, 1, 0.15, 0.5, T) * (1 - anime(courbe.sortieCubique, 0, 1, 0.5, 0.75, T));
        const balayage = anime(courbe.entreeSortieCubique, 0, 90, 0.45, 1.2, T);
        const hauteurBarre = anime(courbe.rebond, 0, 1, SYMBOLE + 0.05, SYMBOLE + 0.6, T);
        const lueur = anime(courbe.sortieCubique, 0, 1, 0.4, 1.2, T) * (1 - anime(courbe.sortieCubique, 0, 1, SIGNATURE, SIGNATURE + 0.8, T));
        const trajet = anime(courbe.entreeSortieCubique, 0, 1, SIGNATURE, SIGNATURE + 0.8, T);

        // le symbole glisse du centre vers sa place dans le logo
        const dx = (1 - trajet) * ((960 - (BOX_L + 368.5 * K)) / K);
        symbole.style.transform = `translate(${dx}px,0) scale(${1.7 - 0.7 * trajet})`;
        halo.style.opacity = lueur * 0.8;
        point.style.transform = `scale(${point_})`;
        quart.style.background = `conic-gradient(from 0deg at 0% 100%, ${VERT} 0deg ${balayage}deg, transparent ${balayage}deg)`;
        barre.style.transform = `scaleY(${hauteurBarre})`;

        // les lettres montent l'une après l'autre
        lettres.forEach((l, i) => {
            const t0 = SIGNATURE + 0.4 + i * 0.09;
            const p = anime(courbe.sortieCubique, 0, 1, t0, t0 + 0.55, T);
            l.img.style.transform = `translate(0,${(1 - p) * 420}px)`;
        });

        piece.style.transform = `scale(${1 + 0.035 * (T / DUREE_FILM)})`;    // très léger zoom pendant tout le film
    }

    // --- Mise à l'échelle de la scène dans la fenêtre ---
    function ajuster() {
        const s = Math.min(window.innerWidth / 1500, window.innerHeight / 900, 1);
        stage.style.transform = `translate(-50%,-50%) scale(${s})`;
        choix.style.top = `calc(50% + ${250 * s}px)`;
    }
    window.addEventListener("resize", ajuster);
    ajuster();

    // --- Lancement ---
    let depart = null;
    let termine = false;
    function terminer() {
        if (termine) return;
        termine = true;
        dessiner(FIN);
        passer.classList.add("cache");
        choix.classList.add("visible");
    }

    function boucle(maintenant) {
        if (termine) return;
        if (depart === null) depart = maintenant;
        const T = Math.min((maintenant - depart) / 1000, FIN);
        dessiner(T);
        if (T >= FIN) terminer(); else requestAnimationFrame(boucle);
    }

    passer.addEventListener("click", terminer);

    const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduit) {
        terminer();                                  // pas d'animation : on affiche directement le logo final
    } else {
        dessiner(0);
        const image = new Image();                   // on attend que la planche soit chargée avant de démarrer
        image.onload = image.onerror = () => requestAnimationFrame(boucle);
        image.src = IMAGE;
    }
})();
