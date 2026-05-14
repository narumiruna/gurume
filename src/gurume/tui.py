"""Terminal UI for interactive restaurant search using Textual framework."""

from __future__ import annotations

import contextlib

from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button
from textual.widgets import DataTable
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Input
from textual.widgets import Label
from textual.widgets import OptionList
from textual.widgets import RadioButton
from textual.widgets import RadioSet
from textual.widgets import Static
from textual.worker import WorkerCancelled

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .restaurant import Restaurant
from .restaurant import SortType
from .search import SearchRequest
from .suggest import AreaSuggestion
from .suggest import KeywordSuggestion
from .suggest import TabelogSuggestUnavailableError
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async

TUI_UPDATE_EXCEPTIONS = (NoMatches, WorkerCancelled)
TUI_ACTION_EXCEPTIONS = (RuntimeError, ValueError)


class AreaSuggestModal(ModalScreen[str]):
    """Area suggestion modal."""

    CSS = """
    AreaSuggestModal {
        align: center middle;
    }

    #suggest-dialog {
        width: 70;
        height: auto;
        max-height: 25;
        border: heavy $accent;
        background: $surface;
        padding: 1;
    }

    #suggest-title {
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }

    #suggest-list {
        height: auto;
        max-height: 18;
        border: solid $primary-lighten-1;
        padding: 0;
    }

    #suggest-list:focus {
        border: solid $success;
    }

    #suggest-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0 0 0;
        margin-top: 1;
    }
    """

    def __init__(self, suggestions: list[AreaSuggestion], **kwargs):
        super().__init__(**kwargs)
        self.suggestions = suggestions

    def compose(self) -> ComposeResult:
        """Compose modal widgets."""
        with Vertical(id="suggest-dialog"):
            yield Label(f"🗺️  地區建議（共 {len(self.suggestions)} 個）", id="suggest-title")
            option_list = OptionList(id="suggest-list")
            for suggestion in self.suggestions:
                # Display format: icon, name, and type.
                type_label = "🚉 駅" if suggestion.datatype == "RailroadStation" else "📍 地區"
                option_list.add_option(f"{type_label}  {suggestion.name}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="suggest-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection events."""
        if event.option_index < len(self.suggestions):
            selected = self.suggestions[event.option_index]
            self.dismiss(selected.name)

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss(None)


class GenreSuggestModal(ModalScreen[str]):
    """Cuisine suggestion modal."""

    CSS = """
    GenreSuggestModal {
        align: center middle;
    }

    #genre-dialog {
        width: 70;
        height: auto;
        max-height: 30;
        border: heavy $accent;
        background: $surface;
        padding: 1;
    }

    #genre-title {
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }

    #genre-list {
        height: auto;
        max-height: 23;
        border: solid $primary-lighten-1;
        padding: 0;
    }

    #genre-list:focus {
        border: solid $success;
    }

    #genre-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0 0 0;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.genres = get_all_genres()

    def compose(self) -> ComposeResult:
        """Compose modal widgets."""
        with Vertical(id="genre-dialog"):
            yield Label(f"🍽️  料理類別（共 {len(self.genres)} 個）", id="genre-title")
            option_list = OptionList(id="genre-list")
            for genre in self.genres:
                # Use a cuisine icon for genre entries.
                option_list.add_option(f"🍜  {genre}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="genre-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection events."""
        if event.option_index < len(self.genres):
            selected = self.genres[event.option_index]
            self.dismiss(selected)

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss(None)


class KeywordSuggestModal(ModalScreen[str]):
    """Keyword suggestion modal backed by the dynamic API."""

    CSS = """
    KeywordSuggestModal {
        align: center middle;
    }

    #keyword-dialog {
        width: 70;
        height: auto;
        max-height: 30;
        border: heavy $accent;
        background: $surface;
        padding: 1;
    }

    #keyword-title {
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        margin-bottom: 1;
    }

    #keyword-list {
        height: auto;
        max-height: 23;
        border: solid $primary-lighten-1;
        padding: 0;
    }

    #keyword-list:focus {
        border: solid $success;
    }

    #keyword-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0 0 0;
        margin-top: 1;
    }
    """

    def __init__(self, suggestions: list[KeywordSuggestion], **kwargs):
        super().__init__(**kwargs)
        self.suggestions = suggestions

    def compose(self) -> ComposeResult:
        """Compose modal widgets."""
        with Vertical(id="keyword-dialog"):
            yield Label(f"🔍  關鍵字建議（共 {len(self.suggestions)} 個）", id="keyword-title")
            option_list = OptionList(id="keyword-list")
            for suggestion in self.suggestions:
                # Choose icons by datatype.
                icon = (
                    "🍜" if suggestion.datatype == "Genre2" else "🏪" if suggestion.datatype == "Restaurant" else "🔖"
                )
                option_list.add_option(f"{icon}  {suggestion.name}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="keyword-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection events."""
        if event.option_index < len(self.suggestions):
            selected = self.suggestions[event.option_index].name
            self.dismiss(selected)

    def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss(None)


