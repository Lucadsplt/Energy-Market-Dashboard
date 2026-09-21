const Parser = require("rss-parser");
const parser = new Parser({ timeout: 8000 });

const FLUX = [
    { source: "EIA", url: "https://www.eia.gov/rss/todayinenergy.xml" },
    { source: "OilPrice", url: "https://oilprice.com/rss/main" },
    { source: "Rigzone", url: "https://www.rigzone.com/news/rss/rigzone_latest.aspx" },
];

const UA = "Mozilla/5.0 (compatible; EnergyDashboard/1.0)";

// Recupere l'image d'apercu (og:image) de la page d'un article
async function recupererImage(url) {
    try {
        const resp = await fetch(url, {
            headers: { "User-Agent": UA },
            signal: AbortSignal.timeout(5000),
        });
        const html = await resp.text();
        const balise = html.match(/<meta[^>]+(?:property|name)=["']og:image["'][^>]*>/i);
        if (!balise) return null;
        const contenu = balise[0].match(/content=["']([^"']+)["']/i);
        return contenu ? contenu[1] : null;
    } catch (e) {
        return null;   // page injoignable ou sans image
    }
}

module.exports = async (req, res) => {
    let articles = [];

    // 1. Recuperer les flux RSS en parallele
    await Promise.all(FLUX.map(async (flux) => {
        try {
            const feed = await parser.parseURL(flux.url);
            for (const item of feed.items.slice(0, 8)) {
                articles.push({
                    source: flux.source,
                    titre: item.title,
                    lien: item.link,
                    date: item.isoDate || item.pubDate || null,
                });
            }
        } catch (e) {
            // un flux qui ne repond pas est ignore
        }
    }));

    // 2. Trier du plus recent au plus ancien, garder les 12 premiers
    articles.sort((a, b) => new Date(b.date) - new Date(a.date));
    articles = articles.slice(0, 12);

    // 3. Recuperer l'image d'apercu de chaque article, en parallele
    await Promise.all(articles.map(async (a) => {
        a.image = await recupererImage(a.lien);
    }));

    res.setHeader("Cache-Control", "s-maxage=1800, stale-while-revalidate");
    res.status(200).json({ articles });
};
