#!/usr/bin/env python3
"""Mint an API key for a partner organization (relief org, church, consulate).

Run on the server (same DB_PATH as the bot):
    python scripts/make_partner_key.py "Direct Relief"

Give the printed key to the org; they paste it into the org portal to see the
needs heatmap, claim needs, and push live shelter/clinic capacity.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import matching as M  # noqa: E402
from app import partners       # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python scripts/make_partner_key.py "Org Name"')
    name = sys.argv[1]
    M.init_db()
    key = partners.create_partner(name, verified=True)
    print(f"Partner created: {name}")
    print(f"API key (share privately): {key}")


if __name__ == "__main__":
    main()