class SearchPanel(Container):
    """Search input panel."""

    def compose(self) -> ComposeResult:
        """Compose search panel widgets."""
        yield Static("餐廳搜尋", classes="panel-title")
        with Horizontal(id="input-row"):
            yield Input(placeholder="地區 (例如: 東京, 按 F2 查看建議)", id="area-input")
            yield Input(placeholder="關鍵字 (例如: 寿司, 按 F3 選擇料理類別)", id="keyword-input")
        with Horizontal(id="sort-row"):
            yield Static("排序:", classes="sort-label")
            with RadioSet(id="sort-radio"):
                yield RadioButton("評分排名", value=True, id="sort-ranking")
                yield RadioButton("評論數", id="sort-review")
                yield RadioButton("新開幕", id="sort-new")
                yield RadioButton("標準", id="sort-standard")
            yield Button("搜尋", variant="primary", id="search-button")


class ResultsTable(DataTable):
    """Restaurant results table."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """Initialize table columns."""
        self.add_columns("餐廳名稱", "評分", "評論數", "地區", "類型")


class DetailPanel(Container):
    """Restaurant detail panel."""

    def compose(self) -> ComposeResult:
        """Compose detail panel widgets."""
        yield Static("詳細資訊", classes="panel-title")
        yield Static("請選擇餐廳查看詳細資訊", id="detail-content")


class TabelogApp(App):
    """Tabelog restaurant search TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    .panel-title {
        background: $surface-darken-1;
        color: $text;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }

    SearchPanel {
        height: auto;
        border: solid $primary-lighten-1;
        padding: 0 1 1 1;
        margin: 1 1 0 1;
    }

    #input-row {
        height: auto;
        margin: 0 0 1 0;
        padding: 0;
    }

    #area-input, #keyword-input {
        width: 1fr;
        margin-right: 1;
    }

    #area-input:focus, #keyword-input:focus {
        border: solid $success;
    }

    #sort-row {
        height: auto;
        margin: 0;
        padding: 0;
    }

    #content-row {
        height: 1fr;
        margin: 0 1 1 1;
    }

    ResultsTable {
        width: 2fr;
        height: 100%;
        border: solid $primary-lighten-1;
        margin-right: 1;
    }

    ResultsTable:focus {
        border: solid $accent;
    }

    ResultsTable > .datatable--header {
        background: $surface-darken-1;
        color: $text;
        text-style: bold;
    }

    ResultsTable > .datatable--cursor {
        background: $accent-darken-1;
        color: $text;
    }

    DetailPanel {
        width: 1fr;
        height: 100%;
        border: solid $primary-lighten-1;
        padding: 1;
    }

    .sort-label {
        width: auto;
        padding: 0 1 0 0;
        color: $text-muted;
        text-style: bold;
        content-align: center middle;
    }

    RadioSet {
        width: 1fr;
        padding: 0;
        background: transparent;
        layout: horizontal;
    }

    RadioButton {
        padding: 0 1;
        margin: 0;
        background: transparent;
        color: $text-muted;
    }

    RadioButton:hover {
        color: $text;
    }

    RadioButton.-selected {
        color: $success;
        text-style: bold;
    }

    Button {
        margin: 0 0 0 1;
        width: auto;
        min-width: 20;
    }

    Button:hover {
        background: $primary-darken-1;
    }

    Button:focus {
        border: solid $accent;
    }

    #detail-content {
        height: 100%;
        overflow-y: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "focus_search", "Search"),
        ("r", "focus_results", "Results"),
        ("d", "focus_detail", "Detail"),
        ("f2", "show_area_suggest", "Area Suggest"),
        ("f3", "show_genre_suggest", "Genre Suggest"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.restaurants: list[Restaurant] = []
        self.selected_restaurant: Restaurant | None = None
        self.search_worker = None
        self.current_genre_code: str | None = None  # Currently selected cuisine genre code.

    def compose(self) -> ComposeResult:
        """Compose application widgets."""
        yield Header()
        yield SearchPanel()
        with Horizontal(id="content-row"):
            yield ResultsTable(id="results-table")
            yield DetailPanel()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "search-button":
            self.start_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key submissions from inputs."""
        if event.input.id in ("area-input", "keyword-input"):
            self.start_search()

    def start_search(self) -> None:
        """Start a search and cancel any previous search."""
        # Cancel the previous search worker.
        if self.search_worker and not self.search_worker.is_finished:
            self.search_worker.cancel()

        # Start a new search worker.
        self.search_worker = self.run_worker(self.perform_search())

    async def perform_search(self) -> None:
        """Run a restaurant search."""
        try:
            area, keyword = self._get_search_inputs()
            if not area and not keyword:
                self.query_one("#detail-content", Static).update("請輸入地區或關鍵字")
                return

            genre_code_to_use, keyword = self._resolve_genre_search(keyword)
            sort_type, sort_name = self._get_sort_selection()
            detail_content = self.query_one("#detail-content", Static)
            search_params = self._build_search_params_text(area, keyword, genre_code_to_use)
            detail_content.update(f"搜尋中 ({sort_name}): {search_params}...")

            request = SearchRequest(area=area, keyword=keyword, genre_code=genre_code_to_use, sort_type=sort_type)
            response = await request.search()
            self._handle_search_response(response.restaurants, search_params, sort_name)
        except TUI_ACTION_EXCEPTIONS as e:
            self._update_search_error(e)
        except TUI_UPDATE_EXCEPTIONS as e:
            self._update_search_error(e)

    def update_results_table(self) -> None:
        """Update the results table."""
        try:
            table = self.query_one("#results-table", ResultsTable)
            table.clear()

            for restaurant in self.restaurants:
                rating = f"{restaurant.rating:.2f}" if restaurant.rating else "N/A"
                review_count = str(restaurant.review_count) if restaurant.review_count else "N/A"
                area = restaurant.area or "N/A"
                genres = ", ".join(restaurant.genres[:2]) if restaurant.genres else "N/A"

                table.add_row(restaurant.name, rating, review_count, area, genres)
        except TUI_UPDATE_EXCEPTIONS:
            pass

    def _get_search_inputs(self) -> tuple[str, str]:
        area_input = self.query_one("#area-input", Input)
        keyword_input = self.query_one("#keyword-input", Input)
        return area_input.value.strip(), keyword_input.value.strip()

    def _resolve_genre_search(self, keyword: str) -> tuple[str | None, str]:
        detected_genre = get_genre_code(keyword) if keyword else None
        if detected_genre:
            return detected_genre, ""
        return self.current_genre_code, keyword

    def _get_sort_selection(self) -> tuple[SortType, str]:
        sort_radio = self.query_one("#sort-radio", RadioSet)
        pressed_button = sort_radio.pressed_button
        if pressed_button and pressed_button.id == "sort-review":
            return SortType.REVIEW_COUNT, "評論數排序"
        if pressed_button and pressed_button.id == "sort-new":
            return SortType.NEW_OPEN, "新開幕"
        if pressed_button and pressed_button.id == "sort-standard":
            return SortType.STANDARD, "標準排序"
        return SortType.RANKING, "評分排名"

    def _build_search_params_text(self, area: str, keyword: str, genre_code: str | None) -> str:
        genre_name = ""
        if genre_code:
            from .genre_mapping import get_genre_name_by_code

            genre_name = get_genre_name_by_code(genre_code) or ""

        search_params = f"地區: {area or '(無)'}, 關鍵字: {keyword or '(無)'}"
        if genre_name:
            search_params += f", 料理類別: {genre_name}"
        return search_params

    def _handle_search_response(self, restaurants: list[Restaurant], search_params: str, sort_name: str) -> None:
        detail_content = self.query_one("#detail-content", Static)
        if restaurants:
            self.restaurants = restaurants
            self.update_results_table()
            detail_content.update(f"找到 {len(self.restaurants)} 家餐廳\n搜尋條件: {search_params}\n排序: {sort_name}")
            return

        self.restaurants = []
        self.query_one("#results-table", ResultsTable).clear()
        detail_content.update("沒有找到餐廳")

    def _update_search_error(self, error: BaseException) -> None:
        message = "搜尋已取消" if isinstance(error, WorkerCancelled) else f"搜尋錯誤: {error!s}"
        with contextlib.suppress(*TUI_UPDATE_EXCEPTIONS):
            self.query_one("#detail-content", Static).update(message)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle table row selection events."""
        if event.cursor_row < len(self.restaurants):
            self.selected_restaurant = self.restaurants[event.cursor_row]
            self.update_detail_panel()

    def update_detail_panel(self) -> None:
        """Update the detail panel."""
        if not self.selected_restaurant:
            return

        r = self.selected_restaurant

        detail_text = f"""名稱: {r.name}
評分: {r.rating or "N/A"}
評論數: {r.review_count or "N/A"}
儲存數: {r.save_count or "N/A"}
地區: {r.area or "N/A"}
車站: {r.station or "N/A"}
距離: {r.distance or "N/A"}
類型: {", ".join(r.genres) if r.genres else "N/A"}
午餐價格: {r.lunch_price or "N/A"}
晚餐價格: {r.dinner_price or "N/A"}
URL: {r.url}
"""

        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(detail_text)

    def action_focus_search(self) -> None:
        """Focus the search input."""
        area_input = self.query_one("#area-input", Input)
        area_input.focus()

    def action_focus_results(self) -> None:
        """Focus the results table."""
        table = self.query_one("#results-table", ResultsTable)
        table.focus()

    def action_focus_detail(self) -> None:
        """Focus the detail panel."""
        detail_panel = self.query_one(DetailPanel)
        detail_panel.focus()

    async def action_show_area_suggest(self) -> None:
        """Show the area suggestion modal."""
        area_input = self.query_one("#area-input", Input)
        query = area_input.value.strip()

        if not query:
            # Prompt the user when the input is empty.
            detail_content = self.query_one("#detail-content", Static)
            detail_content.update("💡 請先輸入地區關鍵字\n\n例如：東京、大阪、伊勢\n\n然後按 F2 查看建議")
            return

        # Show a loading message.
        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(f"🔍 正在搜尋「{query}」的地區建議...\n\n請稍候...")

        # Fetch suggestions.
        try:
            suggestions = await get_area_suggestions_async(query)
        except TabelogSuggestUnavailableError as e:
            detail_content.update(f"⚠️ 地區建議服務暫時無法使用\n\n{e}")
            return

        if not suggestions:
            detail_content.update(
                f"❌ 找不到「{query}」的地區建議\n\n建議：\n• 嘗試更短的關鍵字\n• 使用日文地名\n• 試試附近的地標或車站"
            )
            return

        # Show modal.
        def on_dismiss(selected_area: str | None) -> None:
            if selected_area:
                area_input.value = selected_area
                detail_content.update(f"✅ 已選擇地區：{selected_area}\n\n現在可以點擊搜尋按鈕或按 Enter 開始搜尋")
            else:
                detail_content.update("⏸️ 已取消選擇")

        await self.push_screen(AreaSuggestModal(suggestions), on_dismiss)

    async def action_show_genre_suggest(self) -> None:
        """Show the cuisine suggestion modal.

        - Empty keyword: show the fixed cuisine list.
        - Non-empty keyword: show dynamic keyword suggestions from the API.
        """
        keyword_input = self.query_one("#keyword-input", Input)
        keyword_value = keyword_input.value.strip()
        detail_content = self.query_one("#detail-content", Static)

        # Case 1: empty keyword; show the fixed cuisine list.
        if not keyword_value:
            detail_content.update("🍽️ 正在載入料理類別選項...")

            def on_dismiss_genre(selected_genre: str | None) -> None:
                if selected_genre:
                    keyword_input.value = selected_genre
                    self.current_genre_code = get_genre_code(selected_genre)
                    detail_content.update(
                        f"✅ 已選擇料理類別：{selected_genre}\n\n"
                        f"料理代碼：{self.current_genre_code}\n\n"
                        f"💡 現在可以輸入地區後按搜尋，或直接按 Enter 開始搜尋"
                    )
                else:
                    detail_content.update("⏸️ 已取消選擇")

            await self.push_screen(GenreSuggestModal(), on_dismiss_genre)

        # Case 2: non-empty keyword; show dynamic API suggestions.
        else:
            detail_content.update(f"🔍 正在搜尋「{keyword_value}」的關鍵字建議...")

            try:
                # Fetch keyword suggestions from the API.
                suggestions = await get_keyword_suggestions_async(keyword_value)

                if not suggestions:
                    detail_content.update(
                        f"❌ 沒有找到「{keyword_value}」的相關建議\n\n"
                        f"💡 提示：\n"
                        f"• 清空關鍵字後按 F3 可查看所有料理類別\n"
                        f"• 嘗試輸入更短的關鍵字（例如：すき、寿司）"
                    )
                    return

                detail_content.update(f"✅ 找到 {len(suggestions)} 個建議")

                def on_dismiss_keyword(selected_keyword: str | None) -> None:
                    if selected_keyword:
                        keyword_input.value = selected_keyword
                        # Try to resolve a genre_code.
                        self.current_genre_code = get_genre_code(selected_keyword)
                        if self.current_genre_code:
                            detail_content.update(
                                f"✅ 已選擇：{selected_keyword}\n\n"
                                f"料理代碼：{self.current_genre_code}\n\n"
                                f"💡 現在可以輸入地區後按搜尋，或直接按 Enter 開始搜尋"
                            )
                        else:
                            detail_content.update(
                                f"✅ 已選擇：{selected_keyword}\n\n💡 現在可以輸入地區後按搜尋，或直接按 Enter 開始搜尋"
                            )
                    else:
                        detail_content.update("⏸️ 已取消選擇")

                await self.push_screen(KeywordSuggestModal(suggestions), on_dismiss_keyword)

            except TUI_ACTION_EXCEPTIONS as e:
                detail_content.update(
                    f"❌ 取得關鍵字建議時發生錯誤\n\n錯誤訊息：{e}\n\n💡 建議：清空關鍵字後按 F3 查看所有料理類別"
                )


def main():
    """Launch the TUI application."""
    app = TabelogApp()
    app.run()


if __name__ == "__main__":
    main()
