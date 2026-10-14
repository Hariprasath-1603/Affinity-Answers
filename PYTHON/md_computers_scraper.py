import argparse
import csv
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from typing import List, Optional
from urllib.parse import quote_plus

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Run: pip install requests beautifulsoup4 brotli")


BASE_URL   = "https://mdcomputers.in"
SEARCH_URL = BASE_URL + "/?route=product/search"
CARD       = ".retrinapro-productlist-all_products_design"
PAGE_DELAY = 0.8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


@dataclass
class Product:
    name:           str
    url:            str
    price:          str
    original_price: str
    discount:       str
    availability:   str
    rating:         str


def clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def get_page(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        r = session.get(url, headers={**HEADERS, "Referer": BASE_URL}, timeout=20)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.exceptions.HTTPError as e:
        print(f"[!] HTTP {e.response.status_code} — {url}", file=sys.stderr)
    except requests.exceptions.RequestException as e:
        print(f"[!] {e}", file=sys.stderr)
    return None


def parse_page(soup: BeautifulSoup) -> List[Product]:
    products = []

    for card in soup.select(CARD):
        title = card.select_one("h3.product-entities-title a") or card.select_one("h3 a")
        if not title:
            continue

        name = clean(title.get_text())
        url  = title.get("href", "")

        ins = card.select_one("span.price span.ins span.amount")
        del_ = card.select_one("span.price span.del span.amount")
        if ins:
            price = clean(ins.get_text())
            original_price = clean(del_.get_text()) if del_ else ""
        else:
            amt = card.select_one("span.price span.amount") or card.select_one("span.price")
            price = clean(amt.get_text()) if amt else ""
            original_price = ""

        badge = card.select_one("span.onsale") or card.select_one(".product-labels span")
        discount = clean(badge.get_text()) if badge else ""

        btn = card.select_one("button.add_to_cart_button")
        if btn:
            availability = "Out of Stock" if "out" in " ".join(btn.get("class", [])).lower() else "In Stock"
        else:
            stock = card.select_one(".stock")
            availability = clean(stock.get_text()) if stock else "Unknown"

        stars = len(card.select(".bi-star-fill, .star-rating span"))
        rating = f"{stars}/5" if stars else ""

        products.append(Product(name, url, price, original_price, discount, availability, rating))

    return products


def total_pages(soup: BeautifulSoup) -> int:
    for tag in soup.select("p, .woocommerce-result-count, .col-sm-6"):
        m = re.search(r"\((\d+)\s+pages?\)", clean(tag.get_text()), re.I)
        if m:
            return int(m.group(1))
    nums = [int(a.get_text()) for a in soup.select("ul.pagination li a, .page-numbers a") if a.get_text().isdigit()]
    return max(nums) if nums else 1


def scrape(term: str, max_pages: int = 5) -> List[Product]:
    session = requests.Session()

    # Visit homepage first to get Cloudflare cookies
    try:
        session.get(BASE_URL, headers=HEADERS, timeout=15)
    except requests.exceptions.RequestException:
        pass
    time.sleep(0.5)

    encoded = quote_plus(term)
    results = []

    soup = get_page(f"{SEARCH_URL}&search={encoded}", session)
    if not soup:
        return results

    results.extend(parse_page(soup))
    pages = min(total_pages(soup), max_pages)
    print(f"  Page 1/{pages} done ({len(results)} products so far)")

    for p in range(2, pages + 1):
        time.sleep(PAGE_DELAY)
        soup = get_page(f"{SEARCH_URL}&search={encoded}&page={p}", session)
        if not soup:
            break
        before = len(results)
        results.extend(parse_page(soup))
        print(f"  Page {p}/{pages} done ({len(results) - before} products)")

    return results


def _rs(text: str) -> str:
    return text.replace("\u20b9", "Rs.")


def to_table(products: List[Product]) -> None:
    if not products:
        print("No products found.")
        return

    W = [4, 52, 14, 14, 7, 14, 6]
    headers = ["#", "Name", "Price", "Original", "Disc%", "Stock", "Rating"]
    sep = "+-" + "-+-".join("-" * w for w in W) + "-+"

    def row(*cells):
        return "| " + " | ".join(_rs(str(c)).ljust(w)[:w] for c, w in zip(cells, W)) + " |"

    print(sep)
    print(row(*headers))
    print(sep)
    for i, p in enumerate(products, 1):
        print(row(i, p.name, p.price, p.original_price, p.discount, p.availability, p.rating))
    print(sep)
    print(f"\n  {len(products)} result(s)\n")
    print("  URLs")
    print("  " + "-" * 70)
    for i, p in enumerate(products, 1):
        print(f"  [{i:>3}] {p.url}")


def save_report(products: List[Product], search_term: str) -> str:
    # Build a clean text file named after the search term
    slug = re.sub(r"[^\w]+", "_", search_term.strip()).upper()
    filename = f"{slug}_results.txt"

    W = [4, 52, 14, 14, 7, 14, 6]
    headers = ["#", "Name", "Price", "Original", "Disc%", "Stock", "Rating"]
    sep = "+-" + "-+-".join("-" * w for w in W) + "-+"

    def row(*cells):
        return "| " + " | ".join(_rs(str(c)).ljust(w)[:w] for c, w in zip(cells, W)) + " |"

    lines = []
    lines.append(f"MDComputers.in — Search results for: {search_term.upper()}")
    lines.append(f"Total products found: {len(products)}")
    lines.append("")
    lines.append(sep)
    lines.append(row(*headers))
    lines.append(sep)
    for i, p in enumerate(products, 1):
        lines.append(row(i, p.name, p.price, p.original_price, p.discount, p.availability, p.rating))
    lines.append(sep)
    lines.append("")
    lines.append("  Product URLs")
    lines.append("  " + "-" * 70)
    for i, p in enumerate(products, 1):
        lines.append(f"  [{i:>3}] {p.name}")
        lines.append(f"        {p.url}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename


def to_json(products: List[Product], path: Optional[str] = None) -> None:
    out = json.dumps([asdict(p) for p in products], ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Saved to {path}")
    else:
        sys.stdout.buffer.write(out.encode("utf-8") + b"\n")


def to_csv(products: List[Product], path: Optional[str] = None) -> None:
    fields = ["name", "price", "original_price", "discount", "availability", "rating", "url"]
    dest = open(path, "w", newline="", encoding="utf-8-sig") if path else sys.stdout
    w = csv.DictWriter(dest, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for p in products:
        w.writerow(asdict(p))
    if path:
        dest.close()
        print(f"Saved to {path}")


def main():
    parser = argparse.ArgumentParser(prog="md_computers_scraper",
                                     description="Search products on MDComputers.in")
    parser.add_argument("--search",   "-s", metavar="TERM")
    parser.add_argument("--pages",    "-p", metavar="N",   type=int, default=5)
    parser.add_argument("--output",   "-o", choices=["table", "json", "csv"], default="table")
    parser.add_argument("--out-file", "-f", metavar="FILE")
    parser.add_argument("--save",     "-S", action="store_true",
                        help="Auto-save results to a file named after the search term")
    args = parser.parse_args()

    if not args.search:
        try:
            args.search = input("Search term: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)

    if not args.search:
        sys.exit("No search term given.")

    print(f'\nSearching for "{args.search}" on MDComputers.in ...\n')
    products = scrape(args.search, args.pages)
    print()

    if   args.output == "table": to_table(products)
    elif args.output == "json":  to_json(products, args.out_file)
    elif args.output == "csv":   to_csv(products,  args.out_file)

    if not products:
        return

    # Ask to save (skip prompt if --save flag was passed)
    do_save = args.save
    if not do_save and args.output == "table":
        try:
            answer = input("\nSave results to file? [y/N]: ").strip().lower()
            do_save = answer == "y"
        except (EOFError, KeyboardInterrupt):
            pass

    if do_save:
        saved = save_report(products, args.search)
        print(f"\n  Saved -> {saved}")


if __name__ == "__main__":
    main()
