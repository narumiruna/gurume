"""Terminal UI for interactive restaurant search using Textual framework."""

from __future__ import annotations

from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Button
from textual.widgets import DataTable
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Input
from textual.widgets import Static

from .restaurant import Restaurant
from .search import SearchRequest


class SearchPanel(Container):
    """搜尋輸入面板"""

    def compose(self) -> ComposeResult:
        """建立搜尋面板的元件"""
        yield Static("🔍 餐廳搜尋", classes="panel-title")
        yield Input(placeholder="地區 (例如: 東京)", id="area-input")
        yield Input(placeholder="關鍵字 (例如: 寿司)", id="keyword-input")
        yield Button("搜尋", variant="primary", id="search-button")


class ResultsTable(DataTable):
    """餐廳結果列表"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """初始化表格欄位"""
        self.add_columns("名稱", "評分", "評論數", "地區", "類型")


class DetailPanel(Container):
    """餐廳詳細資訊面板"""

    def compose(self) -> ComposeResult:
        """建立詳細資訊面板的元件"""
        yield Static("📋 餐廳詳細資訊", classes="panel-title")
        yield Static("選擇一個餐廳查看詳細資訊", id="detail-content")


class TabelogApp(App):
    """Tabelog 餐廳搜尋 TUI 應用程式"""

    CSS = """
    Screen {
        layout: vertical;
    }

    .panel-title {
        background: $boost;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    SearchPanel {
        height: 12;
        border: solid $primary;
        padding: 1;
    }

    ResultsTable {
        height: 1fr;
        border: solid $secondary;
    }

    DetailPanel {
        height: 12;
        border: solid $accent;
        padding: 1;
    }

    Input {
        margin: 1;
    }

    Button {
        margin: 1;
    }

    #detail-content {
        height: 100%;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "focus_search", "Search"),
        ("r", "focus_results", "Results"),
        ("d", "focus_detail", "Detail"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.restaurants: list[Restaurant] = []
        self.selected_restaurant: Restaurant | None = None

    def compose(self) -> ComposeResult:
        """建立應用程式的元件"""
        yield Header()
        yield SearchPanel()
        yield ResultsTable(id="results-table")
        yield DetailPanel()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """處理按鈕點擊事件"""
        if event.button.id == "search-button":
            self.run_worker(self.perform_search())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """處理 Input Enter 鍵事件"""
        if event.input.id in ("area-input", "keyword-input"):
            self.run_worker(self.perform_search())

    async def perform_search(self) -> None:
        """執行餐廳搜尋"""
        # 取得輸入值
        area_input = self.query_one("#area-input", Input)
        keyword_input = self.query_one("#keyword-input", Input)

        area = area_input.value.strip()
        keyword = keyword_input.value.strip()

        if not area and not keyword:
            detail_content = self.query_one("#detail-content", Static)
            detail_content.update("請輸入地區或關鍵字")
            return

        # 顯示搜尋中訊息
        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(f"搜尋中: {area} {keyword}...")

        # 建立搜尋請求
        request = SearchRequest(area=area, keyword=keyword)

        try:
            # 執行搜尋
            response = await request.search()

            if response.restaurants:
                self.restaurants = response.restaurants
                self.update_results_table()
                detail_content.update(f"找到 {len(self.restaurants)} 家餐廳")
            else:
                self.restaurants = []
                table = self.query_one("#results-table", ResultsTable)
                table.clear()
                detail_content.update("沒有找到餐廳")

        except Exception as e:
            detail_content.update(f"搜尋錯誤: {str(e)}")

    def update_results_table(self) -> None:
        """更新結果表格"""
        table = self.query_one("#results-table", ResultsTable)
        table.clear()

        for restaurant in self.restaurants:
            rating = f"{restaurant.rating:.2f}" if restaurant.rating else "N/A"
            review_count = str(restaurant.review_count) if restaurant.review_count else "N/A"
            area = restaurant.area or "N/A"
            genres = ", ".join(restaurant.genres[:2]) if restaurant.genres else "N/A"

            table.add_row(restaurant.name, rating, review_count, area, genres)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """處理表格行選擇事件"""
        if event.cursor_row < len(self.restaurants):
            self.selected_restaurant = self.restaurants[event.cursor_row]
            self.update_detail_panel()

    def update_detail_panel(self) -> None:
        """更新詳細資訊面板"""
        if not self.selected_restaurant:
            return

        r = self.selected_restaurant

        detail_text = f"""名稱: {r.name}
評分: {r.rating if r.rating else "N/A"}
評論數: {r.review_count if r.review_count else "N/A"}
儲存數: {r.save_count if r.save_count else "N/A"}
地區: {r.area if r.area else "N/A"}
車站: {r.station if r.station else "N/A"}
距離: {r.distance if r.distance else "N/A"}
類型: {", ".join(r.genres) if r.genres else "N/A"}
午餐價格: {r.lunch_price if r.lunch_price else "N/A"}
晚餐價格: {r.dinner_price if r.dinner_price else "N/A"}
URL: {r.url}
"""

        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(detail_text)

    def action_focus_search(self) -> None:
        """聚焦到搜尋輸入框"""
        area_input = self.query_one("#area-input", Input)
        area_input.focus()

    def action_focus_results(self) -> None:
        """聚焦到結果表格"""
        table = self.query_one("#results-table", ResultsTable)
        table.focus()

    def action_focus_detail(self) -> None:
        """聚焦到詳細資訊面板"""
        detail_panel = self.query_one(DetailPanel)
        detail_panel.focus()


def main():
    """啟動 TUI 應用程式"""
    app = TabelogApp()
    app.run()


if __name__ == "__main__":
    main()
