from . import amazon, ashby, google, greenhouse

CONNECTORS = {
    "greenhouse": greenhouse.fetch,
    "ashby": ashby.fetch,
    "google": google.fetch,
    "amazon": amazon.fetch,
}
