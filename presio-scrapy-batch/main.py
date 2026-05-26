import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


SPIDERS = {
    "wong": "presio.spiders.wong.WongSpider",
    "plazavea": "presio.spiders.plazavea.PlazaVeaSpider",
}


def main():
    parser = argparse.ArgumentParser(description="Presio scraper")
    parser.add_argument("--supermarket", type=str, default="wong", choices=SPIDERS.keys(), help="Supermarket to scrape (default: wong)")
    parser.add_argument("--max-scrolls", type=int, default=5, help="Max scroll attempts per page (default: 7)")
    parser.add_argument("--no-change-limit", type=int, default=5, help="Stop scrolling after N scrolls with no new products (default: 5)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages per category (default: unlimited)")
    parser.add_argument("--output", type=str, default="out.json", help="Output file (default: out.json)")
    parser.add_argument("--loglevel", type=str, default="INFO", help="Log level (default: INFO)")
    parser.add_argument("--category", type=str, default=None, help="Category name or id to scrape (default: all)")
    args = parser.parse_args()

    settings = get_project_settings()
    settings.set("LOG_LEVEL", args.loglevel)
    settings.set("FEEDS", {args.output: {"format": "json", "overwrite": True}})

    spider_cls_path = SPIDERS[args.supermarket]
    module_path, cls_name = spider_cls_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    spider_cls = getattr(module, cls_name)

    process = CrawlerProcess(settings)
    process.crawl(
        spider_cls,
        max_scrolls=args.max_scrolls,
        no_change_limit=args.no_change_limit,
        max_pages=args.max_pages,
        category=args.category,
    )
    process.start()


if __name__ == "__main__":
    main()
