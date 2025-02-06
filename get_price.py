import re
import pandas as pd
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

base_url = "https://yuyu-tei.jp/sell/poc/s/search?search_word=&rare="
rarities = ["UR", "HR", "SR", "SAR", "CSR", "SSR", "PROMO"]
csv_path = "/Users/vaibhavgupta/Desktop/pokemon_card_analysis/card_info/base_card_info.csv"
price_csv_path = "/Users/vaibhavgupta/Desktop/pokemon_card_analysis/card_info/card_price.csv"

# Get the current date in YYYYMMDD format for column naming
current_date = datetime.now().strftime("%Y%m%d")
price_column = f"p_{current_date}"

# The placeholder image for "under printing" cards
PLACEHOLDER_IMG_SRC = "https://img.yuyu-tei.jp/card_image/noimage_100_140.jpg"

async def scrape_price(playwright, rarity):
    """Scrape a single rarity page."""
    print(f"Scraping: {base_url + rarity}")

    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(base_url + rarity, timeout=60000)

    results_price = []
    results_info = []
    
    card_divs = await page.query_selector_all(".col-md")
    if not card_divs:
        print(f"No `div.col-md` elements found for rarity {rarity}. Skipping...")

    for card_div in card_divs:
        index_element = await card_div.query_selector("span.d-block.border.border-dark.p-1.w-100.text-center.my-2")
        index = await index_element.inner_text() if index_element else "N/A"
        
        price_element = await card_div.query_selector("strong.d-block.text-end")
        price = await price_element.inner_text() if price_element else "N/A"

        # Clean price: Remove "円" and commas, convert to integer
        clean_price = re.sub(r"[^\d]", "", price)  # Keep only digits
        clean_price = int(clean_price) if clean_price else 0  # Convert to int
        
        card_name_element = await card_div.query_selector("h4.text-primary.fw-bold")
        card_name = await card_name_element.inner_text() if card_name_element else "N/A"

        img_element = await card_div.query_selector("img.card.img-fluid")
        img_src = await img_element.get_attribute("src") if img_element else "N/A"

        results_price.append({
            "index": index,
            "card_name": card_name,
            "img_src": img_src,
            price_column: clean_price,  # Dynamically set the column name
        })
        
        results_info.append({
            "index": index,
            "rarity": rarity,
            "card_name": card_name,
            "img_src": img_src
        })

    await browser.close()
    print(f"Scraped {len(results_price)} cards for rarity {rarity}.")
    return results_price, results_info

async def scrape_all():
    """Runs all rarity scrapers asynchronously using Playwright."""
    async with async_playwright() as playwright:
        tasks = [scrape_price(playwright, rarity) for rarity in rarities]
        results = await asyncio.gather(*tasks)

        # Separate results into price and info lists
        results_price = [item[0] for item in results]  # Extract first part (price)
        results_info = [item[1] for item in results]  # Extract second part (info)

        # Flatten lists
        all_prices_flat = [card for sublist in results_price for card in sublist]
        all_info_flat = [card for sublist in results_info for card in sublist]

        df_price = pd.DataFrame(all_prices_flat)
        df_info = pd.DataFrame(all_info_flat)

        # Load existing price data (if available)
        try:
            df_existing_price = pd.read_csv(price_csv_path, dtype=str)
        except FileNotFoundError:
            print(f"{price_csv_path} not found. Creating a new one.")
            df_existing_price = pd.DataFrame(columns=["index", "card_name", "img_src"])
            
        # Use `index + card_name + img_src` as the composite key
        df_existing_price["unique_key"] = df_existing_price["index"] + "_" + df_existing_price["card_name"] + "_" + df_existing_price["img_src"].astype(str)
        df_price["unique_key"] = df_price["index"] + "_" + df_price["card_name"] + "_" + df_price["img_src"].astype(str)
        df_info["unique_key"] = df_info["index"] + "_" + df_info["card_name"] + "_" + df_info["img_src"].astype(str)

        # Merge price data using `unique_key`
        df_existing_price.set_index("unique_key", inplace=True)
        df_price.set_index("unique_key", inplace=True)

        # Update prices
        df_existing_price[price_column] = df_price[price_column].astype('Int64')
        df_existing_price.reset_index(inplace=True)
        df_existing_price.drop(columns=['unique_key'], inplace=True)

        # Handle img_src updates for multiple "to be printed" cases
        for i, row in df_info.iterrows():
            # Find all rows with the same `index` and `card_name`
            existing_rows = df_existing_price[
                (df_existing_price["index"] == row["index"]) & 
                (df_existing_price["card_name"] == row["card_name"])
            ]

            if not existing_rows.empty:
                new_img_src = row["img_src"]

                # Iterate through all matching rows
                for idx in existing_rows.index:
                    existing_img_src = df_existing_price.at[idx, "img_src"]

                    # Update only if the old img_src was the placeholder and the new one is real
                    if existing_img_src == PLACEHOLDER_IMG_SRC and new_img_src != PLACEHOLDER_IMG_SRC:
                        df_existing_price.at[idx, "img_src"] = new_img_src
                        print(f"Updated image for {row['card_name']} ({row['index']}) at row {idx}")

        # Save updated price CSV
        df_existing_price.to_csv(price_csv_path, index=False, encoding="utf-8-sig")
        print(f"Updated data saved to {price_csv_path} with column {price_column}")

        # Save new card information
        df_info.drop(columns=['unique_key'], inplace=True)
        df_info.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"Base card info saved to {csv_path}")

if __name__ == '__main__':
    asyncio.run(scrape_all())