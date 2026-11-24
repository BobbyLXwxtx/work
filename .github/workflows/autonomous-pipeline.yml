name: Autonomous Daily Feed & Deploy

on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:

jobs:
  etl-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run unit and schema tests
        run: python3 -m unittest discover -s tests -v

      - name: Fetch, normalize, and build static storefront
        env:
          DIST_DIR: dist
          POLAR_CHECKOUT_URL: ${{ vars.POLAR_CHECKOUT_URL || 'https://polar.sh/' }}
        run: python3 src/etl/fetch_and_normalize.py

      - name: Deploy to Cloudflare Pages (optional)
        if: ${{ secrets.CLOUDFLARE_API_TOKEN != '' }}
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name=autonomous-feed
