from . import amazon, apple, ashby, goldman_sachs, google, greenhouse, lever, microsoft, tiktok, workday

CONNECTORS = {
    "greenhouse": greenhouse.fetch,
    "ashby": ashby.fetch,
    "google": google.fetch,
    "amazon": amazon.fetch,
    "workday": workday.fetch,
    "lever": lever.fetch,
    "goldman_sachs": goldman_sachs.fetch,
    "microsoft": microsoft.fetch,
    "tiktok": tiktok.fetch,
    "apple": apple.fetch,
}
