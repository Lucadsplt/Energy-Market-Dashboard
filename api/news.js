const Parser = require("rss-parser");
const parser = new Parser({ timeout: 8000 });

// Les sources RSS (on en ajoutera d'autres plus tard)
const FLUX = [
    { source: "EIA", url: "https://www.eia.gov/rss/todayinenergy.xml" },
    { source: "OilPrice", url: "https://oilprice.com/rss/main" },
];

module.exports = async (req, res) => {
    const articles = [];

    // On interroge tous les flux en parallele
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
            // Un flux qui ne repond pas est ignore, pas de plantage
        }
    }));

    // Tri du plus recent au plus ancien
    articles.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Cache 30 min cote Vercel (evite de re-interroger les flux a chaque visite)
    res.setHeader("Cache-Control", "s-maxage=1800, stale-while-revalidate");
    res.status(200).json({ articles });
};