# -*- coding: utf-8 -*-
import os
from PySide6.QtWidgets import (
    QTableWidget,
    QAbstractItemView,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
    QMenu,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from . import constants as const


class SortableTableWidget(QTableWidget):
    """
    可拖拽排序的表格组件
    """

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.source() == self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.source() == self:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: "QDropEvent"):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on_row(event)
            rows = sorted(list(set(item.row() for item in self.selectedItems())))
            rows_to_move = []
            for row in rows:
                row_data = []
                for column in range(self.columnCount()):
                    item = self.item(row, column)
                    if item:
                        # Clone the item to avoid moving the same item instance
                        clone_item = QTableWidgetItem(item)
                        # Copy user data if it exists
                        for role in range(
                            Qt.ItemDataRole.UserRole, Qt.ItemDataRole.UserRole + 100
                        ):
                            data = item.data(role)
                            if data is not None:
                                clone_item.setData(role, data)
                        row_data.append(clone_item)
                    else:
                        row_data.append(None)
                rows_to_move.append(row_data)

            # Adjust drop_row for items moved from above
            for row in reversed(rows):
                self.removeRow(row)
                if row < drop_row:
                    drop_row -= 1

            # Insert rows at the new position
            for row_index, row_data in enumerate(rows_to_move):
                row = drop_row + row_index
                self.insertRow(row)
                for column, item in enumerate(row_data):
                    if item:
                        self.setItem(row, column, item)

            # Reselect the moved rows
            self.clearSelection()
            for row_index in range(len(rows_to_move)):
                self.selectRow(drop_row + row_index)

            event.accept()
        super().dropEvent(event)

    def drop_on_row(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()
        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # Check if the drop position is in the lower half of the row
        return pos.y() - rect.top() > rect.height() / 2

    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_rows()
        super().keyPressEvent(event)
        event.accept()

    def open_selected_file_location(self):
        """打开选中文件所在文件夹"""
        selected_items = self.selectedItems()
        if not selected_items:
            return

        # 获取选中行的第一列（文件名列）
        row = selected_items.row()
        file_path_item = self.item(row, 0)
        if file_path_item:
            file_path = file_path_item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.exists(os.path.dirname(file_path)):
                folder = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def contextMenuEvent(self, event):
        """创建右键菜单"""
        if not self.selectedItems():
            return

        menu = QMenu(self)
        open_folder_action = menu.addAction(const.CONTEXT_MENU_OPEN_FOLDER)
        menu.addSeparator()
        move_top_action = menu.addAction(const.CONTEXT_MENU_MOVE_TOP)
        move_up_action = menu.addAction(const.CONTEXT_MENU_MOVE_UP)
        move_down_action = menu.addAction(const.CONTEXT_MENU_MOVE_DOWN)
        move_bottom_action = menu.addAction(const.CONTEXT_MENU_MOVE_BOTTOM)
        menu.addSeparator()
        delete_action = menu.addAction(const.CONTEXT_MENU_DELETE)

        action = menu.exec(self.mapToGlobal(event.pos()))

        if action == open_folder_action:
            self.open_selected_file_location()
        elif action == move_top_action:
            self.move_to_top()
        elif action == move_up_action:
            self.move_row_up()
        elif action == move_down_action:
            self.move_row_down()
        elif action == move_bottom_action:
            self.move_to_bottom()
        elif action == delete_action:
            self.delete_selected_rows()

    def move_to_top(self):
        """将选中的行移动到顶部"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return

        # 从上往下移动到顶部
        target_row = 0
        for row in selected_rows:
            # 如果行已经在目标位置之后，需要考虑前面的行移动带来的影响
            actual_row = row + len([r for r in selected_rows if r < row])
            self.move_row(actual_row, target_row)
            target_row += 1

        # 重新选择移动后的行
        self.clearSelection()
        for i in range(len(selected_rows)):
            self.selectRow(i)

    def move_to_bottom(self):
        """将选中的行移动到底部"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return

        # 计算目标位置（考虑到删除行后总行数的变化）
        total_rows = self.rowCount()
        target_start = total_rows - len(selected_rows)

        # 从下往上移动到底部
        for i, row in enumerate(reversed(selected_rows)):
            target_row = total_rows - i - 1
            # 如果行在目标位置之前，需要考虑前面的行移动带来的影响
            actual_row = row - len([r for r in selected_rows if r > row])
            self.move_row(actual_row, target_row)

        # 重新选择移动后的行
        self.clearSelection()
        for i in range(len(selected_rows)):
            self.selectRow(target_start + i)

    def move_row_up(self):
        """向上移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows or selected_rows == 0:
            return

        for row in selected_rows:
            self.move_row(row, row - 1)

        self.clearSelection()
        new_selection = [row - 1 for row in selected_rows]
        for row in new_selection:
            self.selectRow(row)

    def move_row_down(self):
        """向下移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return

        # 检查最后一个选中的行是否已经是最后一行
        if max(selected_rows) >= self.rowCount() - 1:
            return

        # 从下往上移动，避免行号变化影响
        for row in reversed(selected_rows):
            # 移动行
            self.move_row(row, row + 1)

        # 重新选择移动后的行
        self.clearSelection()
        for row in selected_rows:
            if row < self.rowCount() - 1:  # 确保不超出表格范围
                self.selectRow(row + 1)

    def move_row(self, source_row, dest_row):
        """移动一行"""
        if source_row == dest_row or dest_row < 0 or dest_row >= self.rowCount():
            return

        # 保存源行的所有列数据
        row_data = []
        for col in range(self.columnCount()):
            item = self.takeItem(source_row, col)
            if item is None:
                item = QTableWidgetItem("")
            row_data.append(item)

        # 删除源行
        self.removeRow(source_row)

        # 在目标位置插入新行
        self.insertRow(dest_row)

        # 还原数据
        for col, item in enumerate(row_data):
            self.setItem(dest_row, col, item)

    def delete_selected_rows(self):
        """删除所有选定的行"""
        selected_rows = set()
        for item in self.selectedItems():
            selected_rows.add(item.row())

        for row in sorted(list(selected_rows), reverse=True):
            self.removeRow(row)


def create_table_widget(column_count, headers, stretch_last_column=False):
    """创建通用的表格组件"""
    table = SortableTableWidget()
    table.setColumnCount(column_count)
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    if stretch_last_column and column_count > 1:
        table.horizontalHeader().setSectionResizeMode(
            column_count - 1, QHeaderView.Stretch
        )
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    return table


def create_control_button(text, callback=None):
    """创建通用的控制按钮"""
    button = QPushButton(text)
    if callback:
        button.clicked.connect(callback)
    return button


def create_file_select_layout(select_callback, additional_buttons=None):
    """创建文件选择布局"""
    layout = QHBoxLayout()
    select_button = create_control_button(
        const.SELECT_PDF_BUTTON_TEXT, select_callback
    )
    layout.addWidget(select_button)

    if additional_buttons:
        for btn in additional_buttons:
            layout.addWidget(btn)

    layout.addStretch()
    return layout, select_button


def create_progress_layout(
    progress_bar,
    clear_callback,
    start_callback,
    stop_callback,
    clear_text=const.CLEAR_LIST_BUTTON_TEXT,
    start_text=const.START_BUTTON_TEXT,
    stop_text=const.STOP_BUTTON_TEXT,
):
    """创建通用的进度和控制按钮布局"""
    layout = QHBoxLayout()
    layout.addWidget(progress_bar)

    clear_button = create_control_button(clear_text, clear_callback)
    start_button = create_control_button(start_text, start_callback)
    stop_button = create_control_button(stop_text, stop_callback)

    layout.addWidget(clear_button)
    layout.addWidget(start_button)
    layout.addWidget(stop_button)

    return layout, clear_button, start_button, stop_button


def create_simple_control_layout(
    clear_callback,
    start_callback,
    stop_callback,
    clear_text=const.CLEAR_LIST_BUTTON_TEXT,
    start_text=const.START_BUTTON_TEXT,
    stop_text=const.STOP_BUTTON_TEXT,
):
    """创建简化的控制按钮布局"""
    layout = QHBoxLayout()
    layout.addStretch()

    clear_button = create_control_button(clear_text, clear_callback)
    start_button = create_control_button(start_text, start_callback)
    stop_button = create_control_button(stop_text, stop_callback)

    layout.addWidget(clear_button)
    layout.addWidget(start_button)
    layout.addWidget(stop_button)

    return layout, clear_button, start_button, stop_button