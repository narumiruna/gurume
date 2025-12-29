"""Terminal UI for interactive restaurant search using Textual framework."""

from __future__ import annotations

from textual import on
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.containers import Horizontal
from textual.containers import Vertical
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

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .llm import parse_user_input
from .restaurant import Restaurant
from .restaurant import SortType
from .search import SearchRequest
from .suggest import AreaSuggestion
from .suggest import KeywordSuggestion
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async


class AreaSuggestModal(ModalScreen[str]):
    """地區建議彈出視窗"""

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
        """建立彈出視窗的元件"""
        with Vertical(id="suggest-dialog"):
            yield Label(f"🗺️  地區建議（共 {len(self.suggestions)} 個）", id="suggest-title")
            option_list = OptionList(id="suggest-list")
            for suggestion in self.suggestions:
                # 顯示格式：圖標 名稱 (類型)
                type_label = "🚉 駅" if suggestion.datatype == "RailroadStation" else "📍 地區"
                option_list.add_option(f"{type_label}  {suggestion.name}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="suggest-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """處理選項選擇事件"""
        if event.option_index < len(self.suggestions):
            selected = self.suggestions[event.option_index]
            self.dismiss(selected.name)

    def on_key(self, event) -> None:
        """處理鍵盤事件"""
        if event.key == "escape":
            self.dismiss(None)


class GenreSuggestModal(ModalScreen[str]):
    """料理類別建議彈出視窗"""

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
        """建立彈出視窗的元件"""
        with Vertical(id="genre-dialog"):
            yield Label(f"🍽️  料理類別（共 {len(self.genres)} 個）", id="genre-title")
            option_list = OptionList(id="genre-list")
            for genre in self.genres:
                # 使用不同的圖標來區分料理類別
                option_list.add_option(f"🍜  {genre}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="genre-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """處理選項選擇事件"""
        if event.option_index < len(self.genres):
            selected = self.genres[event.option_index]
            self.dismiss(selected)

    def on_key(self, event) -> None:
        """處理鍵盤事件"""
        if event.key == "escape":
            self.dismiss(None)


class KeywordSuggestModal(ModalScreen[str]):
    """關鍵字建議彈出視窗（動態 API）"""

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
        """建立彈出視窗的元件"""
        with Vertical(id="keyword-dialog"):
            yield Label(f"🔍  關鍵字建議（共 {len(self.suggestions)} 個）", id="keyword-title")
            option_list = OptionList(id="keyword-list")
            for suggestion in self.suggestions:
                # 根據 datatype 使用不同圖標
                icon = (
                    "🍜" if suggestion.datatype == "Genre2" else "🏪" if suggestion.datatype == "Restaurant" else "🔖"
                )
                option_list.add_option(f"{icon}  {suggestion.name}")
            yield option_list
            yield Static("💡 提示：使用 ↑↓ 方向鍵選擇，Enter 確認，Esc 取消", id="keyword-hint")

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """處理選項選擇事件"""
        if event.option_index < len(self.suggestions):
            selected = self.suggestions[event.option_index].name
            self.dismiss(selected)

    def on_key(self, event) -> None:
        """處理鍵盤事件"""
        if event.key == "escape":
            self.dismiss(None)


class SearchPanel(Container):
    """搜尋輸入面板"""

    def compose(self) -> ComposeResult:
        """建立搜尋面板的元件"""
        yield Static("餐廳搜尋", classes="panel-title")
        with Horizontal(id="input-row"):
            yield Input(placeholder="地區 (例如: 東京, 按 F2 查看建議)", id="area-input")
            yield Input(
                placeholder="關鍵字 (例如: 寿司, 按 F3 選擇料理類別, 或輸入自然語言後按 F4 解析)", id="keyword-input"
            )
        with Horizontal(id="sort-row"):
            yield Static("排序:", classes="sort-label")
            with RadioSet(id="sort-radio"):
                yield RadioButton("評分排名", value=True, id="sort-ranking")
                yield RadioButton("評論數", id="sort-review")
                yield RadioButton("新開幕", id="sort-new")
                yield RadioButton("標準", id="sort-standard")
            yield Button("搜尋", variant="primary", id="search-button")


class ResultsTable(DataTable):
    """餐廳結果列表"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"

    def on_mount(self) -> None:
        """初始化表格欄位"""
        self.add_columns("餐廳名稱", "評分", "評論數", "地區", "類型")


class DetailPanel(Container):
    """餐廳詳細資訊面板"""

    def compose(self) -> ComposeResult:
        """建立詳細資訊面板的元件"""
        yield Static("詳細資訊", classes="panel-title")
        yield Static("請選擇餐廳查看詳細資訊", id="detail-content")


class TabelogApp(App):
    """Tabelog 餐廳搜尋 TUI 應用程式"""

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
        ("f4", "parse_natural_language", "AI Parse"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.restaurants: list[Restaurant] = []
        self.selected_restaurant: Restaurant | None = None
        self.search_worker = None
        self.current_genre_code: str | None = None  # 當前選擇的料理類別代碼

    def compose(self) -> ComposeResult:
        """建立應用程式的元件"""
        yield Header()
        yield SearchPanel()
        with Horizontal(id="content-row"):
            yield ResultsTable(id="results-table")
            yield DetailPanel()
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """處理按鈕點擊事件"""
        if event.button.id == "search-button":
            self.start_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """處理 Input Enter 鍵事件"""
        if event.input.id in ("area-input", "keyword-input"):
            self.start_search()

    def start_search(self) -> None:
        """啟動搜尋（取消之前的搜尋）"""
        # 取消之前的搜尋 worker
        if self.search_worker and not self.search_worker.is_finished:
            self.search_worker.cancel()

        # 啟動新的搜尋 worker
        self.search_worker = self.run_worker(self.perform_search())

    async def perform_search(self) -> None:
        """執行餐廳搜尋"""
        try:
            # 取得輸入值
            area_input = self.query_one("#area-input", Input)
            keyword_input = self.query_one("#keyword-input", Input)

            area = area_input.value.strip()
            keyword = keyword_input.value.strip()

            if not area and not keyword:
                detail_content = self.query_one("#detail-content", Static)
                detail_content.update("請輸入地區或關鍵字")
                return

            # 自動偵測 keyword 是否為料理類別名稱
            genre_code_to_use = self.current_genre_code
            detected_genre = get_genre_code(keyword) if keyword else None
            if detected_genre:
                # 如果 keyword 是已知的料理類別，使用對應的 genre_code
                genre_code_to_use = detected_genre
                # 將 keyword 設為空，避免重複搜尋
                keyword = ""

            # 取得排序方式
            sort_radio = self.query_one("#sort-radio", RadioSet)
            pressed_button = sort_radio.pressed_button

            if pressed_button and pressed_button.id == "sort-review":
                sort_type = SortType.REVIEW_COUNT
                sort_name = "評論數排序"
            elif pressed_button and pressed_button.id == "sort-new":
                sort_type = SortType.NEW_OPEN
                sort_name = "新開幕"
            elif pressed_button and pressed_button.id == "sort-standard":
                sort_type = SortType.STANDARD
                sort_name = "標準排序"
            else:
                sort_type = SortType.RANKING
                sort_name = "評分排名"

            # 顯示搜尋中訊息
            detail_content = self.query_one("#detail-content", Static)
            genre_name = ""
            if genre_code_to_use:
                from .genre_mapping import get_genre_name_by_code

                genre_name = get_genre_name_by_code(genre_code_to_use) or ""
            search_params = f"地區: {area or '(無)'}, 關鍵字: {keyword or '(無)'}"
            if genre_name:
                search_params += f", 料理類別: {genre_name}"
            detail_content.update(f"搜尋中 ({sort_name}): {search_params}...")

            # 建立搜尋請求（使用 Tabelog 的排序和料理類別代碼）
            request = SearchRequest(area=area, keyword=keyword, genre_code=genre_code_to_use, sort_type=sort_type)

            # 執行搜尋
            response = await request.search()

            if response.restaurants:
                self.restaurants = response.restaurants
                self.update_results_table()
                detail_content.update(
                    f"找到 {len(self.restaurants)} 家餐廳\n搜尋條件: {search_params}\n排序: {sort_name}"
                )
            else:
                self.restaurants = []
                table = self.query_one("#results-table", ResultsTable)
                table.clear()
                detail_content.update("沒有找到餐廳")

        except Exception as e:
            # 捕獲所有異常，包括搜尋被取消的情況
            try:
                detail_content = self.query_one("#detail-content", Static)
                detail_content.update(f"搜尋錯誤: {str(e)}")
            except Exception:
                # 如果連更新 UI 都失敗（例如應用程式正在關閉），就忽略
                pass

    def update_results_table(self) -> None:
        """更新結果表格"""
        try:
            table = self.query_one("#results-table", ResultsTable)
            table.clear()

            for restaurant in self.restaurants:
                rating = f"{restaurant.rating:.2f}" if restaurant.rating else "N/A"
                review_count = str(restaurant.review_count) if restaurant.review_count else "N/A"
                area = restaurant.area or "N/A"
                genres = ", ".join(restaurant.genres[:2]) if restaurant.genres else "N/A"

                table.add_row(restaurant.name, rating, review_count, area, genres)
        except Exception:
            # 忽略更新表格時的錯誤（例如在搜尋被取消時）
            pass

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

    async def action_show_area_suggest(self) -> None:
        """顯示地區建議彈出視窗"""
        area_input = self.query_one("#area-input", Input)
        query = area_input.value.strip()

        if not query:
            # 如果輸入框為空，提示用戶
            detail_content = self.query_one("#detail-content", Static)
            detail_content.update("💡 請先輸入地區關鍵字\n\n例如：東京、大阪、伊勢\n\n然後按 F2 查看建議")
            return

        # 顯示載入訊息（帶動畫效果）
        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(f"🔍 正在搜尋「{query}」的地區建議...\n\n請稍候...")

        # 取得建議
        suggestions = await get_area_suggestions_async(query)

        if not suggestions:
            detail_content.update(
                f"❌ 找不到「{query}」的地區建議\n\n建議：\n• 嘗試更短的關鍵字\n• 使用日文地名\n• 試試附近的地標或車站"
            )
            return

        # 顯示彈出視窗
        def on_dismiss(selected_area: str | None) -> None:
            if selected_area:
                area_input.value = selected_area
                detail_content.update(f"✅ 已選擇地區：{selected_area}\n\n現在可以點擊搜尋按鈕或按 Enter 開始搜尋")
            else:
                detail_content.update("⏸️ 已取消選擇")

        await self.push_screen(AreaSuggestModal(suggestions), on_dismiss)

    async def action_parse_natural_language(self) -> None:
        """使用 AI 解析自然語言輸入"""
        keyword_input = self.query_one("#keyword-input", Input)
        user_input = keyword_input.value.strip()

        if not user_input:
            # 如果輸入框為空，提示用戶
            detail_content = self.query_one("#detail-content", Static)
            detail_content.update(
                "💡 請先在關鍵字欄位輸入自然語言\n\n例如：\n• 我想吃三重的壽喜燒\n• 東京的拉麵\n• 大阪難波附近的居酒屋\n\n然後按 F4 使用 AI 解析"
            )
            return

        # 顯示載入訊息
        detail_content = self.query_one("#detail-content", Static)
        detail_content.update(f"🤖 正在使用 AI 解析「{user_input}」...\n\n請稍候...")

        try:
            # 使用 run_in_executor 在背景執行同步的 parse_user_input
            import asyncio

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, parse_user_input, user_input)

            # 更新 area 和 keyword 欄位
            area_input = self.query_one("#area-input", Input)
            area_input.value = result.area
            keyword_input.value = result.keyword

            # 顯示解析結果
            detail_content.update(
                f"✅ AI 解析成功！\n\n"
                f"原始輸入：{user_input}\n\n"
                f"解析結果：\n"
                f"• 地區：{result.area or '(無)'}\n"
                f"• 關鍵字：{result.keyword or '(無)'}\n\n"
                f"💡 可以手動調整後按搜尋，或直接按 Enter 開始搜尋"
            )

            # 如果地區有值，自動觸發地區建議
            if result.area:
                await self.action_show_area_suggest()
            # 如果關鍵字有值，自動觸發料理類別建議
            elif result.keyword:
                await self.action_show_genre_suggest()
            else:
                # 自動聚焦到搜尋按鈕，方便使用者直接 Enter 搜尋
                area_input.focus()

        except Exception as e:
            # 處理錯誤（API 失敗、網路問題等）
            error_msg = str(e)
            detail_content.update(
                f"❌ AI 解析失敗\n\n"
                f"錯誤訊息：{error_msg}\n\n"
                f"可能原因：\n"
                f"• OpenAI API 金鑰未設定（請檢查 .env 檔案）\n"
                f"• 網路連線問題\n"
                f"• API 呼叫限制\n\n"
                f"💡 建議改用手動輸入地區和關鍵字"
            )

    async def action_show_genre_suggest(self) -> None:
        """顯示料理類別建議彈出視窗（智慧型）

        - keyword 空字串 → 顯示固定料理類別列表
        - keyword 有內容 → 使用 API 顯示動態關鍵字建議
        """
        keyword_input = self.query_one("#keyword-input", Input)
        keyword_value = keyword_input.value.strip()
        detail_content = self.query_one("#detail-content", Static)

        # 情況1：keyword 為空，顯示固定料理類別列表
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

        # 情況2：keyword 有內容，使用 API 顯示動態建議
        else:
            detail_content.update(f"🔍 正在搜尋「{keyword_value}」的關鍵字建議...")

            try:
                # 呼叫 API 取得關鍵字建議
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
                        # 嘗試取得 genre_code
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

            except Exception as e:
                detail_content.update(
                    f"❌ 取得關鍵字建議時發生錯誤\n\n錯誤訊息：{e}\n\n💡 建議：清空關鍵字後按 F3 查看所有料理類別"
                )


def main():
    """啟動 TUI 應用程式"""
    app = TabelogApp()
    app.run()


if __name__ == "__main__":
    main()
