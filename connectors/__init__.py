from . import (
    amazon, apple, ashby, eightfold, goldman_sachs, google, greenhouse, ibm, icims,
    lever, microsoft, oracle_hcm, smartrecruiters, tiktok, workday,
)

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
    "eightfold": eightfold.fetch,
    "oracle_hcm": oracle_hcm.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "icims": icims.fetch,
    "ibm": ibm.fetch,
}
