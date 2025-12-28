"""命令列介面"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="tabelog",
    help="Tabelog 餐廳搜尋工具",
    add_completion=False,
)


@app.command()
def search(
    area: str | None = typer.Option(None, "--area", "-a", help="搜尋地區"),
    keyword: str | None = typer.Option(None, "--keyword", "-k", help="關鍵字"),
) -> None:
    """搜尋餐廳"""
    typer.echo("搜尋功能尚未實作")
    typer.echo(f"地區: {area}")
    typer.echo(f"關鍵字: {keyword}")


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
