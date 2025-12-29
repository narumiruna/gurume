"""命令列介面"""

from __future__ import annotations

import json
from enum import Enum
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .llm import parse_user_input
from .restaurant import SortType
from .search import SearchRequest

app = typer.Typer(
    name="gurume",
    help="Gurume 餐廳搜尋工具 - 搜尋 Tabelog 上的日本餐廳",
    add_completion=False,
)

console = Console()


class OutputFormat(str, Enum):
    """輸出格式"""

    TABLE = "table"
    JSON = "json"
    SIMPLE = "simple"


class SortOption(str, Enum):
    """排序選項"""

    RANKING = "ranking"
    REVIEW_COUNT = "review-count"
    NEW_OPEN = "new-open"
    STANDARD = "standard"


@app.command()
def search(
    area: Annotated[str | None, typer.Option("--area", "-a", help="搜尋地區（例如：東京、大阪）")] = None,
    keyword: Annotated[str | None, typer.Option("--keyword", "-k", help="關鍵字（例如：寿司、ラーメン）")] = None,
    cuisine: Annotated[str | None, typer.Option("--cuisine", "-c", help="料理類別（例如：すき焼き、寿司）")] = None,
    query: Annotated[str | None, typer.Option("--query", "-q", help="自然語言查詢（會自動解析地區和關鍵字）")] = None,
    sort: Annotated[SortOption, typer.Option("--sort", "-s", help="排序方式")] = SortOption.RANKING,
    limit: Annotated[int, typer.Option("--limit", "-n", help="顯示結果數量")] = 20,
    output: Annotated[OutputFormat, typer.Option("--output", "-o", help="輸出格式")] = OutputFormat.TABLE,
) -> None:
    """搜尋餐廳

    範例：
      gurume search --area 東京 --keyword 寿司
      gurume search -a 三重 -c すき焼き --sort ranking
      gurume search --area 大阪 --cuisine ラーメン -o json
      gurume search -q 三重すきやき
    """
    # 如果提供了自然語言查詢，自動解析
    if query:
        console.print(f"[cyan]🤖 使用 AI 解析自然語言：{query}[/cyan]")
        try:
            result = parse_user_input(query)
            # 只在未提供的情況下填入解析結果
            if not area and result.area:
                area = result.area
                console.print(f"[green]  ✓ 解析地區：{area}[/green]")
            if not keyword and result.keyword:
                keyword = result.keyword
                console.print(f"[green]  ✓ 解析關鍵字：{keyword}[/green]")
        except Exception as e:
            console.print(f"[yellow]警告：AI 解析失敗（{e}），請確認 OpenAI API 金鑰已設定[/yellow]")
            console.print("[yellow]繼續使用原始參數進行搜尋...[/yellow]")

    if not area and not keyword and not cuisine:
        console.print("[red]錯誤：至少需要提供地區、關鍵字或料理類別之一（或使用 -q 自然語言查詢）[/red]")
        raise typer.Exit(1)

    # 處理料理類別
    genre_code = None
    if cuisine:
        genre_code = get_genre_code(cuisine)
        if genre_code:
            console.print(f"[cyan]使用料理類別過濾：{cuisine} ({genre_code})[/cyan]")
        else:
            console.print(f"[yellow]警告：未知的料理類別「{cuisine}」，將作為關鍵字搜尋[/yellow]")
            keyword = cuisine
    # 如果沒有指定 cuisine，但 keyword 是料理類型，自動轉換為精確過濾
    elif keyword:
        detected_genre_code = get_genre_code(keyword)
        if detected_genre_code:
            genre_code = detected_genre_code
            console.print(f"[cyan]自動偵測料理類別：{keyword} ({genre_code})[/cyan]")

    # 轉換排序選項
    sort_type_map = {
        SortOption.RANKING: SortType.RANKING,
        SortOption.REVIEW_COUNT: SortType.REVIEW_COUNT,
        SortOption.NEW_OPEN: SortType.NEW_OPEN,
        SortOption.STANDARD: SortType.STANDARD,
    }
    sort_type = sort_type_map[sort]

    # 執行搜尋
    console.print("[green]搜尋中...[/green]")
    request = SearchRequest(
        area=area,
        keyword=keyword,
        genre_code=genre_code,
        sort_type=sort_type,
        max_pages=1,
    )

    response = request.search_sync()

    if response.status.value == "error":
        console.print(f"[red]搜尋錯誤：{response.error_message}[/red]")
        raise typer.Exit(1)

    if not response.restaurants:
        console.print("[yellow]沒有找到餐廳[/yellow]")
        raise typer.Exit(0)

    # 限制結果數量
    restaurants = response.restaurants[:limit]

    # 輸出結果
    if output == OutputFormat.JSON:
        _output_json(restaurants)
    elif output == OutputFormat.SIMPLE:
        _output_simple(restaurants)
    else:
        _output_table(restaurants)

    # 顯示統計
    console.print(f"\n[cyan]共找到 {len(response.restaurants)} 家餐廳，顯示前 {len(restaurants)} 家[/cyan]")


def _output_table(restaurants: list) -> None:
    """以表格格式輸出"""
    table = Table(title="搜尋結果")
    table.add_column("餐廳名稱", style="cyan", no_wrap=False)
    table.add_column("評分", justify="right", style="yellow")
    table.add_column("評論數", justify="right", style="green")
    table.add_column("地區", style="blue")
    table.add_column("類型", style="magenta")

    for r in restaurants:
        table.add_row(
            r.name,
            f"{r.rating:.2f}" if r.rating else "N/A",
            str(r.review_count) if r.review_count else "N/A",
            r.area or "N/A",
            ", ".join(r.genres[:2]) if r.genres else "N/A",
        )

    console.print(table)


def _output_json(restaurants: list) -> None:
    """以 JSON 格式輸出"""
    data = []
    for r in restaurants:
        data.append(
            {
                "name": r.name,
                "rating": r.rating,
                "review_count": r.review_count,
                "area": r.area,
                "genres": r.genres,
                "url": r.url,
                "lunch_price": r.lunch_price,
                "dinner_price": r.dinner_price,
            }
        )
    console.print(json.dumps(data, ensure_ascii=False, indent=2))


def _output_simple(restaurants: list) -> None:
    """以簡單格式輸出"""
    for i, r in enumerate(restaurants, 1):
        rating_str = f"{r.rating:.2f}" if r.rating else "N/A"
        review_str = str(r.review_count) if r.review_count else "N/A"
        console.print(f"{i}. {r.name} - ⭐{rating_str} ({review_str} 評論)")
        if r.area:
            console.print(f"   地區: {r.area}")
        if r.genres:
            console.print(f"   類型: {', '.join(r.genres[:3])}")
        console.print(f"   URL: {r.url}")
        console.print()


@app.command()
def list_cuisines() -> None:
    """列出所有支援的料理類別"""
    cuisines = get_all_genres()

    table = Table(title=f"支援的料理類別（共 {len(cuisines)} 種）")
    table.add_column("料理名稱", style="cyan")
    table.add_column("代碼", style="yellow")

    for cuisine in cuisines:
        code = get_genre_code(cuisine)
        table.add_row(cuisine, code or "")

    console.print(table)


@app.command()
def tui() -> None:
    """啟動互動式 TUI 介面"""
    from .tui import main as tui_main

    tui_main()


def main() -> None:
    """主程式進入點"""
    app()


if __name__ == "__main__":
    main()
