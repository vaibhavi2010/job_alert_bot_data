from . import amazon, ashby, goldman_sachs, google, greenhouse, jpmorgan, lever, microsoft, tiktok, workday

CONNECTORS = {
    "greenhouse": greenhouse.fetch,
    "ashby": ashby.fetch,
    "google": google.fetch,
    "amazon": amazon.fetch,
    "workday": workday.fetch,
    "lever": lever.fetch,
    "goldman_sachs": goldman_sachs.fetch,
    "jpmorgan": jpmorgan.fetch,
    "microsoft": microsoft.fetch,
    "tiktok": tiktok.fetch,
}
