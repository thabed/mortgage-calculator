from . import landsbankinn, arion, islandsbanki, audur, almenni, bru

ALL_SCRAPERS = [
    landsbankinn.scrape,
    arion.scrape,
    islandsbanki.scrape,
    audur.scrape,
    almenni.scrape,
    bru.scrape,
]
